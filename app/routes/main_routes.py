from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/recipes')
def recipes():
    return render_template('recipes.html')


@main_bp.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    return render_template('recipe_detail.html', recipe_id=recipe_id)


@main_bp.route('/recipe/create')
@login_required
def create_recipe():
    return render_template('create_recipe.html')


@main_bp.route('/share')
@login_required
def share():
    return render_template('share.html')
