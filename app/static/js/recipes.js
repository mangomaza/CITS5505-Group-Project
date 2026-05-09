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
  var activeFilter = 'all';

  // honour ?category=cocktail|food from the home page browse-by-category links
  var urlCategory = (new URLSearchParams(window.location.search)).get('category');
  if (urlCategory === 'cocktail' || urlCategory === 'food') {
    activeFilter = urlCategory;
    pills.forEach(function (p) {
      p.classList.toggle('active', p.dataset.filter === urlCategory);
    });
  }

  function applyPillFilter() {
    document.querySelectorAll('.recipe-grid-item').forEach(function (item) {
      var category = item.dataset.category || '';
      var mine = item.dataset.mine === '1';
      var matches = true;
      if (activeFilter === 'cocktail' || activeFilter === 'food') {
        matches = (category === activeFilter);
      } else if (activeFilter === 'my-recipes') {
        matches = mine;
      }
      item.dataset.hiddenByFilter = matches ? '0' : '1';
    });
    applyFilters();
  }

  pills.forEach(function (pill) {
    pill.addEventListener('click', function () {
      pills.forEach(function (p) { p.classList.remove('active'); });
      pill.classList.add('active');
      activeFilter = pill.dataset.filter || 'all';
      applyPillFilter();
    });
  });

  // initialise so the default "All" pill marks every card visible
  applyPillFilter();

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
