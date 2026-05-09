document.addEventListener('DOMContentLoaded', function () {
  var uploadArea = document.getElementById('uploadArea');
  var imageInput = document.getElementById('recipeImage');
  var imagePreview = document.getElementById('imagePreview');
  var uploadPlaceholder = document.getElementById('uploadPlaceholder');
  var ingredientList = document.getElementById('ingredientList');
  var addIngredientBtn = document.getElementById('addIngredient');
  var categorySelect = document.getElementById('recipeCategory');
  var alcoholChoices = document.getElementById('alcoholChoices');
  var alcoholTrue = document.getElementById('is_alcoholic-0');
  var alcoholFalse = document.getElementById('is_alcoholic-1');

  function getDefaultPlaceholder() {
    if (!uploadArea) {
      return '';
    }
    var category = categorySelect ? categorySelect.value : 'cocktail';
    if (category === 'food') {
      return uploadArea.getAttribute('data-default-food') || '';
    }
    return uploadArea.getAttribute('data-default-cocktail') || '';
  }

  function setHasPreview(hasPreview) {
    if (!uploadArea) {
      return;
    }
    if (hasPreview) {
      uploadArea.classList.add('has-preview');
    } else {
      uploadArea.classList.remove('has-preview');
    }
  }

  function showPreviewSrc(src) {
    if (!imagePreview) {
      return;
    }
    if (src) {
      imagePreview.src = src;
      setHasPreview(true);
    } else {
      imagePreview.removeAttribute('src');
      setHasPreview(false);
    }
  }

  function updateImagePreview(file) {
    if (!file) {
      return;
    }
    var reader = new FileReader();
    reader.onload = function (event) {
      showPreviewSrc(event.target.result);
    };
    reader.readAsDataURL(file);
  }

  // Seed preview from any pre-set src (e.g. external image URL on prefill)
  // or fall back to the category-appropriate placeholder asset.
  if (imagePreview) {
    imagePreview.addEventListener('error', function () {
      // Placeholder asset is missing — fall back to the empty upload state.
      imagePreview.removeAttribute('src');
      setHasPreview(false);
    });
    if (imagePreview.getAttribute('src')) {
      setHasPreview(true);
    } else {
      var placeholder = getDefaultPlaceholder();
      if (placeholder) {
        imagePreview.src = placeholder;
        setHasPreview(true);
      }
    }
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
        if (uploadArea) {
          uploadArea.dataset.hasUserImage = '1';
        }
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

  function syncCategoryFields() {
    var isFood = categorySelect && categorySelect.value === 'food';
    var blocks = document.querySelectorAll('[data-cocktail-only]');
    blocks.forEach(function (el) {
      if (isFood) {
        el.classList.add('d-none');
      } else {
        el.classList.remove('d-none');
      }
    });
    if (isFood) {
      var glassInput = document.getElementById('recipeGlass');
      if (glassInput) {
        glassInput.value = '';
      }
    }
  }

  if (categorySelect) {
    categorySelect.addEventListener('change', function () {
      syncAlcoholChoices();
      syncCategoryFields();
      // Swap default placeholder if the user hasn't picked a real photo yet.
      if (uploadArea && imagePreview && !uploadArea.dataset.hasUserImage) {
        var fallback = getDefaultPlaceholder();
        if (fallback) {
          imagePreview.src = fallback;
          setHasPreview(true);
        }
      }
    });
    syncAlcoholChoices();
    syncCategoryFields();
  }
});
