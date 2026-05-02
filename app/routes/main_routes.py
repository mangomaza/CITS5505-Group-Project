from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.share_forms import RevokeShareForm, ShareRecipeForm
from app.models import Recipe, SharedAccess
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


@main_bp.route('/recipe/create')
@login_required
def create_recipe():
    return render_template('create_recipe.html')


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
