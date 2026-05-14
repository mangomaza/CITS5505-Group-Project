import os
import threading
import time
import unittest

from dotenv import load_dotenv

# Load SECRET_KEY (and anything else) from .env, same as app.py does.
load_dotenv()

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from werkzeug.serving import make_server

from app import create_app, db
from app.models.user import User
from app.models.recipe import Recipe
from app.models.rating import Rating
from app.models.shared_access import SharedAccess
from app.models.ingredient import Ingredient


BASE_URL = 'http://localhost:5001'
SELENIUM_DB_FILENAME = 'selenium_test.db'


class ServerThread(threading.Thread):
    # We use werkzeug.serving.make_server on a daemon thread instead of
    # multiprocessing because Python 3.13 can't pickle Flask apps across
    # processes on Windows. Flask handles app context per-request on its own
    # threads, so we don't push one here.
    def __init__(self, app):
        super().__init__(daemon=True)
        self.server = make_server('localhost', 5001, app)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


def wait_for_server(timeout=5.0):
    import urllib.request
    import urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(BASE_URL + '/', timeout=0.5)
            return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError('Test server did not start in time.')


class SeleniumSystemTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        instance_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        cls.db_path = os.path.join(instance_dir, SELENIUM_DB_FILENAME)
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

        cls.app = create_app('selenium')
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()

        cls.server = ServerThread(cls.app)
        cls.server.start()
        wait_for_server()

        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1280,900')
        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.driver.implicitly_wait(0)
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        cls.server.shutdown()
        try:
            db.drop_all()
        except Exception:
            pass
        try:
            cls.app_context.pop()
        except (AssertionError, RuntimeError):
            pass
        if os.path.exists(cls.db_path):
            try:
                os.remove(cls.db_path)
            except OSError:
                pass

    def setUp(self):
        # Clean tables between tests in FK-safe order, keep a fresh seed user.
        db.session.rollback()
        for model in (Rating, SharedAccess, Ingredient, Recipe, User):
            db.session.query(model).delete()
        db.session.commit()
        db.session.expire_all()

        self.seed_user = User(username='seeduser', email='seed@example.com')
        self.seed_user.set_password('password123')
        db.session.add(self.seed_user)
        db.session.commit()
        self.seed_user_id = self.seed_user.id

        self.driver.delete_all_cookies()

    # ---------- helpers ----------

    def go(self, path):
        self.driver.get(BASE_URL + path)

    def fill(self, name, value):
        # We set values via JavaScript because chromedriver's send_keys
        # silently drops keystrokes on this layout under headless mode.
        el = self.driver.find_element(By.NAME, name)
        self.driver.execute_script(
            "arguments[0].value = arguments[1];"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            el, value
        )

    def click_submit_in_form(self, form_locator=(By.TAG_NAME, 'form')):
        form = self.driver.find_element(*form_locator)
        button = form.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]')
        # JS click bypasses the sticky navbar overlay but still triggers
        # HTML5 form validation, since it dispatches a real click event.
        self.driver.execute_script('arguments[0].click();', button)

    def login_via_ui(self, email, password='password123'):
        self.go('/auth/login')
        self.fill('email', email)
        self.fill('password', password)
        self.click_submit_in_form()
        self.wait.until(EC.url_contains('/'))

    def logged_in_marker(self):
        # base.html shows a logout form inside the navbar when logged in.
        try:
            self.driver.find_element(By.CSS_SELECTOR, 'form[action$="/auth/logout"]')
            return True
        except NoSuchElementException:
            return False

    # ---------- 1. Signup happy path ----------
    def test_signup_creates_account(self):
        self.go('/auth/signup')
        self.fill('username', 'aliceuser')
        self.fill('email', 'alice@example.com')
        self.fill('password', 'password123')
        self.fill('confirm_password', 'password123')
        self.click_submit_in_form()

        self.wait.until(lambda d: self.logged_in_marker())

        user = User.query.filter_by(email='alice@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'aliceuser')

    # ---------- 2. Login happy path ----------
    def test_login_with_correct_password(self):
        self.login_via_ui('seed@example.com')
        self.assertTrue(self.logged_in_marker())

    # ---------- 3. Login with wrong password shows flash ----------
    def test_login_with_wrong_password_shows_error(self):
        self.go('/auth/login')
        self.fill('email', 'seed@example.com')
        self.fill('password', 'wrong-password')
        self.click_submit_in_form()

        flash = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.alert-danger'))
        )
        self.assertIn('Invalid email or password.', flash.text)
        self.assertFalse(self.logged_in_marker())

    # ---------- 4. Logout ----------
    def test_logout_ends_session(self):
        self.login_via_ui('seed@example.com')
        logout_form = self.driver.find_element(
            By.CSS_SELECTOR, 'form[action$="/auth/logout"]'
        )
        button = logout_form.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        self.driver.execute_script('arguments[0].click();', button)
        self.wait.until(lambda d: not self.logged_in_marker())
        self.assertFalse(self.logged_in_marker())

    # ---------- 5. HTML5 required blocks empty signup submit (client layer) ----------
    def test_signup_html5_required_blocks_empty_submit(self):
        self.go('/auth/signup')
        self.click_submit_in_form()

        # HTML5 keeps us on the same page, no user created.
        self.assertIn('/auth/signup', self.driver.current_url)
        username = self.driver.find_element(By.NAME, 'username')
        is_invalid = self.driver.execute_script(
            'return !arguments[0].checkValidity();', username
        )
        self.assertTrue(is_invalid)
        self.assertEqual(User.query.filter_by(username='').count(), 0)

    # ---------- 6. Unauthenticated user redirected from /recipe/create ----------
    def test_unauthenticated_user_redirected_from_create_recipe(self):
        self.go('/recipe/create')
        self.wait.until(EC.url_contains('/auth/login'))
        self.assertIn('/auth/login', self.driver.current_url)

    # ---------- 7. Create a recipe end-to-end ----------
    def test_create_recipe_persists_row(self):
        self.login_via_ui('seed@example.com')
        self.go('/recipe/create')

        self.fill('name', 'Selenium Spritz')
        self.fill('description', 'A bright drink for tests.')
        # Category is a select.
        from selenium.webdriver.support.ui import Select
        Select(self.driver.find_element(By.NAME, 'category')).select_by_value('cocktail')
        self.fill('glass', 'Wine glass')
        self.fill('instructions', 'Combine ingredients over ice and stir.')

        # Pick non-alcoholic and public via radio buttons (JS click is robust
        # against the sticky navbar overlay).
        self.driver.execute_script(
            "document.querySelector('input[name=\"is_alcoholic\"][value=\"false\"]').click();"
        )
        self.driver.execute_script(
            "document.querySelector('input[name=\"visibility\"][value=\"public\"]').click();"
        )

        self.fill('ingredient_name', 'Soda water')
        self.fill('ingredient_quantity', '60')
        self.fill('ingredient_unit', 'ml')

        self.click_submit_in_form((By.CSS_SELECTOR, 'form[enctype="multipart/form-data"]'))

        self.wait.until(
            lambda d: Recipe.query.filter_by(name='Selenium Spritz').first() is not None
        )
        recipe = Recipe.query.filter_by(name='Selenium Spritz').first()
        self.assertEqual(recipe.creator_id, self.seed_user_id)

    # ---------- 8. Share a recipe with another user ----------
    def test_share_recipe_creates_grant(self):
        viewer = User(username='vieweruser', email='viewer@example.com')
        viewer.set_password('password123')
        db.session.add(viewer)

        recipe = Recipe(
            name='Private For Share',
            description='To share.',
            category='cocktail',
            glass='Coupe',
            is_alcoholic=False,
            instructions='Just shake.',
            is_public=False,
            creator_id=self.seed_user_id,
        )
        db.session.add(recipe)
        db.session.commit()
        recipe_id = recipe.id
        viewer_id = viewer.id

        self.login_via_ui('seed@example.com')
        self.go('/share')

        from selenium.webdriver.support.ui import Select
        Select(self.driver.find_element(By.NAME, 'recipe_id')).select_by_value(str(recipe_id))
        self.fill('username', 'vieweruser')
        self.click_submit_in_form(
            (By.CSS_SELECTOR, 'form[action$="/share"]')
        )

        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.alert-success'))
        )
        from app.models.shared_access import SharedAccess
        # End the test thread's transaction so we can read the row the
        # server thread just inserted.
        db.session.rollback()
        grant = SharedAccess.query.filter_by(
            recipe_id=recipe_id, shared_with_user_id=viewer_id
        ).first()
        self.assertIsNotNone(grant)

    # ---------- 9. Rate a recipe via the JSON endpoint (AJAX layer) ----------
    def test_rate_recipe_via_ajax(self):
        recipe = Recipe(
            name='Rate Me',
            description='For rating.',
            category='cocktail',
            glass='Tumbler',
            is_alcoholic=False,
            instructions='Pour and serve.',
            is_public=True,
            creator_id=self.seed_user_id,
        )
        db.session.add(recipe)

        rater = User(username='rater', email='rater@example.com')
        rater.set_password('password123')
        db.session.add(rater)
        db.session.commit()
        recipe_id = recipe.id

        self.login_via_ui('rater@example.com')
        self.go(f'/recipes/{recipe_id}')

        self.driver.execute_script(
            """
            const recipeId = arguments[0];
            fetch(`/recipes/${recipeId}/rate`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({stars: 4}),
            });
            """,
            recipe_id,
        )

        def rating_persisted():
            from app.models.rating import Rating
            return Rating.query.filter_by(recipe_id=recipe_id).first() is not None

        self.wait.until(lambda d: rating_persisted())

        from app.models.rating import Rating
        rating = Rating.query.filter_by(recipe_id=recipe_id).first()
        self.assertEqual(rating.stars, 4)

    # ---------- 10. 403 page shown for private recipe to unrelated user ----------
    def test_403_renders_for_private_recipe_unrelated_user(self):
        recipe = Recipe(
            name='Private Drink',
            description='Owner only.',
            category='cocktail',
            glass='Coupe',
            is_alcoholic=False,
            instructions='Secret.',
            is_public=False,
            creator_id=self.seed_user_id,
        )
        intruder = User(username='intruder', email='intruder@example.com')
        intruder.set_password('password123')
        db.session.add_all([recipe, intruder])
        db.session.commit()
        recipe_id = recipe.id

        self.login_via_ui('intruder@example.com')
        self.go(f'/recipes/{recipe_id}')

        self.wait.until(lambda d: '403' in d.page_source or 'Forbidden' in d.page_source)
        self.assertTrue('403' in self.driver.page_source or 'Forbidden' in self.driver.page_source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
