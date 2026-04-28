from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

USERS = [
    ('asadm123456', 'asad@test.com', 'Asadpass123'),
    ('jianing123', 'jianing@test.com', 'Jianingpass123'),
    ('wendy123', 'wendy@test.com', 'Wendypass123'),
    ('wenmin123', 'wenmin@test.com', 'Wenminpass123'),
]


def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        for username, email, password in USERS:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)

        db.session.commit()
        print(f'Seeded {len(USERS)} users.')


if __name__ == '__main__':
    seed()
