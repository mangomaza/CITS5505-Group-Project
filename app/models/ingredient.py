from app.extensions import db


class Ingredient(db.Model):
    __tablename__ = 'ingredients'

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(
        db.Integer,
        db.ForeignKey('recipes.id', ondelete='CASCADE'),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50), nullable=True)
    unit = db.Column(db.String(30), nullable=True)
    position = db.Column(db.Integer, nullable=False)

    recipe = db.relationship(
        'Recipe',
        backref=db.backref(
            'ingredients',
            order_by='Ingredient.position',
            cascade='all, delete-orphan',
            lazy=True,
        ),
    )

    def __repr__(self):
        return f'<Ingredient {self.position} {self.name!r}>'
