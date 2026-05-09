# Ingredient thumbnail placeholders

These folders hold the pool of AI-generated ingredient thumbnail images shown
on the recipe detail page. JS randomly picks one per ingredient based on the
recipe category.

## Expected structure

```
ingredients/
  cocktail/
    1.jpg  ... 6.jpg   (cocktail-themed: ice, citrus, spirits, shaker, bar tools, garnish)
  food/
    1.jpg  ... 6.jpg   (food-themed: herbs, vegetables, grains, dairy, meat, spices)
```

## Pool size

The pool is currently set to **6 images per category** (`INGREDIENT_POOL_SIZE = 6`
in `static/js/recipe_detail.js`). Adjust that constant if you add more.

## Fallback

If a file is missing (404) the ingredient row falls back to the placehold.co
letter-initial tile already baked into the template.
