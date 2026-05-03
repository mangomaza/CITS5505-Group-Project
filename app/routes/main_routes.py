from io import BytesIO

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.recipe_forms import CreateRecipeForm
from app.forms.share_forms import RevokeShareForm, ShareRecipeForm
from app.models import Ingredient, Recipe, SharedAccess
from app.models.recipe import can_view_recipe

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/recipes')
def recipes():
    return render_template('recipes.html')


@main_bp.route('/recipes/<int:recipe_id>')
def recipe_detail(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)
    if not can_view_recipe(recipe, current_user):
        abort(403)
    return render_template('recipe_detail.html', recipe=recipe)


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
