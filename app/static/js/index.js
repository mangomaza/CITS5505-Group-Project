/* ============================================================
   Mix It Up: Home Page JS (index.js)
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  var heroShuffle = document.getElementById('heroShuffle');
  var randomShuffle = document.getElementById('randomShuffle');
  var randomResult = document.getElementById('randomResult');

  function triggerShuffle(btn) {
    if (!btn) return;
    btn.classList.add('spinning');
    btn.disabled = true;

    setTimeout(function () {
      btn.classList.remove('spinning');
      btn.disabled = false;

      // show the random result section
      if (randomResult) {
        randomResult.classList.remove('d-none');
        randomResult.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 900);
  }

  if (heroShuffle) {
    heroShuffle.addEventListener('click', function () {
      triggerShuffle(heroShuffle);
    });
  }

  if (randomShuffle) {
    randomShuffle.addEventListener('click', function () {
      triggerShuffle(randomShuffle);
    });
  }

});
