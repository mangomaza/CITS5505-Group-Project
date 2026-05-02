from flask import Blueprint, render_template, abort, Response
from flask_login import current_user, login_required
from app.models.recipe import Recipe, can_view_recipe

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/recipes')
def recipes():
    my_recipes=[]
    if current_user.is_authenticated:
        my_recipes = (
            Recipe.query
            .filter_by(creator_id=current_user.id)
            .order_by(Recipe.created_at.desc())
            .all()
        )
    return render_template('recipes.html', my_recipes=my_recipes)

@main_bp.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    return render_template('recipe_detail.html', recipe_id=recipe_id, source='api')


@main_bp.route('/recipes/db/<int:recipe_id>')
def database_recipe_detail(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)

    if not can_view_recipe(recipe, current_user):
        abort(403)

    return render_template('recipe_detail.html', recipe=recipe, source='db')

@main_bp.route('/recipes/db/<int:recipe_id>/image')
def database_recipe_image(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)

    if not can_view_recipe(recipe, current_user):
        abort(403)

    if not recipe.image_data:
        abort(404)

    return Response(recipe.image_data, mimetype=recipe.image_mime)

@main_bp.route('/recipe/create')
@login_required
def create_recipe():
    return render_template('create_recipe.html')


@main_bp.route('/share')
@login_required
def share():
    return render_template('share.html')
