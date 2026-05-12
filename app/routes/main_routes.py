import random
import re
import secrets
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import requests
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import CSRFError, validate_csrf
from sqlalchemy import func, or_

from app import db
from app.forms.recipe_forms import CreateRecipeForm, DeleteRecipeForm, SaveExternalRecipeForm
from app.forms.auth_forms import ProfileForm
from app.forms.share_forms import RevokeShareForm, ShareRecipeForm
from app.models import Ingredient, Rating, Recipe, SharedAccess
from app.models.recipe import can_view_recipe
from app.models.user import User
COCKTAIL_API_URL = 'https://www.thecocktaildb.com/api/json/v1/1/random.php'
MEAL_API_URL = 'https://www.themealdb.com/api/json/v1/1/random.php'
COCKTAIL_LOOKUP_URL = 'https://www.thecocktaildb.com/api/json/v1/1/lookup.php'
MEAL_LOOKUP_URL = 'https://www.themealdb.com/api/json/v1/1/lookup.php'
EXTERNAL_API_TIMEOUT = 1.5
EXTERNAL_IMAGE_TIMEOUT = 3
EXTERNAL_IMAGE_HOSTS = ('thecocktaildb.com', 'themealdb.com')
EXTERNAL_IMAGE_URL_RE = re.compile(
    r'^https://(?:www\.)?(?:thecocktaildb|themealdb)\.com/images/[A-Za-z0-9/_.-]+$'
)

main_bp = Blueprint('main', __name__)


# ============================================================
# Shared helpers (ratings, external API shaping, save-external)
# ============================================================


def get_rating_summary(recipe_id):
    summary = (
        db.session.query(func.avg(Rating.stars), func.count(Rating.id))
        .filter(Rating.recipe_id == recipe_id)
        .first()
    )
    average = summary[0] or 0
    count = summary[1] or 0
    return round(float(average), 1), count


def _extract_external_ingredients(payload, max_slots=20):
    rows = []
    for index in range(1, max_slots + 1):
        name = (payload.get(f'strIngredient{index}') or '').strip()
        measure = (payload.get(f'strMeasure{index}') or '').strip()
        if not name:
            continue
        rows.append({'name': name, 'quantity': measure, 'unit': ''})
    return rows


def _shape_cocktail(payload):
    return {
        'name': (payload.get('strDrink') or '').strip(),
        'category': 'cocktail',
        'subcategory': (payload.get('strCategory') or '').strip() or None,
        'glass': (payload.get('strGlass') or '').strip() or None,
        'is_alcoholic': (payload.get('strAlcoholic') or '').strip().lower() == 'alcoholic',
        'instructions': (payload.get('strInstructions') or '').strip(),
        'image_url': (payload.get('strDrinkThumb') or '').strip() or None,
        'ingredients': _extract_external_ingredients(payload),
        'external_source': 'thecocktaildb',
        'external_id': str(payload.get('idDrink') or '').strip(),
        'source_origin': 'api',
        'internal_recipe_id': None,
    }


def _shape_meal(payload):
    return {
        'name': (payload.get('strMeal') or '').strip(),
        'category': 'food',
        'subcategory': (payload.get('strCategory') or '').strip() or None,
        'cuisine': (payload.get('strArea') or '').strip() or None,
        'glass': None,
        'is_alcoholic': False,
        'instructions': (payload.get('strInstructions') or '').strip(),
        'image_url': (payload.get('strMealThumb') or '').strip() or None,
        'ingredients': _extract_external_ingredients(payload),
        'external_source': 'themealdb',
        'external_id': str(payload.get('idMeal') or '').strip(),
        'source_origin': 'api',
        'internal_recipe_id': None,
    }


def _fetch_random_cocktail():
    try:
        response = requests.get(COCKTAIL_API_URL, timeout=EXTERNAL_API_TIMEOUT)
        response.raise_for_status()
        drinks = (response.json() or {}).get('drinks') or []
        if not drinks:
            return None
        shaped = _shape_cocktail(drinks[0])
        if not shaped['name'] or not shaped['external_id']:
            return None
        return shaped
    except (requests.RequestException, ValueError):
        return None


def _fetch_random_meal():
    try:
        response = requests.get(MEAL_API_URL, timeout=EXTERNAL_API_TIMEOUT)
        response.raise_for_status()
        meals = (response.json() or {}).get('meals') or []
        if not meals:
            return None
        shaped = _shape_meal(meals[0])
        if not shaped['name'] or not shaped['external_id']:
            return None
        return shaped
    except (requests.RequestException, ValueError):
        return None


def _shape_internal_recipe(recipe):
    image_url = None
    if recipe.image_data:
        image_url = url_for('main.recipe_image', recipe_id=recipe.id)
    return {
        'name': recipe.name,
        'category': recipe.category,
        'subcategory': recipe.subcategory,
        'glass': recipe.glass,
        'is_alcoholic': recipe.is_alcoholic,
        'instructions': recipe.instructions,
        'image_url': image_url,
        'ingredients': [
            {'name': ing.name, 'quantity': ing.quantity or '', 'unit': ing.unit or ''}
            for ing in recipe.ingredients
        ],
        'external_source': None,
        'external_id': None,
        'source_origin': 'db',
        'internal_recipe_id': recipe.id,
    }


def _fallback_from_db(category):
    candidates = (
        Recipe.query
        .filter(Recipe.is_public.is_(True), Recipe.category == category)
        .all()
    )
    if not candidates:
        return None
    return _shape_internal_recipe(random.choice(candidates))


# ============================================================
# Random draw (home page widget + save-external endpoint)
# ============================================================


@main_bp.route('/recipes/random.json')
def random_recipe_pair():
    fallback_used = False

    # Fetch both external sources in parallel so an offline source does not
    # block the other one (and cuts worst-case wait roughly in half).
    with ThreadPoolExecutor(max_workers=2) as pool:
        cocktail_future = pool.submit(_fetch_random_cocktail)
        meal_future = pool.submit(_fetch_random_meal)
        side_a = cocktail_future.result()
        side_b = meal_future.result()

    if side_a is None:
        side_a = _fallback_from_db('cocktail')
        if side_a is not None:
            fallback_used = True

    if side_b is None:
        side_b = _fallback_from_db('food')
        if side_b is not None:
            fallback_used = True

    if side_a is None and side_b is None:
        return jsonify({
            'error': 'no_recipes_available',
            'message': 'Recipe sources are unavailable right now. Please try again in a moment.',
        }), 503

    return jsonify({
        'side_a': side_a,
        'side_b': side_b,
        'fallback_used': fallback_used,
    })


def _lookup_external(source, external_id):
    if source == 'thecocktaildb':
        url = COCKTAIL_LOOKUP_URL
        list_key = 'drinks'
        shaper = _shape_cocktail
    elif source == 'themealdb':
        url = MEAL_LOOKUP_URL
        list_key = 'meals'
        shaper = _shape_meal
    else:
        return None

    try:
        response = requests.get(url, params={'i': external_id}, timeout=EXTERNAL_API_TIMEOUT)
        response.raise_for_status()
        items = (response.json() or {}).get(list_key) or []
        if not items:
            return None
        shaped = shaper(items[0])
        if not shaped['name'] or not shaped['external_id']:
            return None
        return shaped
    except (requests.RequestException, ValueError):
        return None


def _check_external_dedupe(user_id, source, external_id, name, category):
    exact = (
        Recipe.query
        .filter_by(
            creator_id=user_id,
            external_source=source,
            external_id=external_id,
        )
        .first()
    )
    if exact is not None:
        return 'exact', exact

    fuzzy = (
        Recipe.query
        .filter(
            Recipe.creator_id == user_id,
            Recipe.category == category,
            func.lower(Recipe.name) == name.strip().lower(),
        )
        .first()
    )
    if fuzzy is not None:
        return 'fuzzy', fuzzy

    return 'none', None


def _synthesise_external_description(payload):
    """Build a short blurb for an external recipe so listing cards show one.

    The cocktail/meal APIs don't expose a description field, so we synthesise
    one from the structured fields we do have.
    """
    bits = []
    if payload.get('category') == 'cocktail':
        bits.append('Alcoholic cocktail' if payload.get('is_alcoholic') else 'Non-alcoholic cocktail')
        if payload.get('glass'):
            bits.append(f"served in a {payload['glass'].lower()}")
    else:
        if payload.get('cuisine'):
            bits.append(f"{payload['cuisine']} dish")
        else:
            bits.append('Recipe')
        if payload.get('subcategory'):
            bits.append(f"({payload['subcategory'].lower()})")
    src = payload.get('external_source') or payload.get('source')
    src_label = 'TheCocktailDB' if src == 'thecocktaildb' else 'TheMealDB'
    return ', '.join(bits) + f'. Saved from {src_label}.'


def _download_external_image(url):
    """Fetch an external recipe photo and return (bytes, mime) or (None, None).

    Only allows images served from TheCocktailDB / TheMealDB to avoid SSRF
    against arbitrary hosts.
    """
    if not url or not isinstance(url, str):
        return None, None
    if not EXTERNAL_IMAGE_URL_RE.match(url):
        return None, None
    try:
        response = requests.get(url, timeout=EXTERNAL_IMAGE_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException:
        return None, None

    content_type = (response.headers.get('Content-Type') or '').split(';')[0].strip().lower()
    if not content_type.startswith('image/'):
        return None, None
    if len(response.content) > 5 * 1024 * 1024:
        return None, None
    return response.content, content_type


def _save_external_recipe(user_id, payload, visibility):
    recipe = Recipe(
        name=payload['name'],
        description=_synthesise_external_description(payload),
        category=payload['category'],
        subcategory=payload.get('subcategory'),
        glass=payload.get('glass'),
        is_alcoholic=bool(payload.get('is_alcoholic')),
        instructions=payload['instructions'],
        is_public=(visibility == 'public'),
        source='external',
        external_source=payload['external_source'],
        external_id=payload['external_id'],
        creator_id=user_id,
    )

    image_bytes, image_mime = _download_external_image(payload.get('image_url'))
    if image_bytes:
        recipe.image_data = image_bytes
        recipe.image_mime = image_mime

    db.session.add(recipe)
    db.session.flush()

    for index, row in enumerate(payload.get('ingredients') or [], start=1):
        if not row.get('name'):
            continue
        db.session.add(Ingredient(
            recipe_id=recipe.id,
            name=row['name'],
            quantity=(row.get('quantity') or '').strip() or None,
            unit=(row.get('unit') or '').strip() or None,
            position=index,
        ))

    db.session.commit()
    return recipe


@main_bp.route('/recipes/save-external', methods=['POST'])
@login_required
def save_external_recipe():
    form = SaveExternalRecipeForm()
    if not form.validate_on_submit():
        return jsonify({
            'error': 'invalid_request',
            'message': 'Could not save this recipe. Please try again.',
            'details': form.errors,
        }), 400

    source = form.external_source.data
    external_id = form.external_id.data.strip()
    visibility = form.visibility.data
    confirm = (form.confirm_duplicate.data or '').strip() == '1'

    payload = _lookup_external(source, external_id)
    if payload is None:
        return jsonify({
            'error': 'lookup_failed',
            'message': 'Could not look up that recipe. It may have been removed.',
        }), 502

    state, existing = _check_external_dedupe(
        current_user.id, source, external_id, payload['name'], payload['category'],
    )

    if state == 'exact':
        return jsonify({
            'error': 'already_saved',
            'message': f'You already have "{existing.name}" in your cookbook.',
            'existing_recipe_id': existing.id,
            'existing_recipe_url': url_for('main.recipe_detail', recipe_id=existing.id),
        }), 409

    if state == 'fuzzy' and not confirm:
        return jsonify({
            'error': 'similar_recipe',
            'message': f'You already have a recipe called "{existing.name}" in this category. Save anyway?',
            'confirm_required': True,
            'existing_recipe_id': existing.id,
            'existing_recipe_url': url_for('main.recipe_detail', recipe_id=existing.id),
        }), 409

    recipe = _save_external_recipe(current_user.id, payload, visibility)
    return jsonify({
        'ok': True,
        'recipe_id': recipe.id,
        'recipe_url': url_for('main.recipe_detail', recipe_id=recipe.id),
    }), 201


# ============================================================
# Home page
# ============================================================


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        shared_ids = [
            row[0] for row in db.session.execute(
                db.select(SharedAccess.recipe_id)
                .where(SharedAccess.shared_with_user_id == current_user.id)
            ).all()
        ]
        clauses = [
            Recipe.is_public.is_(True),
            Recipe.creator_id == current_user.id,
        ]
        if shared_ids:
            clauses.append(Recipe.id.in_(shared_ids))
        query = Recipe.query.filter(or_(*clauses))
    else:
        query = Recipe.query.filter(Recipe.is_public.is_(True))

    featured_recipes = (
        query.order_by(Recipe.created_at.desc()).limit(4).all()
    )
    rating_map = _rating_map_for([r.id for r in featured_recipes])
    featured = [
        {
            'recipe': r,
            'origin': _origin_label(r, current_user),
            'avg_rating': rating_map.get(r.id, (0.0, 0))[0],
            'rating_count': rating_map.get(r.id, (0.0, 0))[1],
        }
        for r in featured_recipes
    ]

    # Top rated public recipes (any creator) with at least one rating.
    top_rows = db.session.execute(
        db.select(Recipe, func.avg(Rating.stars).label('avg_stars'), func.count(Rating.id).label('rating_count'))
        .join(Rating, Rating.recipe_id == Recipe.id)
        .where(Recipe.is_public.is_(True))
        .group_by(Recipe.id)
        .order_by(func.avg(Rating.stars).desc(), func.count(Rating.id).desc())
        .limit(4)
    ).all()
    top_rated = [
        {
            'recipe': row[0],
            'avg_rating': float(row[1] or 0),
            'rating_count': int(row[2] or 0),
            'origin': _origin_label(row[0], current_user),
        }
        for row in top_rows
    ]

    return render_template('index.html', featured=featured, top_rated=top_rated)


def _origin_label(recipe, user):
    """Return the visibility/origin label for a recipe relative to user."""
    is_anon = user is None or not getattr(user, 'is_authenticated', False)
    if is_anon:
        return 'Community'
    if recipe.creator_id == user.id:
        return 'Public' if recipe.is_public else 'Private'
    if recipe.is_public:
        return 'Community'
    return 'Shared'


def _rating_map_for(recipe_ids):
    """Return {recipe_id: (avg_stars, count)} for the given recipe ids."""
    if not recipe_ids:
        return {}
    rows = db.session.execute(
        db.select(Rating.recipe_id, func.avg(Rating.stars), func.count(Rating.id))
        .where(Rating.recipe_id.in_(recipe_ids))
        .group_by(Rating.recipe_id)
    ).all()
    return {row[0]: (float(row[1] or 0), int(row[2] or 0)) for row in rows}


# ============================================================
# Recipes listing + detail + image
# ============================================================


@main_bp.route('/recipes')
def recipes():
    if current_user.is_authenticated:
        shared_ids_rows = db.session.execute(
            db.select(SharedAccess.recipe_id)
            .where(SharedAccess.shared_with_user_id == current_user.id)
        ).all()
        shared_ids = [row[0] for row in shared_ids_rows]

        # community + shared-to-me, excluding my own (mine show in the
        # "My recipes" section instead)
        query = Recipe.query.filter(
            Recipe.creator_id != current_user.id,
            or_(
                Recipe.is_public.is_(True),
                Recipe.id.in_(shared_ids) if shared_ids else False,
            )
        )
    else:
        query = Recipe.query.filter(Recipe.is_public.is_(True))

    all_recipes = query.order_by(Recipe.created_at.desc()).all()

    my_recipe_rows = []
    if current_user.is_authenticated:
        my_recipe_rows = Recipe.query.filter(
            Recipe.creator_id == current_user.id
        ).order_by(Recipe.created_at.desc()).all()

    rating_map = _rating_map_for(
        [r.id for r in all_recipes] + [r.id for r in my_recipe_rows]
    )

    visible_recipes = [
        {
            'recipe': r,
            'origin': _origin_label(r, current_user),
            'avg_rating': rating_map.get(r.id, (0.0, 0))[0],
            'rating_count': rating_map.get(r.id, (0.0, 0))[1],
        }
        for r in all_recipes
    ]

    my_recipes = [
        {
            'recipe': r,
            'origin': _origin_label(r, current_user),
            'avg_rating': rating_map.get(r.id, (0.0, 0))[0],
            'rating_count': rating_map.get(r.id, (0.0, 0))[1],
        }
        for r in my_recipe_rows
    ]

    return render_template(
        'recipes.html',
        visible_recipes=visible_recipes,
        my_recipes=my_recipes,
    )


@main_bp.route('/recipes/<int:recipe_id>')
def recipe_detail(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)
    if not can_view_recipe(recipe, current_user):
        abort(403)

    average_rating, rating_count = get_rating_summary(recipe.id)

    user_rating = None
    if current_user.is_authenticated:
        existing = Rating.query.filter_by(
            recipe_id=recipe.id,
            user_id=current_user.id,
        ).first()
        if existing:
            user_rating = existing.stars

    return render_template(
        'recipe_detail.html',
        recipe=recipe,
        origin=_origin_label(recipe, current_user),
        average_rating=average_rating,
        rating_count=rating_count,
        user_rating=user_rating,
        delete_form=DeleteRecipeForm(),
    )


@main_bp.route('/recipes/<int:recipe_id>/image')
def recipe_image(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)
    if not can_view_recipe(recipe, current_user):
        abort(403)
    if not recipe.image_data or not recipe.image_mime:
        abort(404)

    return send_file(
        BytesIO(recipe.image_data),
        mimetype=recipe.image_mime,
        max_age=3600,
    )


def _normalise_ingredient_rows(form_data):
    if form_data is None:
        return [{'name': '', 'quantity': '', 'unit': ''} for _ in range(3)]

    names = form_data.getlist('ingredient_name')
    quantities = form_data.getlist('ingredient_quantity')
    units = form_data.getlist('ingredient_unit')

    max_len = max(len(names), len(quantities), len(units), 3)
    rows = []
    for index in range(max_len):
        rows.append({
            'name': (names[index] if index < len(names) else '').strip(),
            'quantity': (quantities[index] if index < len(quantities) else '').strip(),
            'unit': (units[index] if index < len(units) else '').strip(),
        })
    return rows


# ============================================================
# Recipe create / edit / delete
# ============================================================


@main_bp.route('/recipes/external-prefill', methods=['GET'])
@login_required
def external_prefill():
    source = (request.args.get('source') or '').strip()
    external_id = (request.args.get('external_id') or '').strip()

    if source not in {'thecocktaildb', 'themealdb'}:
        flash('Could not start that recipe. Please try again.', 'warning')
        return redirect(url_for('main.create_recipe'))
    if not re.match(r'^[A-Za-z0-9_-]{1,20}$', external_id):
        flash('Could not start that recipe. Please try again.', 'warning')
        return redirect(url_for('main.create_recipe'))

    payload = _lookup_external(source, external_id)
    if payload is None:
        flash('Could not look up that recipe. It may have been removed.', 'warning')
        return redirect(url_for('main.create_recipe'))

    token = secrets.token_urlsafe(16)
    session[f'external_prefill_{token}'] = payload
    return redirect(url_for('main.create_recipe', prefill=token))


@main_bp.route('/recipe/create', methods=['GET', 'POST'])
@login_required
def create_recipe():
    prefill_payload = None
    prefill_token = request.args.get('prefill') if request.method == 'GET' else None
    if prefill_token:
        prefill_payload = session.pop(f'external_prefill_{prefill_token}', None)

    if prefill_payload:
        is_alc = 'true' if prefill_payload.get('is_alcoholic') else 'false'
        form = CreateRecipeForm(data={
            'name': prefill_payload.get('name', ''),
            'description': prefill_payload.get('description') or _synthesise_external_description(prefill_payload),
            'category': prefill_payload.get('category', ''),
            'glass': prefill_payload.get('glass') or '',
            'instructions': prefill_payload.get('instructions') or '',
            'is_alcoholic': is_alc,
            'visibility': 'private',
            'external_source': prefill_payload.get('source', ''),
            'external_id': prefill_payload.get('external_id', ''),
            'external_image_url': prefill_payload.get('image_url') or '',
        })
        ingredient_rows = [
            {
                'name': (i.get('name') or '').strip(),
                'quantity': (i.get('quantity') or '').strip(),
                'unit': (i.get('unit') or '').strip(),
            }
            for i in (prefill_payload.get('ingredients') or [])
        ]
        if not ingredient_rows:
            ingredient_rows = [{'name': '', 'quantity': '', 'unit': ''} for _ in range(3)]
    else:
        form = CreateRecipeForm()
        ingredient_rows = _normalise_ingredient_rows(request.form if request.method == 'POST' else None)

    ingredient_error = None

    if form.validate_on_submit():
        non_empty_rows = [
            row for row in ingredient_rows
            if row['name'] or row['quantity'] or row['unit']
        ]

        ext_source = (form.external_source.data or '').strip() or None
        ext_id = (form.external_id.data or '').strip() or None
        is_external = bool(ext_source and ext_id)

        if is_external:
            state, existing = _check_external_dedupe(
                current_user.id, ext_source, ext_id,
                form.name.data.strip(), form.category.data,
            )
            if state == 'exact':
                flash(f'You already have "{existing.name}" in your cookbook.', 'warning')
                return redirect(url_for('main.recipe_detail', recipe_id=existing.id))

        if not non_empty_rows:
            ingredient_error = 'Please add at least one ingredient.'
        else:
            is_food = form.category.data == 'food'
            glass_value = None if is_food else ((form.glass.data or '').strip() or None)
            is_alcoholic_value = False if is_food else (form.is_alcoholic.data == 'true')
            recipe = Recipe(
                name=form.name.data.strip(),
                description=(form.description.data or '').strip() or None,
                category=form.category.data,
                glass=glass_value,
                is_alcoholic=is_alcoholic_value,
                instructions=form.instructions.data.strip(),
                is_public=(form.visibility.data == 'public'),
                creator_id=current_user.id,
                source='external' if is_external else 'user',
                external_source=ext_source,
                external_id=ext_id,
            )

            upload = form.image.data
            if upload is not None and getattr(upload, 'filename', ''):
                upload.stream.seek(0)
                recipe.image_data = upload.read()
                recipe.image_mime = upload.mimetype
            elif (form.external_image_url.data or '').strip():
                ext_image_bytes, ext_image_mime = _download_external_image(
                    form.external_image_url.data.strip()
                )
                if ext_image_bytes:
                    recipe.image_data = ext_image_bytes
                    recipe.image_mime = ext_image_mime

            db.session.add(recipe)
            db.session.flush()

            position = 1
            for row in non_empty_rows:
                if not row['name']:
                    ingredient_error = 'Each saved ingredient needs a name.'
                    db.session.rollback()
                    break

                db.session.add(Ingredient(
                    recipe_id=recipe.id,
                    name=row['name'],
                    quantity=row['quantity'] or None,
                    unit=row['unit'] or None,
                    position=position,
                ))
                position += 1

            if ingredient_error is None:
                db.session.commit()
                flash('Recipe created successfully.', 'success')
                return redirect(url_for('main.recipe_detail', recipe_id=recipe.id))

    return render_template(
        'create_recipe.html',
        form=form,
        ingredient_rows=ingredient_rows,
        ingredient_error=ingredient_error,
    )


@main_bp.route('/recipes/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)
    if recipe.creator_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        form = CreateRecipeForm()
        ingredient_rows = _normalise_ingredient_rows(request.form)
    else:
        form = CreateRecipeForm(data={
            'name': recipe.name,
            'description': recipe.description or '',
            'category': recipe.category,
            'glass': recipe.glass or '',
            'instructions': recipe.instructions,
            'is_alcoholic': 'true' if recipe.is_alcoholic else 'false',
            'visibility': 'public' if recipe.is_public else 'private',
        })
        ingredient_rows = [
            {'name': i.name, 'quantity': i.quantity or '', 'unit': i.unit or ''}
            for i in recipe.ingredients
        ]
        if not ingredient_rows:
            ingredient_rows = [{'name': '', 'quantity': '', 'unit': ''} for _ in range(3)]

    ingredient_error = None

    if form.validate_on_submit():
        non_empty_rows = [
            row for row in ingredient_rows
            if row['name'] or row['quantity'] or row['unit']
        ]

        if not non_empty_rows:
            ingredient_error = 'Please add at least one ingredient.'
        else:
            is_food = form.category.data == 'food'
            recipe.name = form.name.data.strip()
            recipe.description = (form.description.data or '').strip() or None
            recipe.category = form.category.data
            recipe.glass = None if is_food else ((form.glass.data or '').strip() or None)
            recipe.is_alcoholic = False if is_food else (form.is_alcoholic.data == 'true')
            recipe.instructions = form.instructions.data.strip()
            recipe.is_public = (form.visibility.data == 'public')

            upload = form.image.data
            if upload is not None and getattr(upload, 'filename', ''):
                upload.stream.seek(0)
                recipe.image_data = upload.read()
                recipe.image_mime = upload.mimetype

            for ing in list(recipe.ingredients):
                db.session.delete(ing)
            db.session.flush()

            for index, row in enumerate(non_empty_rows, start=1):
                if not row['name']:
                    ingredient_error = 'Each saved ingredient needs a name.'
                    db.session.rollback()
                    break
                db.session.add(Ingredient(
                    recipe_id=recipe.id,
                    name=row['name'],
                    quantity=row['quantity'] or None,
                    unit=row['unit'] or None,
                    position=index,
                ))

            if ingredient_error is None:
                db.session.commit()
                flash('Recipe updated.', 'success')
                return redirect(url_for('main.recipe_detail', recipe_id=recipe.id))

    return render_template(
        'create_recipe.html',
        form=form,
        ingredient_rows=ingredient_rows,
        ingredient_error=ingredient_error,
        edit_recipe=recipe,
    )


@main_bp.route('/recipes/<int:recipe_id>/delete', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)
    if recipe.creator_id != current_user.id:
        abort(403)

    form = DeleteRecipeForm()
    if not form.validate_on_submit():
        abort(400)

    name = recipe.name
    db.session.delete(recipe)
    db.session.commit()
    flash(f'Deleted "{name}".', 'success')
    return redirect(url_for('main.recipes'))


# ============================================================
# Share page (grant + revoke access)
# ============================================================


@main_bp.route('/share', methods=['GET', 'POST'])
@login_required
def share():
    owned_private_recipes = db.session.execute(
        db.select(Recipe)
        .where(
            Recipe.creator_id == current_user.id,
            Recipe.is_public.is_(False),
        )
        .order_by(Recipe.name.asc())
    ).scalars().all()

    form = ShareRecipeForm(owner=current_user)
    form.set_recipe_choices(owned_private_recipes)
    revoke_form = RevokeShareForm()

    if form.validate_on_submit():
        db.session.add(SharedAccess(
            recipe_id=form.recipe.id,
            shared_with_user_id=form.target_user.id,
            granted_by_user_id=current_user.id,
        ))
        db.session.commit()
        flash(f'Shared "{form.recipe.name}" with {form.target_user.username}.', 'success')
        return redirect(url_for('main.share'))

    existing_grants = db.session.execute(
        db.select(SharedAccess)
        .join(Recipe, SharedAccess.recipe_id == Recipe.id)
        .where(Recipe.creator_id == current_user.id)
        .order_by(SharedAccess.created_at.desc())
    ).scalars().all()

    shared_with_you = db.session.execute(
        db.select(SharedAccess)
        .where(SharedAccess.shared_with_user_id == current_user.id)
        .order_by(SharedAccess.created_at.desc())
    ).scalars().all()

    return render_template(
        'share.html',
        form=form,
        revoke_form=revoke_form,
        existing_grants=existing_grants,
        shared_with_you=shared_with_you,
        has_private_recipes=bool(owned_private_recipes),
    )


@main_bp.route('/share/remove/<int:grant_id>', methods=['POST'])
@login_required
def remove_share(grant_id):
    form = RevokeShareForm()
    if not form.validate_on_submit():
        abort(400)

    grant = db.get_or_404(SharedAccess, grant_id)
    if grant.recipe.creator_id != current_user.id:
        abort(403)

    recipe_name = grant.recipe.name
    target_username = grant.shared_with.username
    db.session.delete(grant)
    db.session.commit()

    flash(f'Removed access to "{recipe_name}" for {target_username}.', 'success')
    return redirect(url_for('main.share'))


# ============================================================
# Ratings
# ============================================================


@main_bp.route('/recipes/<int:recipe_id>/rate', methods=['POST'])
def rate_recipe(recipe_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Please log in to rate recipes.'}), 401

    recipe = db.get_or_404(Recipe, recipe_id)

    if recipe.creator_id == current_user.id:
        return jsonify({'error': 'You cannot rate your own recipe.'}), 403

    if not can_view_recipe(recipe, current_user):
        return jsonify({'error': 'You are not allowed to rate this recipe.'}), 403

    payload = request.get_json(silent=True) or {}
    stars = payload.get('stars')

    try:
        stars = int(stars)
    except (TypeError, ValueError):
        return jsonify({'error': 'Rating must be a number from 1 to 5.'}), 400

    if stars < 1 or stars > 5:
        return jsonify({'error': 'Rating must be between 1 and 5.'}), 400

    rating = Rating.query.filter_by(
        recipe_id=recipe.id,
        user_id=current_user.id,
    ).first()

    if rating:
        rating.stars = stars
    else:
        rating = Rating(recipe_id=recipe.id, user_id=current_user.id, stars=stars)
        db.session.add(rating)

    db.session.commit()

    average, count = get_rating_summary(recipe.id)
    return jsonify({
        'success': True,
        'average': average,
        'count': count,
        'user_rating': stars,
    })


# ============================================================
# Profile + user avatar
# ============================================================


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = db.session.get(User, current_user.id)
    form = ProfileForm(user, obj=user)

    if request.method == 'POST' and request.form.get('action') == 'remove_avatar':
        try:
            validate_csrf(request.form.get('csrf_token'))
        except CSRFError:
            abort(400)
        user.avatar_data = None
        user.avatar_mime = None
        db.session.commit()
        flash('Profile picture removed.', 'success')
        return redirect(url_for('main.profile'))

    if form.validate_on_submit():
        user.username = form.username.data.strip()
        user.email = form.email.data.strip().lower()

        if form.new_password.data:
            user.set_password(form.new_password.data)

        upload = form.avatar.data
        if upload is not None and getattr(upload, 'filename', ''):
            upload.stream.seek(0)
            user.avatar_data = upload.read()
            user.avatar_mime = upload.mimetype

        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('main.profile'))

    return render_template('profile.html', form=form, user=user)


@main_bp.route('/users/<int:user_id>/avatar')
def user_avatar(user_id):
    user = db.get_or_404(User, user_id)
    if not user.avatar_data or not user.avatar_mime:
        abort(404)
    return send_file(
        BytesIO(user.avatar_data),
        mimetype=user.avatar_mime,
        max_age=3600,
    )
