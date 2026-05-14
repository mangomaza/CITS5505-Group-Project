import os
import unittest
from io import BytesIO

from dotenv import load_dotenv

# Load SECRET_KEY (and anything else) from .env, same as app.py does.
load_dotenv()

from app import create_app, db
from app.models.user import User
from app.models.recipe import Recipe, can_view_recipe
from app.models.ingredient import Ingredient
from app.models.rating import Rating
from app.models.shared_access import SharedAccess
from app.routes.main_routes import get_rating_summary


class IssueUnitTests(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

            self.owner = User(username='owner', email='owner@example.com')
            self.owner.set_password('password123')

            self.shared_user = User(username='shareduser', email='shared@example.com')
            self.shared_user.set_password('password123')

            self.unrelated_user = User(username='unrelated', email='unrelated@example.com')
            self.unrelated_user.set_password('password123')

            db.session.add_all([self.owner, self.shared_user, self.unrelated_user])
            db.session.commit()

            self.private_recipe = Recipe(
                name='Private Test Recipe',
                description='Private recipe used for share tests.',
                category='cocktail',
                glass='Coupe',
                is_alcoholic=False,
                instructions='Shake and serve.',
                is_public=False,
                creator_id=self.owner.id,
            )

            self.public_recipe = Recipe(
                name='Public Test Recipe',
                description='Public recipe used for rating tests.',
                category='cocktail',
                glass='Highball',
                is_alcoholic=False,
                instructions='Mix and serve.',
                is_public=True,
                creator_id=self.owner.id,
            )

            db.session.add_all([self.private_recipe, self.public_recipe])
            db.session.commit()

            self.owner_id = self.owner.id
            self.shared_user_id = self.shared_user.id
            self.unrelated_user_id = self.unrelated_user.id
            self.private_recipe_id = self.private_recipe.id
            self.public_recipe_id = self.public_recipe.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, email, password='password123'):
        return self.client.post(
            '/auth/login',
            data={'email': email, 'password': password},
            follow_redirects=True,
        )

    def valid_recipe_form_data(self):
        return {
            'name': 'Image Validation Recipe',
            'description': 'Testing image upload validation.',
            'category': 'cocktail',
            'glass': 'Martini',
            'is_alcoholic': 'false',
            'visibility': 'public',
            'instructions': 'Mix everything and serve.',
            'ingredient_name': ['Lime juice'],
            'ingredient_quantity': ['30'],
            'ingredient_unit': ['ml'],
        }

    # 1. Helper coverage: visibility matrix
    def test_can_view_recipe_helper_matrix(self):
        with self.app.app_context():
            private_recipe = db.session.get(Recipe, self.private_recipe_id)
            public_recipe = db.session.get(Recipe, self.public_recipe_id)
            owner = db.session.get(User, self.owner_id)
            shared_user = db.session.get(User, self.shared_user_id)
            unrelated_user = db.session.get(User, self.unrelated_user_id)

            self.assertTrue(can_view_recipe(private_recipe, owner))
            self.assertFalse(can_view_recipe(private_recipe, shared_user))
            self.assertFalse(can_view_recipe(private_recipe, unrelated_user))
            self.assertTrue(can_view_recipe(public_recipe, unrelated_user))

            grant = SharedAccess(
                recipe_id=self.private_recipe_id,
                shared_with_user_id=self.shared_user_id,
                granted_by_user_id=self.owner_id,
            )
            db.session.add(grant)
            db.session.commit()

            self.assertTrue(can_view_recipe(private_recipe, shared_user))
            self.assertFalse(can_view_recipe(private_recipe, unrelated_user))

    # 2. Signup duplicate username (server + db uniqueness)
    def test_signup_rejects_duplicate_username(self):
        response = self.client.post(
            '/auth/signup',
            data={
                'username': 'owner',
                'email': 'new@example.com',
                'password': 'password123',
                'confirm_password': 'password123',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This username is already taken.', response.data)

    # 3. Signup duplicate email
    def test_signup_rejects_duplicate_email(self):
        response = self.client.post(
            '/auth/signup',
            data={
                'username': 'newuser',
                'email': 'owner@example.com',
                'password': 'password123',
                'confirm_password': 'password123',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This email is already registered.', response.data)

    # 4. Share with self rejected
    def test_share_rejects_self(self):
        self.login('owner@example.com')

        response = self.client.post(
            '/share',
            data={'recipe_id': self.private_recipe_id, 'username': 'owner'},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You cannot share a recipe with yourself.', response.data)

        with self.app.app_context():
            grant = SharedAccess.query.filter_by(
                recipe_id=self.private_recipe_id,
                shared_with_user_id=self.owner_id,
            ).first()
            self.assertIsNone(grant)

    # 5. Share duplicate grant rejected
    def test_share_rejects_duplicate_grant(self):
        with self.app.app_context():
            grant = SharedAccess(
                recipe_id=self.private_recipe_id,
                shared_with_user_id=self.shared_user_id,
                granted_by_user_id=self.owner_id,
            )
            db.session.add(grant)
            db.session.commit()

        self.login('owner@example.com')

        response = self.client.post(
            '/share',
            data={'recipe_id': self.private_recipe_id, 'username': 'shareduser'},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'That user already has access to this recipe.', response.data)

        with self.app.app_context():
            grants = SharedAccess.query.filter_by(
                recipe_id=self.private_recipe_id,
                shared_with_user_id=self.shared_user_id,
            ).all()
            self.assertEqual(len(grants), 1)

    # 6. Image upload type validator
    def test_create_recipe_rejects_non_image_upload(self):
        self.login('owner@example.com')

        data = self.valid_recipe_form_data()
        data['image'] = (BytesIO(b'This is not an image.'), 'notes.txt', 'text/plain')

        response = self.client.post(
            '/recipe/create',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please upload a valid image file.', response.data)

        with self.app.app_context():
            recipe = Recipe.query.filter_by(name='Image Validation Recipe').first()
            self.assertIsNone(recipe)

    # 7. Image upload size validator (5 MB cap, stays under MAX_CONTENT_LENGTH of 6 MB)
    def test_create_recipe_rejects_oversized_image(self):
        self.login('owner@example.com')

        oversized_bytes = b'x' * (5 * 1024 * 1024 + 1)

        data = self.valid_recipe_form_data()
        data['image'] = (BytesIO(oversized_bytes), 'large.png', 'image/png')

        response = self.client.post(
            '/recipe/create',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Image must be 5 MB or smaller.', response.data)

        with self.app.app_context():
            recipe = Recipe.query.filter_by(name='Image Validation Recipe').first()
            self.assertIsNone(recipe)

    # 8. Rating summary helper
    def test_get_rating_summary_average_and_count(self):
        with self.app.app_context():
            db.session.add_all([
                Rating(recipe_id=self.public_recipe_id, user_id=self.shared_user_id, stars=4),
                Rating(recipe_id=self.public_recipe_id, user_id=self.unrelated_user_id, stars=5),
            ])
            db.session.commit()

            average, count = get_rating_summary(self.public_recipe_id)

            self.assertEqual(average, 4.5)
            self.assertEqual(count, 2)

    # 9. NEW: rate endpoint allows one row per user (second submit updates the first)
    def test_rate_endpoint_one_rating_per_user(self):
        self.login('shared@example.com')

        first = self.client.post(
            f'/recipes/{self.public_recipe_id}/rate',
            json={'stars': 3},
        )
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.get_json()['success'])

        second = self.client.post(
            f'/recipes/{self.public_recipe_id}/rate',
            json={'stars': 5},
        )
        self.assertEqual(second.status_code, 200)
        payload = second.get_json()
        self.assertEqual(payload['user_rating'], 5)
        self.assertEqual(payload['count'], 1)

        with self.app.app_context():
            ratings = Rating.query.filter_by(
                recipe_id=self.public_recipe_id,
                user_id=self.shared_user_id,
            ).all()
            self.assertEqual(len(ratings), 1)
            self.assertEqual(ratings[0].stars, 5)

    # 10. NEW: edit recipe blocks a non-owner with 403
    def test_edit_recipe_blocks_non_owner(self):
        self.login('unrelated@example.com')

        response = self.client.get(f'/recipes/{self.private_recipe_id}/edit')
        self.assertEqual(response.status_code, 403)

        post_response = self.client.post(
            f'/recipes/{self.private_recipe_id}/edit',
            data={
                'name': 'Hijacked Name',
                'description': '',
                'category': 'cocktail',
                'glass': 'Coupe',
                'is_alcoholic': 'false',
                'visibility': 'private',
                'instructions': 'Trying to overwrite.',
            },
        )
        self.assertEqual(post_response.status_code, 403)

        with self.app.app_context():
            recipe = db.session.get(Recipe, self.private_recipe_id)
            self.assertEqual(recipe.name, 'Private Test Recipe')


if __name__ == '__main__':
    unittest.main(verbosity=2)
