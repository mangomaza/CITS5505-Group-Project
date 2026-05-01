from flask import Blueprint, render_template, session, redirect, url_for, flash

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/recipes')
def recipes():
    return render_template('recipes.html')


@main_bp.route('/recipes/<int:recipe_id>')
def recipe_detail(recipe_id):
    return render_template('recipe_detail.html', recipe_id=recipe_id)


@main_bp.route('/recipe/create')
def create_recipe():
    if 'user_id' not in session:
        flash('Please log in to create a recipe.', 'warning')
        return redirect(url_for('auth.login'))

    return render_template('create_recipe.html')

@main_bp.route('/share')
def share():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth.login'))

    return render_template('share.html')