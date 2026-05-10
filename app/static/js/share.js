// Filter the share tables by recipe name and category.
document.addEventListener('DOMContentLoaded', function () {
  var search = document.getElementById('shareSearch');
  var pillsBox = document.getElementById('shareFilterPills');
  if (!search || !pillsBox) return;

  var pills = pillsBox.querySelectorAll('.filter-pill');
  var tables = document.querySelectorAll('#sharedByYouTable, #sharedWithYouTable');
  var activeCategory = 'all';

  function applyFilter() {
    var q = search.value.trim().toLowerCase();
    tables.forEach(function (table) {
      var rows = table.querySelectorAll('tbody tr[data-name]');
      var visibleCount = 0;
      rows.forEach(function (row) {
        var name = row.getAttribute('data-name') || '';
        var cat = row.getAttribute('data-category') || '';
        var matchName = !q || name.indexOf(q) !== -1;
        var matchCat = activeCategory === 'all' || cat === activeCategory;
        var show = matchName && matchCat;
        row.hidden = !show;
        if (show) visibleCount += 1;
      });
      var emptyRow = table.querySelector('tr.share-empty-filter');
      if (emptyRow) emptyRow.hidden = !(rows.length > 0 && visibleCount === 0);
    });
  }

  search.addEventListener('input', applyFilter);
  pills.forEach(function (pill) {
    pill.addEventListener('click', function () {
      pills.forEach(function (p) { p.classList.remove('active'); });
      pill.classList.add('active');
      activeCategory = pill.getAttribute('data-filter');
      applyFilter();
    });
  });
});
