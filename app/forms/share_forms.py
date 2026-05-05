from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError

from app.extensions import db
from app.models import Recipe, SharedAccess, User


class ShareRecipeForm(FlaskForm):
    recipe_id = SelectField(
        'Recipe',
        coerce=int,
        validators=[DataRequired(message='Please choose one of your recipes.')],
    )
    username = StringField(
        'Share with',
        validators=[
            DataRequired(message='Enter the username to share with.'),
            Length(max=80, message='Username must be 80 characters or fewer.'),
        ],
    )
    submit = SubmitField('Share recipe')

    def __init__(self, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.target_user = None
        self.recipe = None

    def set_recipe_choices(self, recipes):
        self.recipe_id.choices = [(0, 'Select a recipe to share')] + [
            (recipe.id, recipe.name)
            for recipe in recipes
        ]

    def validate_recipe_id(self, field):
        if self.owner is None or not getattr(self.owner, 'is_authenticated', False):
            raise ValidationError('You must be logged in to share a recipe.')

        if field.data == 0:
            raise ValidationError('Please choose one of your recipes.')

        recipe = db.session.get(Recipe, field.data)
        if recipe is None:
            raise ValidationError('Selected recipe does not exist.')
        if recipe.creator_id != self.owner.id:
            raise ValidationError('You can only share recipes you created.')
        if recipe.is_public:
            raise ValidationError('Only private recipes can be shared from this page.')

        self.recipe = recipe

    def validate_username(self, field):
        if self.owner is None or not getattr(self.owner, 'is_authenticated', False):
            raise ValidationError('You must be logged in to share a recipe.')

        username = (field.data or '').strip()
        field.data = username
        target_user = db.session.execute(
            db.select(User).where(db.func.lower(User.username) == username.lower())
        ).scalar_one_or_none()

        if target_user is None:
            raise ValidationError('No user exists with that username.')
        if target_user.id == self.owner.id:
            raise ValidationError('You cannot share a recipe with yourself.')

        if self.recipe_id.data:
            existing_grant = db.session.execute(
                db.select(SharedAccess).where(
                    SharedAccess.recipe_id == self.recipe_id.data,
                    SharedAccess.shared_with_user_id == target_user.id,
                )
            ).scalar_one_or_none()
            if existing_grant is not None:
                raise ValidationError('That user already has access to this recipe.')

        self.target_user = target_user


class RevokeShareForm(FlaskForm):
    submit = SubmitField('Remove')
