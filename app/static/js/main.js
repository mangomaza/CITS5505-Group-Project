/* ============================================================
   Mix It Up: Shared JS (main.js)
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  // highlight active nav link based on current page
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.navbar-nav .nav-link').forEach(function (link) {
    const href = link.getAttribute('href');
    if (href === currentPage) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // auto-dismiss flash alerts after 5 seconds
  document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
    setTimeout(function () {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert.close();
    }, 5000);
  });

  // fallback for broken images (API images that fail to load)
  document.querySelectorAll('img').forEach(function (img) {
    img.addEventListener('error', function () {
      if (!img.dataset.fallback) {
        img.dataset.fallback = 'true';
        img.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'%3E%3Crect fill='%232C2421' width='400' height='300'/%3E%3Ctext x='50%25' y='45%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='48' fill='%23D4944C'%3E%F0%9F%8D%B9%3C/text%3E%3Ctext x='50%25' y='62%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='14' fill='%239B8E82'%3EImage unavailable%3C/text%3E%3C/svg%3E";
        img.alt = 'Image unavailable';
      }
    });
  });

  // footer rewind-to-top link
  document.querySelectorAll('[data-mix-top]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });

});
