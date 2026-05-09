/* ============================================================
   Mix It Up — Option A: Browse Recipes JS (recipes.js)
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  var searchInput = document.getElementById('recipeSearch');
  var searchQuery = '';

  function applyFilters() {
    var query = searchQuery.trim().toLowerCase();
    document.querySelectorAll('.recipe-grid-item').forEach(function (item) {
      var title = item.querySelector('.card-title');
      var name = title ? title.textContent.toLowerCase() : '';
      var matchesSearch = !query || name.indexOf(query) !== -1;
      var hiddenByFilter = item.dataset.hiddenByFilter === '1';
      item.style.display = (matchesSearch && !hiddenByFilter) ? '' : 'none';
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      searchQuery = searchInput.value || '';
      applyFilters();
    });
  }

  // category filter pills
  var pills = document.querySelectorAll('.filter-pill');
  pills.forEach(function (pill) {
    pill.addEventListener('click', function () {
      // toggle active state
      if (pill.classList.contains('active') && pill.dataset.filter !== 'all') {
        pill.classList.remove('active');
        showAllCards();
        return;
      }

      pills.forEach(function (p) { p.classList.remove('active'); });
      pill.classList.add('active');

      var filter = pill.dataset.filter;
      if (filter === 'all') {
        showAllCards();
      } else {
        filterCards(filter);
      }
    });
  });

  function showAllCards() {
    document.querySelectorAll('.recipe-card').forEach(function (card) {
      card.closest('.recipe-grid-item').style.display = '';
    });
  }

  function filterCards(category) {
    document.querySelectorAll('.recipe-card').forEach(function (card) {
      var wrapper = card.closest('.recipe-grid-item');
      var badge = card.querySelector('[class^="badge-"]');
      if (badge && badge.classList.contains('badge-' + category)) {
        wrapper.style.display = '';
      } else {
        wrapper.style.display = 'none';
      }
    });
  }

  // Mix it up button - pick a random visible recipe and navigate to it
  var mixBtn = document.getElementById('mixItUpBtn');
  if (mixBtn) {
    mixBtn.addEventListener('click', function () {
      mixBtn.classList.add('spinning');
      mixBtn.disabled = true;

      setTimeout(function () {
        var visibleItems = Array.prototype.filter.call(
          document.querySelectorAll('.recipe-grid-item'),
          function (item) { return item.style.display !== 'none'; }
        );
        if (visibleItems.length > 0) {
          var pick = visibleItems[Math.floor(Math.random() * visibleItems.length)];
          var link = pick.querySelector('a');
          if (link) { window.location.href = link.getAttribute('href'); return; }
        }
        mixBtn.classList.remove('spinning');
        mixBtn.disabled = false;
      }, 600);
    });
  }

});
