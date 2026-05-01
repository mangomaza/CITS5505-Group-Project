from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError

from app.models import Recipe, SharedAccess, User


class ShareRecipeForm(FlaskForm):
    """Form for granting another user read access to one private recipe."""

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

    def set_recipe_choices(self, recipes):
        self.recipe_id.choices = [
            (recipe.id, recipe.name)
            for recipe in recipes
        ]

    def validate_recipe_id(self, field):
        if self.owner is None or getattr(self.owner, 'id', None) is None:
            raise ValidationError('You must be logged in to share a recipe.')

        recipe = Recipe.query.filter_by(id=field.data).first()
        if recipe is None:
            raise ValidationError('Selected recipe does not exist.')

        if recipe.creator_id != self.owner.id:
            raise ValidationError('You can only share recipes you created.')

        if recipe.is_public:
            raise ValidationError('Public recipes do not need an extra share grant.')

    def validate_username(self, field):
        if self.owner is None or getattr(self.owner, 'id', None) is None:
            raise ValidationError('You must be logged in to share a recipe.')

        target_username = (field.data or '').strip()
        field.data = target_username
        target_user = User.query.filter_by(username=target_username).first()

        if target_user is None:
            raise ValidationError('No user exists with that username.')

        if target_user.id == self.owner.id:
            raise ValidationError('You cannot share a recipe with yourself.')

        if not self.recipe_id.data:
            return

        existing_grant = SharedAccess.query.filter_by(
            recipe_id=self.recipe_id.data,
            shared_with_user_id=target_user.id,
        ).first()
        if existing_grant is not None:
            raise ValidationError('That user already has access to this recipe.')
