from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import HiddenField, RadioField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import AnyOf, DataRequired, Length, Optional, Regexp, ValidationError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'jpeg', 'png', 'gif', 'webp'}


def _detect_image_type(header):
    if header.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if header.startswith((b'GIF87a', b'GIF89a')):
        return 'gif'
    if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
        return 'webp'
    return None


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
    is_alcoholic = RadioField(
        'Alcohol content',
        choices=[
            ('true', 'Alcoholic'),
            ('false', 'Non-alcoholic'),
        ],
        default='true',
        validators=[DataRequired(message='Please choose whether this recipe contains alcohol.')],
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
    external_source = HiddenField(
        validators=[
            Optional(),
            AnyOf(['thecocktaildb', 'themealdb'], message='Invalid recipe source.'),
        ],
    )
    external_id = HiddenField(
        validators=[
            Optional(),
            Length(max=20),
            Regexp(r'^[A-Za-z0-9_-]+$', message='Invalid recipe id.'),
        ],
    )
    external_image_url = HiddenField(
        validators=[
            Optional(),
            Length(max=300),
            Regexp(
                r'^https://(?:www\.)?(?:thecocktaildb|themealdb)\.com/images/[A-Za-z0-9/_.-]+$',
                message='Invalid recipe image source.',
            ),
        ],
    )
    submit = SubmitField('Save to mixtape')

    def validate(self, extra_validators=None):
        # For food recipes the alcohol radio is hidden, so default it to
        # non-alcoholic before WTForms enforces DataRequired.
        if (self.category.data or '').strip() == 'food' and not self.is_alcoholic.data:
            self.is_alcoholic.data = 'false'
        return super().validate(extra_validators=extra_validators)

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
        image_type = _detect_image_type(header)

        mimetype = (upload.mimetype or '').lower()
        if image_type not in ALLOWED_IMAGE_TYPES or not mimetype.startswith('image/'):
            stream.seek(current_pos)
            raise ValidationError('Please upload a valid image file.')

        stream.seek(current_pos)


class SaveExternalRecipeForm(FlaskForm):
    """Save a recipe drawn from an external API into the user's cookbook."""

    external_source = HiddenField(
        validators=[
            DataRequired(message='Missing recipe source.'),
            AnyOf(['thecocktaildb', 'themealdb'], message='Unknown recipe source.'),
        ],
    )
    external_id = HiddenField(
        validators=[
            DataRequired(message='Missing recipe id.'),
            Length(max=20, message='Recipe id is too long.'),
            Regexp(r'^[A-Za-z0-9_-]+$', message='Recipe id contains invalid characters.'),
        ],
    )
    visibility = HiddenField(
        validators=[
            DataRequired(message='Missing visibility.'),
            AnyOf(['public', 'private'], message='Visibility must be public or private.'),
        ],
    )
    confirm_duplicate = HiddenField()
