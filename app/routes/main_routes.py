from flask import Blueprint, render_template, abort, Response
from flask_login import current_user
from app.models.recipe import Recipe, can_view_recipe

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/recipes')
def recipes():
    my_recipes():
    if current_user.authenticated:
        my_recipes = (
            Recipe.query
            .filter_by(creator_id=current_user.id)
            .order_by(Recipe.created_at.desc())
            .all()
        )
    return render_template('recipes.html')


@main_bp.route('/recipes/<int:recipe_id>')
def recipe_detail(recipe_id):
    return render_template('recipe_detail.html', recipe_id=recipe_id)


@main_bp.route('/recipe/create')
def create_recipe():
    return render_template('create_recipe.html')


@main_bp.route('/share')
def share():
    return render_template('share.html')
