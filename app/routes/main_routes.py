import random
from io import BytesIO

import requests
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.forms.recipe_forms import CreateRecipeForm
from app.forms.share_forms import RevokeShareForm, ShareRecipeForm
from app.models import Ingredient, Rating, Recipe, SharedAccess
from app.models.recipe import can_view_recipe

COCKTAIL_API_URL = 'https://www.thecocktaildb.com/api/json/v1/1/random.php'
MEAL_API_URL = 'https://www.themealdb.com/api/json/v1/1/random.php'
EXTERNAL_API_TIMEOUT = 3

main_bp = Blueprint('main', __name__)


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
        'category': 'Cocktail',
        'subcategory': (payload.get('strCategory') or '').strip() or None,
        'cuisine': None,
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
        'category': 'Meal',
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
        'cuisine': recipe.cuisine,
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


@main_bp.route('/recipes/random.json')
def random_recipe_pair():
    side_a = _fetch_random_cocktail() or _fallback_from_db('Cocktail')
    side_b = _fetch_random_meal() or _fallback_from_db('Meal')

    if side_a is None and side_b is None:
        return jsonify({
            'error': 'no_recipes_available',
            'message': 'Recipe sources are unavailable right now. Please try again in a moment.',
        }), 503

    return jsonify({'side_a': side_a, 'side_b': side_b})


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/recipes')
def recipes():
    my_recipes = []
    if current_user.is_authenticated:
        my_recipes = (
            Recipe.query
            .filter_by(creator_id=current_user.id)
            .order_by(Recipe.created_at.desc())
            .all()
        )
    return render_template('recipes.html', my_recipes=my_recipes)


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
        average_rating=average_rating,
        rating_count=rating_count,
        user_rating=user_rating,
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


@main_bp.route('/recipe/create', methods=['GET', 'POST'])
@login_required
def create_recipe():
    # TODO: when Mix It Up's Edit-and-save flow is wired up, accept a
    # ?prefill=external_source:external_id query and pre-populate the form
    # from the cached external recipe.
    form = CreateRecipeForm()
    ingredient_rows = _normalise_ingredient_rows(request.form if request.method == 'POST' else None)
    ingredient_error = None

    if form.validate_on_submit():
        non_empty_rows = [
            row for row in ingredient_rows
            if row['name'] or row['quantity'] or row['unit']
        ]

        if not non_empty_rows:
            ingredient_error = 'Please add at least one ingredient.'
        else:
            recipe = Recipe(
                name=form.name.data.strip(),
                description=(form.description.data or '').strip() or None,
                category=form.category.data,
                glass=(form.glass.data or '').strip() or None,
                is_alcoholic=(form.is_alcoholic.data == 'true'),
                instructions=form.instructions.data.strip(),
                is_public=(form.visibility.data == 'public'),
                creator_id=current_user.id,
            )

            upload = form.image.data
            if upload is not None and getattr(upload, 'filename', ''):
                upload.stream.seek(0)
                recipe.image_data = upload.read()
                recipe.image_mime = upload.mimetype

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
