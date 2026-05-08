import os
import time
import unittest
import threading
import tempfile
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from werkzeug.serving import make_server

from config import TestingConfig, config
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.recipe import Recipe
from app.models.ingredient import Ingredient
from app.models.rating import Rating
from app.models.shared_access import SharedAccess


localHost = "http://127.0.0.1:5001"


class ServerThread(threading.Thread):
    """
    Start the Flask test server in a separate thread.

    This follows the lecture idea of running the server separately for Selenium,
    but uses threading + make_server instead of multiprocessing because
    multiprocessing caused Flask app pickling errors on Python 3.13.
    """

    def __init__(self, app):
        super().__init__()
        self.server = make_server("127.0.0.1", 5001, app)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class SeleniumTests(unittest.TestCase):
    """
    Selenium WebDriver tests for the selected browser flows.

    This class follows the lecture structure:
    - create a test app
    - create a test database
    - add test data
    - start a local server
    - initialise a WebDriver
    - run browser-level tests
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "selenium_test.db"

        class SeleniumTestConfig(TestingConfig):
            TESTING = True
            WTF_CSRF_ENABLED = False
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls.db_path}"

        config["selenium"] = SeleniumTestConfig

        cls.testApp = create_app("selenium")
        cls.app_context = cls.testApp.app_context()
        cls.app_context.push()

        db.create_all()
        cls.add_test_data_to_db()

        cls.server_thread = ServerThread(cls.testApp)
        cls.server_thread.start()
        time.sleep(1)

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1280,1200")

        cls.driver = webdriver.Chrome(options=options)
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

        cls.server_thread.shutdown()
        cls.server_thread.join()

        db.session.remove()
        db.drop_all()
        db.engine.dispose()

        cls.app_context.pop()
        cls.temp_dir.cleanup()

    @classmethod
    def add_test_data_to_db(cls):
        owner = User(username="owner", email="owner@example.com")
        owner.set_password("password123")

        viewer = User(username="viewer", email="viewer@example.com")
        viewer.set_password("password123")

        db.session.add_all([owner, viewer])
        db.session.commit()

        private_recipe = Recipe(
            name="Private Selenium Recipe",
            description="Private recipe used for Selenium sharing test.",
            category="cocktail",
            glass="Coupe",
            is_alcoholic=False,
            instructions="Shake and serve.",
            is_public=False,
            creator_id=owner.id,
        )

        public_recipe = Recipe(
            name="Public Selenium Recipe",
            description="Public recipe used for Selenium rating test.",
            category="cocktail",
            glass="Highball",
            is_alcoholic=False,
            instructions="Mix and serve.",
            is_public=True,
            creator_id=owner.id,
        )

        db.session.add_all([private_recipe, public_recipe])
        db.session.commit()

        ingredient = Ingredient(
            recipe_id=public_recipe.id,
            name="Lime juice",
            quantity="30",
            unit="ml",
            position=1,
        )

        db.session.add(ingredient)
        db.session.commit()

        cls.owner_id = owner.id
        cls.viewer_id = viewer.id
        cls.private_recipe_id = private_recipe.id
        cls.public_recipe_id = public_recipe.id

    def setUp(self):
        self.driver.delete_all_cookies()

    def set_input_value(self, element_id, value):
        element = self.wait.until(
            EC.presence_of_element_located((By.ID, element_id))
        )

        self.driver.execute_script(
            """
            const element = arguments[0];
            const value = arguments[1];

            element.value = value;
            element.dispatchEvent(new Event("input", { bubbles: true }));
            element.dispatchEvent(new Event("change", { bubbles: true }));
            """,
            element,
            value,
        )

    def set_form_field(self, form, field_name, value):
        self.driver.execute_script(
            """
            const form = arguments[0];
            const fieldName = arguments[1];
            const value = arguments[2];

            let fields = form.querySelectorAll(`[name="${fieldName}"]`);

            if (fields.length === 0) {
                const input = document.createElement("input");
                input.type = "hidden";
                input.name = fieldName;
                input.value = value;
                form.appendChild(input);
                return;
            }

            const field = fields[0];

            if (field.type === "checkbox") {
                field.checked = Boolean(value);
            } else if (field.type === "radio") {
                const radio = form.querySelector(`[name="${fieldName}"][value="${value}"]`);
                if (radio) {
                    radio.checked = true;
                } else {
                    field.checked = true;
                }
            } else {
                field.value = value;
            }

            field.dispatchEvent(new Event("input", { bubbles: true }));
            field.dispatchEvent(new Event("change", { bubbles: true }));
            """,
            form,
            field_name,
            value,
        )

    def submit_form_by_action(self, action):
        form = self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, f"form[action='{action}']")
            )
        )

        self.driver.execute_script(
            """
            const form = arguments[0];
            HTMLFormElement.prototype.submit.call(form);
            """,
            form,
        )

    def submit_form_data_by_action(self, action, data):
        form = self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, f"form[action='{action}']")
            )
        )

        for field_name, value in data.items():
            if isinstance(value, list):
                for item in value:
                    self.set_form_field(form, field_name, item)
            else:
                self.set_form_field(form, field_name, value)

        self.driver.execute_script(
            """
            const form = arguments[0];
            HTMLFormElement.prototype.submit.call(form);
            """,
            form,
        )

    def login_through_browser(self, email="owner@example.com", password="password123"):
        self.driver.get(localHost + "/auth/login")

        self.set_input_value("loginEmail", email)
        self.set_input_value("loginPassword", password)

        self.submit_form_by_action("/auth/login")

        self.wait.until(lambda driver: "Logout" in driver.page_source)

    def test_signup_flow(self):
        unique_username = f"seleniumuser{int(time.time())}"
        unique_email = f"{unique_username}@example.com"

        self.driver.get(localHost + "/auth/signup")

        self.set_input_value("signupName", unique_username)
        self.set_input_value("signupEmail", unique_email)
        self.set_input_value("signupPassword", "password123")
        self.set_input_value("signupConfirm", "password123")

        self.submit_form_by_action("/auth/signup")

        self.wait.until(lambda driver: "Logout" in driver.page_source)

        user = User.query.filter_by(username=unique_username).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, unique_email)

    def test_login_flow(self):
        self.login_through_browser("owner@example.com", "password123")

        self.assertIn("Logout", self.driver.page_source)
        self.assertIn("owner", self.driver.page_source)

    def test_logout_flow(self):
        self.login_through_browser("owner@example.com", "password123")

        logout_form = self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "form[action='/auth/logout']")
            )
        )

        self.driver.execute_script(
            """
            const form = arguments[0];
            HTMLFormElement.prototype.submit.call(form);
            """,
            logout_form,
        )

        self.wait.until(
            lambda driver: "Login" in driver.page_source
            and "Sign Up" in driver.page_source
        )

        self.assertIn("Login", self.driver.page_source)
        self.assertIn("Sign Up", self.driver.page_source)

    def test_create_recipe_flow(self):
        self.login_through_browser("owner@example.com", "password123")

        recipe_name = f"Selenium Created Recipe {int(time.time())}"

        self.driver.get(localHost + "/recipe/create")

        self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "form[action='/recipe/create']")
            )
        )

        recipe_data = {
            "name": recipe_name,
            "description": "Created during Selenium system testing.",
            "category": "cocktail",
            "glass": "Martini",
            "is_alcoholic": "false",
            "visibility": "public",
            "instructions": "Add ingredients, mix well, and serve.",
            "ingredient_name": "Lime juice",
            "ingredient_quantity": "30",
            "ingredient_unit": "ml",
        }

        self.submit_form_data_by_action("/recipe/create", recipe_data)

        time.sleep(1)

        created_recipe = Recipe.query.filter_by(name=recipe_name).first()

        self.assertIsNotNone(created_recipe)
        self.assertEqual(created_recipe.creator_id, self.owner_id)

        ingredient = Ingredient.query.filter_by(recipe_id=created_recipe.id).first()

        self.assertIsNotNone(ingredient)
        self.assertEqual(ingredient.name, "Lime juice")

    def test_share_recipe_flow(self):
        self.login_through_browser("owner@example.com", "password123")

        self.driver.get(localHost + "/share")

        self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "form[action='/share']")
            )
        )

        share_data = {
            "recipe_id": str(self.private_recipe_id),
            "username": "viewer",
        }

        self.submit_form_data_by_action("/share", share_data)

        time.sleep(1)

        grant = SharedAccess.query.filter_by(
            recipe_id=self.private_recipe_id,
            shared_with_user_id=self.viewer_id,
            granted_by_user_id=self.owner_id,
        ).first()

        self.assertIsNotNone(grant)

    def test_rate_recipe_flow(self):
        self.login_through_browser("viewer@example.com", "password123")

        self.driver.get(localHost + f"/recipes/{self.public_recipe_id}")

        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        result = self.driver.execute_async_script(
            """
            const recipeId = arguments[0];
            const done = arguments[arguments.length - 1];

            fetch(`/recipes/${recipeId}/rate`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ stars: 5 })
            })
            .then(response => response.json().then(data => {
                done({
                    status: response.status,
                    data: data
                });
            }))
            .catch(error => {
                done({
                    status: 0,
                    error: String(error)
                });
            });
            """,
            self.public_recipe_id,
        )

        self.assertEqual(result["status"], 200)
        self.assertTrue(result["data"]["success"])

        rating = Rating.query.filter_by(
            recipe_id=self.public_recipe_id,
            user_id=self.viewer_id,
        ).first()

        self.assertIsNotNone(rating)
        self.assertEqual(rating.stars, 5)


if __name__ == "__main__":
    unittest.main()