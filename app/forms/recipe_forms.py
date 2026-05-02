import imghdr

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import RadioField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'jpeg', 'png', 'gif', 'webp'}


class CreateRecipeForm(FlaskForm):
    name = StringField(
        'Recipe name',
        validators=[
            DataRequired(message='Please enter a recipe name.'),
            Length(max=150, message='Recipe name must be 150 characters or fewer.'),
        ],
    )
    description = TextAreaField(
        'Description',
        validators=[Length(max=1000, message='Description must be 1000 characters or fewer.')],
    )
    category = SelectField(
        'Category',
        choices=[
            ('', 'Select a category'),
            ('cocktail', 'Cocktail'),
            ('food', 'Food'),
        ],
        validators=[DataRequired(message='Please choose a category.')],
    )
    glass = StringField(
        'Glass type',
        validators=[Length(max=50, message='Glass type must be 50 characters or fewer.')],
    )
    instructions = TextAreaField(
        'Instructions',
        validators=[
            DataRequired(message='Please add the recipe instructions.'),
            Length(max=10000, message='Instructions must be 10000 characters or fewer.'),
        ],
    )
    visibility = RadioField(
        'Visibility',
        choices=[
            ('public', 'Public'),
            ('private', 'Private'),
        ],
        default='public',
        validators=[DataRequired(message='Please choose whether the recipe is public or private.')],
    )
    image = FileField('Photo')
    submit = SubmitField('Create Recipe')

    def validate_image(self, field):
        upload = field.data
        if upload is None or not getattr(upload, 'filename', ''):
            return

        stream = upload.stream
        current_pos = stream.tell()
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(0)

        if size > MAX_IMAGE_BYTES:
            stream.seek(current_pos)
            raise ValidationError('Image must be 5 MB or smaller.')

        header = stream.read(512)
        stream.seek(0)
        image_type = imghdr.what(None, header)
        if image_type == 'jpg':
            image_type = 'jpeg'

        mimetype = (upload.mimetype or '').lower()
        if image_type not in ALLOWED_IMAGE_TYPES or not mimetype.startswith('image/'):
            stream.seek(current_pos)
            raise ValidationError('Please upload a valid image file.')

        stream.seek(current_pos)
