/* ============================================================
   Mix It Up — Option A: Recipe Detail JS (recipe_detail.js)
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  // interactive star rating input
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

});
