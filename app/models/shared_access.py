from datetime import datetime, timezone
from app import db


class SharedAccess(db.Model):
    __tablename__ = 'shared_access'

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(
        db.Integer,
        db.ForeignKey('recipes.id', ondelete='CASCADE'),
        nullable=False,
    )
    shared_with_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    granted_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    recipe = db.relationship(
        'Recipe',
        backref=db.backref('shared_access_grants', lazy=True, cascade='all, delete-orphan'),
    )
    shared_with = db.relationship(
        'User',
        foreign_keys=[shared_with_user_id],
        backref=db.backref('shared_with_me', lazy=True),
    )
    granted_by = db.relationship(
        'User',
        foreign_keys=[granted_by_user_id],
        backref=db.backref('shared_by_me', lazy=True),
    )

    __table_args__ = (
        db.UniqueConstraint(
            'recipe_id', 'shared_with_user_id',
            name='uq_shared_access_recipe_user',
        ),
    )

    def __repr__(self):
        return f'<SharedAccess recipe={self.recipe_id} user={self.shared_with_user_id}>'
