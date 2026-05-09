import requests

from app import create_app
from app.extensions import db
from app.models import User, Recipe, Ingredient, Rating, SharedAccess

app = create_app()

USERS = [
    ('asadm123456', 'asad@test.com', 'Asadpass123'),
    ('jianing123', 'jianing@test.com', 'Jianingpass123'),
    ('wendy123', 'wendy@test.com', 'Wendypass123'),
    ('wenmin123', 'wenmin@test.com', 'Wenminpass123'),
]

SAMPLE_LOOKUPS = [
    {
        'category': 'cocktail',
        'url': 'https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i=11007',
        'source': 'cocktaildb',
        'json_key': 'drinks',
        'name_key': 'strDrink',
        'image_key': 'strDrinkThumb',
        'id_key': 'idDrink',
    },
    {
        'category': 'food',
        'url': 'https://www.themealdb.com/api/json/v1/1/lookup.php?i=52772',
        'source': 'mealdb',
        'json_key': 'meals',
        'name_key': 'strMeal',
        'image_key': 'strMealThumb',
        'id_key': 'idMeal',
    },
]


def fetch_image(url):
    if not url:
        return None, None
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        mime = r.headers.get('Content-Type', 'image/jpeg').split(';')[0].strip()
        return r.content, mime
    except Exception as e:
        print(f'  warning: could not fetch image {url}: {e}')
        return None, None


def build_recipe(spec, creator_id):
    try:
        r = requests.get(spec['url'], timeout=10)
        r.raise_for_status()
        data = r.json()[spec['json_key']][0]
    except Exception as e:
        print(f"  warning: could not fetch {spec['url']}: {e}")
        return None

    image_data, image_mime = fetch_image(data.get(spec['image_key']))

    recipe = Recipe(
        name=data[spec['name_key']],
        category=spec['category'],
        subcategory=data.get('strCategory'),
        glass=data.get('strGlass'),
        is_alcoholic=(data.get('strAlcoholic') == 'Alcoholic'),
        image_data=image_data,
        image_mime=image_mime,
        instructions=data.get('strInstructions') or '',
        is_public=True,
        source='user',
        external_source=spec['source'],
        external_id=data.get(spec['id_key']),
        creator_id=creator_id,
    )
    db.session.add(recipe)
    db.session.flush()

    position = 1
    for i in range(1, 21):
        name = (data.get(f'strIngredient{i}') or '').strip()
        if not name:
            continue
        qty = (data.get(f'strMeasure{i}') or '').strip() or None
        db.session.add(Ingredient(
            recipe_id=recipe.id,
            name=name,
            quantity=qty,
            position=position,
        ))
        position += 1

    return recipe


def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        users = []
        for username, email, password in USERS:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            users.append(user)
        db.session.commit()

        creator = users[0]
        recipes = []
        for spec in SAMPLE_LOOKUPS:
            recipe = build_recipe(spec, creator.id)
            if recipe is not None:
                recipes.append(recipe)
        db.session.commit()

        if recipes:
            db.session.add(Rating(
                recipe_id=recipes[0].id,
                user_id=users[1].id,
                stars=4,
                comment='Solid classic. A bit strong but tasty.',
            ))
            db.session.add(SharedAccess(
                recipe_id=recipes[0].id,
                shared_with_user_id=users[2].id,
                granted_by_user_id=creator.id,
            ))
            db.session.commit()

        print(f'Seeded {len(USERS)} users, {len(recipes)} recipes.')


if __name__ == '__main__':
    seed()
