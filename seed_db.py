from app import create_app
from app.extensions import db
from app.models import User, Recipe, Ingredient

app = create_app()

USERS = [
    ('asadm123456', 'asad@test.com', 'Asadpass123'),
    ('jianing123', 'jianing@test.com', 'Jianingpass123'),
    ('wendy123', 'wendy@test.com', 'Wendypass123'),
    ('wenmin123', 'wenmin@test.com', 'Wenminpass123'),
]

SAMPLE_RECIPES = [
    {
        'name': 'House Margarita',
        'description': 'Classic margarita the way we like it at home.',
        'category': 'cocktail',
        'subcategory': 'Ordinary Drink',
        'glass': 'Cocktail glass',
        'is_alcoholic': True,
        'instructions': 'Rub the rim of the glass with lime, dip in salt. Shake the other ingredients with ice, strain into the glass.',
        'ingredients': [
            ('Tequila', '1 1/2 oz'),
            ('Triple sec', '1/2 oz'),
            ('Lime juice', '1 oz'),
            ('Salt', None),
        ],
    },
    {
        'name': 'Quick Garlic Pasta',
        'description': 'Weeknight pasta when there is nothing in the fridge.',
        'category': 'food',
        'subcategory': 'Pasta',
        'cuisine': 'Italian',
        'is_alcoholic': False,
        'instructions': 'Boil pasta. Meanwhile, gently fry sliced garlic in olive oil with chilli flakes. Toss the drained pasta in the oil, finish with parsley and parmesan.',
        'ingredients': [
            ('Spaghetti', '200 g'),
            ('Garlic cloves', '4'),
            ('Olive oil', '3 tbsp'),
            ('Chilli flakes', '1 tsp'),
            ('Parsley', 'small handful'),
            ('Parmesan', 'to serve'),
        ],
    },
]


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

        # Attribute the sample recipes to the first user
        creator = users[0]
        for data in SAMPLE_RECIPES:
            ingredients = data.pop('ingredients')
            recipe = Recipe(creator_id=creator.id, **data)
            db.session.add(recipe)
            db.session.flush()
            for i, (name, qty) in enumerate(ingredients, start=1):
                db.session.add(Ingredient(
                    recipe_id=recipe.id,
                    name=name,
                    quantity=qty,
                    position=i,
                ))
        db.session.commit()

        print(f'Seeded {len(USERS)} users and {len(SAMPLE_RECIPES)} recipes.')


if __name__ == '__main__':
    seed()
