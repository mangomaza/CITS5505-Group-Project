from flask import Blueprint, redirect, render_template, url_for

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
    return render_template('create_recipe.html')


@main_bp.route('/share', methods=['GET', 'POST'])
def share():
    """Draft share page wiring for issue #45.

    Once the auth blueprint lands we will:
    - protect this route with login_required
    - build ShareRecipeForm(owner=current_user)
    - populate private recipe choices owned by current_user
    - create SharedAccess rows on valid POST
    - flash success and redirect back here
    """
    return render_template(
        'share.html',
        form=None,
        existing_grants=[],
    )


@main_bp.route('/shared-with-me')
def shared_with_me():
    """Draft page for recipes another user has shared with the viewer."""
    return render_template(
        'shared_with_me.html',
        shared_grants=[],
    )


@main_bp.route('/share/remove/<int:grant_id>', methods=['POST'])
def remove_share(grant_id):
    """Placeholder revoke endpoint for issue #45.

    Once auth lands this route should verify the current user owns the recipe
    grant before deleting it.
    """
    return redirect(url_for('main.share'))
