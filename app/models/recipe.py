from datetime import datetime
from app.extensions import db


class Recipe(db.Model):
    __tablename__ = 'recipes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(20), nullable=False)
    subcategory = db.Column(db.String(80), nullable=True)
    cuisine = db.Column(db.String(50), nullable=True)
    glass = db.Column(db.String(50), nullable=True)
    is_alcoholic = db.Column(db.Boolean, default=False, nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=True)
    image_mime = db.Column(db.String(50), nullable=True)
    instructions = db.Column(db.Text, nullable=False)
    is_public = db.Column(db.Boolean, default=True, nullable=False)
    source = db.Column(db.String(10), default='user', nullable=False)
    external_source = db.Column(db.String(20), nullable=True)
    external_id = db.Column(db.String(20), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    creator = db.relationship('User', backref=db.backref('recipes', lazy=True))

    __table_args__ = (
        db.Index(
            'ix_recipes_creator_external',
            'creator_id', 'external_source', 'external_id',
            unique=True,
            sqlite_where=db.text('external_id IS NOT NULL'),
        ),
    )

    def __repr__(self):
        return f'<Recipe {self.id} {self.name!r}>'
