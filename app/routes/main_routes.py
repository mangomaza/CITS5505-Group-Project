from flask import Blueprint, render_template, abort, Response, request, jsonify
from flask_login import current_user, login_required
from app.models.recipe import Recipe, can_view_recipe
from sqlalchemy import func
from app.extensions import db
from app.models.rating import Rating

main_bp = Blueprint('main', __name__)

def get_rating_summary(recipe_id):
    summary = (
        db.session.query(
            func.avg(Rating.stars),
            func.count(Rating.id)
        )
        .filter(Rating.recipe_id == recipe_id)
        .first()
    )
    average = summary[0] or 0
    count = summary[1] or 0
    return round(float(average), 1), count


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
    average_rating, rating_count = get_rating_summary(recipe.id)
    
    user_rating = None
    if current_user.is_authenticated:
        rating = Rating.query.filter_by(
            recipe_id=recipe.id,
            user_id=current_user.id
        ).first()

        if rating:
            user_rating = rating.stars
    return render_template(
        'recipe_detail.html',
        recipe=recipe,
        source='db',
        average_rating=average_rating,
        rating_count=rating_count,
        user_rating=user_rating
    )

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

@main_bp.route('/recipes/db/<int:recipe_id>/rate', methods=['POST'])
def rate_database_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)

    if not can_view_recipe(recipe, current_user):
        return jsonify({
            'success': False,
            'error': 'You are not allowed to rate this recipe.'
        }), 403

    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Please log in to rate this recipe.'
        }), 401

    if recipe.creator_id == current_user.id:
        return jsonify({
            'success': False,
            'error': 'You cannot rate your own recipe.'
        }), 403

    data = request.get_json(silent=True)

    if not data or 'stars' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing rating value.'
        }), 400

    try:
        stars = int(data['stars'])
    except (TypeError, ValueError):
        return jsonify({
            'success': False,
            'error': 'Invalid rating value.'
        }), 400

    if stars < 1 or stars > 5:
        return jsonify({
            'success': False,
            'error': 'Rating must be between 1 and 5.'
        }), 400

    rating = Rating.query.filter_by(
        recipe_id=recipe.id,
        user_id=current_user.id
    ).first()

    if rating:
        rating.stars = stars
    else:
        rating = Rating(
            recipe_id=recipe.id,
            user_id=current_user.id,
            stars=stars
        )
        db.session.add(rating)

    db.session.commit()

    average_rating, rating_count = get_rating_summary(recipe.id)

    return jsonify({
        'success': True,
        'average': average_rating,
        'count': rating_count,
        'user_rating': stars
    })
