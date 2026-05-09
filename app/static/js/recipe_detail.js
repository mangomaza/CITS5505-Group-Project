/* ============================================================
   Mix It Up — Option A: Recipe Detail JS (recipe_detail.js)
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {
  // DB recipe star rating widget
  var ratingWidget = document.getElementById('ratingWidget');

  if (ratingWidget) {
    var recipeId = ratingWidget.dataset.recipeId;
    var starButtons = document.querySelectorAll('.rating-star-button');
    var averageRating = document.getElementById('averageRating');
    var ratingCount = document.getElementById('ratingCount');
    var ratingMessage = document.getElementById('ratingMessage');
    var averageStars = document.getElementById('averageStars');

    function updateUserStars(userRating) {
      starButtons.forEach(function (button) {
        var value = parseInt(button.dataset.stars, 10);
        var icon = button.querySelector('i');

        if (value <= userRating) {
          icon.className = 'bi bi-star-fill';
        } else {
          icon.className = 'bi bi-star';
        }
      });
    }

    function updateAverageStars(average) {
      if (!averageStars) {
        return;
      }

      averageStars.innerHTML = '';

      for (var i = 1; i <= 5; i++) {
        var icon = document.createElement('i');

        if (i <= Math.round(average)) {
          icon.className = 'bi bi-star-fill';
        } else {
          icon.className = 'bi bi-star';
        }

        averageStars.appendChild(icon);
      }
    }

    starButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        var stars = this.dataset.stars;

        if (ratingMessage) {
          ratingMessage.textContent = 'Saving your rating...';
        }

        fetch('/recipes/' + recipeId + '/rate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            stars: stars
          })
        })
          .then(function (response) {
            return response.json();
          })
          .then(function (data) {
            if (!data.success) {
              if (ratingMessage) {
                ratingMessage.textContent = data.error || 'Rating could not be saved.';
              }
              return;
            }

            if (averageRating) {
              averageRating.textContent = data.average;
            }

            if (ratingCount) {
              ratingCount.textContent = data.count;
            }

            if (ratingMessage) {
              ratingMessage.textContent = 'Your rating has been saved.';
            }

            updateUserStars(data.user_rating);
            updateAverageStars(data.average);
          })
          .catch(function () {
            if (ratingMessage) {
              ratingMessage.textContent = 'Something went wrong. Please try again.';
            }
          });
      });
    });
  }

  // Existing external/static rating input fallback
  var starInput = document.querySelector('.star-input');
  var ratingField = document.getElementById('ratingValue');

  if (starInput && ratingField) {
    var stars = starInput.querySelectorAll('.bi');

    stars.forEach(function (star, idx) {
      star.addEventListener('mouseenter', function () {
        highlightStars(idx);
      });

      star.addEventListener('click', function () {
        var value = idx + 1;
        ratingField.value = value;
        setActiveStars(idx);
      });
    });

    starInput.addEventListener('mouseleave', function () {
      var current = parseInt(ratingField.value, 10) || 0;
      if (current > 0) {
        setActiveStars(current - 1);
      } else {
        clearStars();
      }
    });

    function highlightStars(upTo) {
      stars.forEach(function (s, i) {
        s.classList.toggle('hovered', i <= upTo);
      });
    }

    function setActiveStars(upTo) {
      stars.forEach(function (s, i) {
        s.classList.remove('hovered');
        s.classList.toggle('active', i <= upTo);
      });
    }

    function clearStars() {
      stars.forEach(function (s) {
        s.classList.remove('hovered', 'active');
      });
    }
  }

  // like/favourite toggle
  var favBtn = document.getElementById('favBtn');
  if (favBtn) {
    favBtn.addEventListener('click', function () {
      var icon = favBtn.querySelector('.bi');
      if (icon.classList.contains('bi-heart')) {
        icon.classList.replace('bi-heart', 'bi-heart-fill');
        icon.style.color = 'var(--mix-danger)';
        icon.classList.add('heart-bounce');
      } else {
        icon.classList.replace('bi-heart-fill', 'bi-heart');
        icon.style.color = '';
        icon.classList.remove('heart-bounce');
      }
    });
  }

  // Ingredient thumbnail random pool.
  // Each category has POOL_SIZE slots. Drop the corresponding AI-generated
  // images into static/images/placeholders/ingredients/{cocktail,food}/
  // named 1.png, 2.png ... POOL_SIZE.png.
  // Until the assets exist the fallback (placehold.co) is shown automatically.
  var INGREDIENT_POOL_SIZE = 10;
  var ingredientsList = document.querySelector('.ingredients-list');
  if (ingredientsList) {
    var category = (ingredientsList.dataset.category || 'food').toLowerCase();
    var folder = (category === 'cocktail') ? 'cocktail' : 'food';
    var thumbs = ingredientsList.querySelectorAll('.ingredient-thumb');
    thumbs.forEach(function (img) {
      var fallbackSrc = img.getAttribute('src');
      var pick = Math.floor(Math.random() * INGREDIENT_POOL_SIZE) + 1;
      var localSrc = '/static/images/placeholders/ingredients/' + folder + '/' + pick + '.png';
      img.onerror = function () {
        img.src = fallbackSrc;
        img.onerror = null;
      };
      img.src = localSrc;
    });
  }
});
