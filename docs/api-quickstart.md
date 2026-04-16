# API Quickstart

We pull recipes from two free APIs: [TheCocktailDB](https://www.thecocktaildb.com/api.php) for drinks and [TheMealDB](https://www.themealdb.com/api.php) for food. Both use a test key of `1` in the URL, no signup or auth needed.

## Base URLs

```
https://www.thecocktaildb.com/api/json/v1/1/
https://www.themealdb.com/api/json/v1/1/
```

## Try it out

Paste any of these into your browser or use `curl` in the terminal.

**Search by name**

```
curl "https://www.thecocktaildb.com/api/json/v1/1/search.php?s=margarita"
curl "https://www.themealdb.com/api/json/v1/1/search.php?s=Arrabiata"
```

**Get a random recipe**

```
curl "https://www.thecocktaildb.com/api/json/v1/1/random.php"
curl "https://www.themealdb.com/api/json/v1/1/random.php"
```

**Lookup by ID**

```
curl "https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i=11007"
curl "https://www.themealdb.com/api/json/v1/1/lookup.php?i=52772"
```

**Filter by ingredient**

```
curl "https://www.thecocktaildb.com/api/json/v1/1/filter.php?i=Gin"
curl "https://www.themealdb.com/api/json/v1/1/filter.php?i=chicken_breast"
```

**Filter by category**

```
curl "https://www.thecocktaildb.com/api/json/v1/1/filter.php?c=Cocktail"
curl "https://www.themealdb.com/api/json/v1/1/filter.php?c=Seafood"
```

**List all categories**

```
curl "https://www.thecocktaildb.com/api/json/v1/1/list.php?c=list"
curl "https://www.themealdb.com/api/json/v1/1/list.php?c=list"
```

## Testing in JavaScript

If you want to test from the browser console or inside our app:

```js
fetch("https://www.thecocktaildb.com/api/json/v1/1/random.php")
  .then(res => res.json())
  .then(data => console.log(data.drinks[0]));
```

```js
fetch("https://www.themealdb.com/api/json/v1/1/random.php")
  .then(res => res.json())
  .then(data => console.log(data.meals[0]));
```

The cocktail API returns results under `data.drinks` and the meal API under `data.meals`. Both are arrays, so grab `[0]` for single results.

## Images

Both APIs return image URLs in the response. You can append size suffixes to get different resolutions:

```
# Drink thumbnail (200px)
https://www.thecocktaildb.com/images/media/drink/vrwquq1478252802.jpg/small

# Meal thumbnail (350px)
https://www.themealdb.com/images/media/meals/llcbn01574260722.jpg/medium

# Ingredient thumbnail
https://www.thecocktaildb.com/images/ingredients/gin-small.png
https://www.themealdb.com/images/ingredients/lime-small.png
```

Sizes: `small` (200px), `medium` (350px), `large` (500px). Ingredient images follow the same pattern but use the ingredient name in the URL.

## What we use

The main endpoints for Mix It Up are:

- `random.php` for the lucky dip / random recipe feature
- `search.php?s=` for searching recipes by name
- `filter.php?i=` for browsing by ingredient
- `filter.php?c=` for browsing by category
- `lookup.php?i=` for fetching full recipe details by ID

These are all read-only, no POST or auth. User-created recipes live in our local SQLite database, not on these APIs.

## Notes

- The test key `1` is rate-limited but fine for development
- Some endpoints are premium-only (10 random, popular, latest, multi-ingredient filter). We don't need those
- TheMealDB also has `filter.php?a=Canadian` for filtering by area/cuisine, which could be useful later
