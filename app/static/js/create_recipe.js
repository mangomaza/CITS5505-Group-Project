document.addEventListener('DOMContentLoaded', function () {
  var uploadArea = document.getElementById('uploadArea');
  var imageInput = document.getElementById('recipeImage');
  var imagePreview = document.getElementById('imagePreview');
  var uploadPlaceholder = uploadArea ? uploadArea.querySelector('.upload-placeholder') : null;
  var ingredientList = document.getElementById('ingredientList');
  var addIngredientBtn = document.getElementById('addIngredient');
  var categorySelect = document.getElementById('recipeCategory');
  var alcoholChoices = document.getElementById('alcoholChoices');
  var alcoholTrue = document.getElementById('is_alcoholic-0');
  var alcoholFalse = document.getElementById('is_alcoholic-1');

  function updateImagePreview(file) {
    if (!file || !imagePreview || !uploadPlaceholder) {
      return;
    }

    var reader = new FileReader();
    reader.onload = function (event) {
      imagePreview.src = event.target.result;
      imagePreview.style.display = 'block';
      uploadPlaceholder.style.display = 'none';
    };
    reader.readAsDataURL(file);
  }

  function buildIngredientRow() {
    var row = document.createElement('div');
    row.className = 'ingredient-row';
    row.innerHTML = [
      '<input type="text" class="form-control" name="ingredient_name" placeholder="Ingredient name">',
      '<input type="text" class="form-control" name="ingredient_quantity" placeholder="Qty">',
      '<input type="text" class="form-control" name="ingredient_unit" placeholder="Unit">',
      '<button type="button" class="btn-remove" title="Remove"><i class="bi bi-x-lg"></i></button>',
    ].join('');
    return row;
  }

  if (uploadArea && imageInput) {
    uploadArea.addEventListener('click', function () {
      imageInput.click();
    });

    imageInput.addEventListener('change', function () {
      if (imageInput.files && imageInput.files[0]) {
        updateImagePreview(imageInput.files[0]);
      }
    });
  }

  if (addIngredientBtn && ingredientList) {
    addIngredientBtn.addEventListener('click', function () {
      ingredientList.appendChild(buildIngredientRow());
    });

    ingredientList.addEventListener('click', function (event) {
      var removeButton = event.target.closest('.btn-remove');
      if (!removeButton) {
        return;
      }

      var row = removeButton.closest('.ingredient-row');
      if (row) {
        row.remove();
      }

      if (!ingredientList.querySelector('.ingredient-row')) {
        ingredientList.appendChild(buildIngredientRow());
      }
    });
  }

  function syncAlcoholChoices() {
    if (!categorySelect || !alcoholChoices || !alcoholTrue || !alcoholFalse) {
      return;
    }

    var isCocktail = categorySelect.value === 'cocktail';
    var isFood = categorySelect.value === 'food';
    alcoholChoices.style.opacity = '1';

    if (isCocktail) {
      alcoholTrue.checked = true;
    } else if (isFood) {
      alcoholFalse.checked = true;
    }
  }

  if (categorySelect) {
    categorySelect.addEventListener('change', syncAlcoholChoices);
    syncAlcoholChoices();
  }
});
