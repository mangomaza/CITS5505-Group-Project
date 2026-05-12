"""Wipe the database and load showcase data for demos.

Walks every workflow: signup is skipped (users prebuilt), but logged-in
users will see their own recipes, recipes shared with them, public
community recipes on the home page, a populated top-rated list, and at
least one private recipe ready to share onward.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from app import create_app
from app.extensions import db
from app.models import User, Recipe, Ingredient, Rating, SharedAccess

app = create_app()

AVATAR_DIR = Path('app/static/images/seed_avatars')
NOW = datetime.now(timezone.utc)


def days_ago(n):
    return NOW - timedelta(days=n)


# (username, email, password, avatar_filename)
USERS = [
    ('mangomaza', 'asad@test.com', 'Asadpass123', 'mangomaza.png'),
    ('jianing', 'jianing@test.com', 'Jianingpass123', 'jianing.png'),
    ('wendy', 'wendy@test.com', 'Wendypass123', 'wendy.png'),
    ('wenmin', 'wenmin@test.com', 'Wenminpass123', 'wenmin.png'),
]


# External recipes pulled from TheCocktailDB and TheMealDB. Each entry
# names the owner so different users have content of their own.
EXTERNAL_RECIPES = [
    # (owner_username, category, source, external_id, is_public, created_days_ago)
    ('mangomaza', 'cocktail', 'thecocktaildb', '11007', True, 9),   # Margarita
    ('mangomaza', 'cocktail', 'thecocktaildb', '11000', True, 8),   # Mojito
    ('mangomaza', 'cocktail', 'thecocktaildb', '11001', True, 7),   # Old Fashioned
    ('mangomaza', 'cocktail', 'thecocktaildb', '11004', True, 6),   # Whiskey Sour
    ('mangomaza', 'food',     'themealdb',     '52772', True, 5),   # Teriyaki Chicken Casserole
    ('jianing',   'food',     'themealdb',     '52874', True, 5),   # Beef and Mustard Pie
    ('wendy',     'food',     'themealdb',     '52844', True, 4),   # Lasagne (id 52844 returns Lasagne)
    ('wenmin',    'food',     'themealdb',     '52773', True, 4),   # Honey Teriyaki Salmon
]


# Hand-authored recipes so reviewers see the create-form path too.
# Mix of public and private to exercise both visibility branches.
HAND_RECIPES = [
    {
        'owner': 'mangomaza',
        'name': "Mangomaza's Weeknight Dal",
        'category': 'food',
        'is_public': True,
        'is_alcoholic': False,
        'description': 'A quick lentil dal that comes together in under 30 minutes. Good with rice or warm naan.',
        'instructions': (
            'Rinse the lentils until the water runs mostly clear. '
            'Toast the cumin and mustard seeds in oil until they pop, then add the onion and cook until soft. '
            'Stir in garlic, ginger, and the spices, then add the lentils with three cups of water. '
            'Simmer for about 20 minutes, mashing some of the lentils against the side of the pot. '
            'Season with salt, finish with a squeeze of lemon, and top with fresh coriander.'
        ),
        'ingredients': [
            ('Red lentils', '1', 'cup'),
            ('Yellow onion', '1', None),
            ('Garlic', '3', 'cloves'),
            ('Ginger', '1', 'thumb'),
            ('Cumin seeds', '1', 'tsp'),
            ('Mustard seeds', '1', 'tsp'),
            ('Turmeric', '1/2', 'tsp'),
            ('Lemon', '1/2', None),
            ('Coriander', 'a handful', None),
        ],
        'days_ago': 3,
    },
    {
        'owner': 'wendy',
        'name': 'Family Pavlova',
        'category': 'food',
        'is_public': False,
        'is_alcoholic': False,
        'description': 'Mum\'s pavlova recipe. Crisp outside, marshmallow centre. Keep this one in the family.',
        'instructions': (
            'Whip the egg whites with a pinch of salt until stiff. '
            'Add the sugar a spoonful at a time, then fold through the cornflour and vinegar. '
            'Spread onto a lined tray in a rough circle and bake at 120C for ninety minutes, then leave to cool in the oven. '
            'Top with whipped cream and fresh fruit just before serving.'
        ),
        'ingredients': [
            ('Egg whites', '6', None),
            ('Caster sugar', '1.5', 'cups'),
            ('Cornflour', '1', 'tbsp'),
            ('White vinegar', '1', 'tsp'),
            ('Thickened cream', '300', 'ml'),
            ('Strawberries', '1', 'punnet'),
            ('Passionfruit', '2', None),
        ],
        'days_ago': 2,
    },
    {
        'owner': 'mangomaza',
        'name': 'Late-night Espresso Martini',
        'category': 'cocktail',
        'is_public': False,
        'is_alcoholic': True,
        'glass': 'Martini glass',
        'description': 'My after-dinner version. Tweaked the ratio so it leans bitter rather than sweet.',
        'instructions': (
            'Pull a fresh shot of espresso and let it cool for a minute. '
            'Add the vodka, coffee liqueur, and espresso to a shaker with plenty of ice. '
            'Shake hard for at least fifteen seconds to get a good foam. '
            'Double strain into a chilled martini glass and float three coffee beans on top.'
        ),
        'ingredients': [
            ('Vodka', '45', 'ml'),
            ('Coffee liqueur', '20', 'ml'),
            ('Espresso', '30', 'ml'),
            ('Coffee beans', '3', None),
        ],
        'days_ago': 1,
    },
    {
        'owner': 'jianing',
        'name': 'Secret Pho Broth',
        'category': 'food',
        'is_public': False,
        'is_alcoholic': False,
        'description': 'Beef pho broth the way my grandmother taught me. Slow but worth it.',
        'instructions': (
            'Char the onion and ginger over an open flame until blackened in patches. '
            'Blanch the bones in boiling water for five minutes, drain, and rinse. '
            'Add the bones, charred aromatics, and spices to a large pot, cover with water, and simmer for at least six hours. '
            'Skim regularly. Strain the broth and season with fish sauce and rock sugar to taste.'
        ),
        'ingredients': [
            ('Beef knuckle bones', '2', 'kg'),
            ('Yellow onion', '2', None),
            ('Ginger', '1', 'large piece'),
            ('Star anise', '4', None),
            ('Cinnamon stick', '1', None),
            ('Cloves', '6', None),
            ('Fish sauce', '3', 'tbsp'),
            ('Rock sugar', '2', 'tbsp'),
        ],
        'days_ago': 1,
    },
]


# Ratings keyed by recipe name. Cannot include the owner.
RATINGS = {
    'Margarita': [('wendy', 5), ('jianing', 4), ('wenmin', 4)],
    'Mojito': [('wendy', 5), ('wenmin', 5)],
    'Old Fashioned': [('jianing', 5)],
    'Whiskey Sour': [('wendy', 3)],
    'Teriyaki Chicken Casserole': [('jianing', 3), ('wendy', 4)],
    'Beef and Mustard Pie': [('mangomaza', 4), ('wenmin', 5)],
    'Lasagne': [('mangomaza', 5), ('jianing', 4)],
    "Mangomaza's Weeknight Dal": [('wendy', 4), ('jianing', 4)],
}


# Private recipe shares, by recipe name.
SHARES = [
    ('Family Pavlova', ['mangomaza', 'jianing']),
    ('Late-night Espresso Martini', ['wenmin']),
    ('Secret Pho Broth', ['mangomaza']),
]


COCKTAIL_URL = 'https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i={}'
MEAL_URL = 'https://www.themealdb.com/api/json/v1/1/lookup.php?i={}'


def load_avatar(filename):
    path = AVATAR_DIR / filename
    if not path.exists():
        print(f'  warning: avatar missing: {path}')
        return None, None
    data = path.read_bytes()
    mime = 'image/png' if filename.lower().endswith('.png') else 'image/jpeg'
    return data, mime


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


def fetch_external(category, external_id):
    if category == 'cocktail':
        url = COCKTAIL_URL.format(external_id)
        json_key, name_key, image_key, id_key = 'drinks', 'strDrink', 'strDrinkThumb', 'idDrink'
    else:
        url = MEAL_URL.format(external_id)
        json_key, name_key, image_key, id_key = 'meals', 'strMeal', 'strMealThumb', 'idMeal'
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()[json_key][0], name_key, image_key, id_key
    except Exception as e:
        print(f'  warning: could not fetch {url}: {e}')
        return None, None, None, None


def build_external_recipe(owner, category, source, external_id, is_public, created_at):
    data, name_key, image_key, _id_key = fetch_external(category, external_id)
    if data is None:
        return None

    image_data, image_mime = fetch_image(data.get(image_key))

    recipe = Recipe(
        name=data[name_key],
        description=None,
        category=category,
        subcategory=data.get('strCategory'),
        glass=data.get('strGlass'),
        is_alcoholic=(data.get('strAlcoholic') == 'Alcoholic'),
        image_data=image_data,
        image_mime=image_mime,
        instructions=data.get('strInstructions') or '',
        is_public=is_public,
        source='external',
        external_source=source,
        external_id=external_id,
        creator_id=owner.id,
        created_at=created_at,
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


def build_hand_recipe(owner, spec, created_at):
    recipe = Recipe(
        name=spec['name'],
        description=spec.get('description'),
        category=spec['category'],
        glass=spec.get('glass'),
        is_alcoholic=spec.get('is_alcoholic', False),
        instructions=spec['instructions'],
        is_public=spec['is_public'],
        source='user',
        creator_id=owner.id,
        created_at=created_at,
    )
    db.session.add(recipe)
    db.session.flush()

    for position, (name, quantity, unit) in enumerate(spec['ingredients'], start=1):
        db.session.add(Ingredient(
            recipe_id=recipe.id,
            name=name,
            quantity=quantity,
            unit=unit,
            position=position,
        ))
    return recipe


def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        users = {}
        for username, email, password, avatar in USERS:
            avatar_data, avatar_mime = load_avatar(avatar)
            user = User(
                username=username,
                email=email,
                avatar_data=avatar_data,
                avatar_mime=avatar_mime,
            )
            user.set_password(password)
            db.session.add(user)
            users[username] = user
        db.session.commit()

        recipes_by_name = {}

        for owner_name, category, source, external_id, is_public, days in EXTERNAL_RECIPES:
            owner = users[owner_name]
            recipe = build_external_recipe(
                owner, category, source, external_id, is_public, days_ago(days)
            )
            if recipe is not None:
                recipes_by_name[recipe.name] = recipe

        for spec in HAND_RECIPES:
            owner = users[spec['owner']]
            recipe = build_hand_recipe(owner, spec, days_ago(spec['days_ago']))
            recipes_by_name[recipe.name] = recipe

        db.session.commit()

        for recipe_name, entries in RATINGS.items():
            recipe = recipes_by_name.get(recipe_name)
            if recipe is None:
                continue
            for rater_name, stars in entries:
                db.session.add(Rating(
                    recipe_id=recipe.id,
                    user_id=users[rater_name].id,
                    stars=stars,
                ))

        for recipe_name, share_with in SHARES:
            recipe = recipes_by_name.get(recipe_name)
            if recipe is None:
                continue
            for target_name in share_with:
                db.session.add(SharedAccess(
                    recipe_id=recipe.id,
                    shared_with_user_id=users[target_name].id,
                    granted_by_user_id=recipe.creator_id,
                ))

        db.session.commit()

        print(f'Seeded {len(users)} users, {len(recipes_by_name)} recipes, '
              f'{sum(len(v) for v in RATINGS.values())} ratings, '
              f'{sum(len(v) for _, v in SHARES)} shares.')


if __name__ == '__main__':
    seed()
