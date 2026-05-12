from datetime import datetime, timezone
from app import db


class Rating(db.Model):
    __tablename__ = 'ratings'

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(
        db.Integer,
        db.ForeignKey('recipes.id', ondelete='CASCADE'),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    stars = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    recipe = db.relationship(
        'Recipe',
        backref=db.backref('ratings', cascade='all, delete-orphan', lazy=True),
    )
    user = db.relationship('User', backref=db.backref('ratings', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('recipe_id', 'user_id', name='uq_ratings_recipe_user'),
    )

    def __repr__(self):
        return f'<Rating {self.stars}* recipe={self.recipe_id} user={self.user_id}>'
