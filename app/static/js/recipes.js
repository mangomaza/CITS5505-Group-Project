/* ============================================================
   Mix It Up — Option A: Browse Recipes JS (recipes.js)
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  var searchInput = document.getElementById('recipeSearch');
  var searchQuery = '';
  var countEl = document.getElementById('recipeCount');
  var allSection = document.querySelector('[data-recipe-section="all"]');
  var mineSection = document.querySelector('[data-recipe-section="my-recipes"]');
  var activeFilter = 'all';

  function visibleItems() {
    var items = [];
    if (allSection && !allSection.hidden) {
      items = items.concat(Array.prototype.slice.call(allSection.querySelectorAll('.recipe-grid-item')));
    }
    if (mineSection && !mineSection.hidden) {
      items = items.concat(Array.prototype.slice.call(mineSection.querySelectorAll('.recipe-grid-item')));
    }
    return items.filter(function (item) { return item.style.display !== 'none'; });
  }

  function updateCount() {
    if (!countEl) return;
    var visible = visibleItems().length;
    var label;
    if (visible === 0) label = countEl.dataset.zero || 'no recipes';
    else if (visible === 1) label = countEl.dataset.one || '1 recipe';
    else label = (countEl.dataset.many || '{n} recipes').replace('{n}', visible);
    countEl.textContent = label;
  }

  function applyFilters() {
    var query = searchQuery.trim().toLowerCase();
    document.querySelectorAll('.recipe-grid-item').forEach(function (item) {
      var title = item.querySelector('.card-title');
      var name = title ? title.textContent.toLowerCase() : '';
      var matchesSearch = !query || name.indexOf(query) !== -1;
      var hiddenByFilter = item.dataset.hiddenByFilter === '1';
      item.style.display = (matchesSearch && !hiddenByFilter) ? '' : 'none';
    });
    updateCount();
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      searchQuery = searchInput.value || '';
      applyFilters();
    });
  }

  // category filter pills
  var pills = document.querySelectorAll('.filter-pill');

  // honour ?category=cocktail|food from the home page browse-by-category links
  var urlCategory = (new URLSearchParams(window.location.search)).get('category');
  if (urlCategory === 'cocktail' || urlCategory === 'food') {
    activeFilter = urlCategory;
    pills.forEach(function (p) {
      p.classList.toggle('active', p.dataset.filter === urlCategory);
    });
  }

  function applyPillFilter() {
    var onlyMine = activeFilter === 'my-recipes';
    if (allSection) allSection.hidden = onlyMine;
    if (mineSection) mineSection.hidden = false;

    document.querySelectorAll('.recipe-grid-item').forEach(function (item) {
      var category = item.dataset.category || '';
      var matches = true;
      if (activeFilter === 'cocktail' || activeFilter === 'food') {
        matches = (category === activeFilter);
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

  applyPillFilter();

  // Mix it up button - pick a random visible recipe and navigate to it
  var mixBtn = document.getElementById('mixItUpBtn');
  if (mixBtn) {
    mixBtn.addEventListener('click', function () {
      mixBtn.classList.add('spinning');
      mixBtn.disabled = true;

      setTimeout(function () {
        var pool = visibleItems();
        if (pool.length > 0) {
          var pick = pool[Math.floor(Math.random() * pool.length)];
          var link = pick.querySelector('a');
          if (link) { window.location.href = link.getAttribute('href'); return; }
        }
        mixBtn.classList.remove('spinning');
        mixBtn.disabled = false;
      }, 600);
    });
  }

});
