// Mix It Up random draw modal.
// Triggers from any [data-mix-trigger]. Fetches /recipes/random.json,
// flips two cards, lets the user pick one, then save it to their cookbook.

(function () {
  'use strict';

  const modal = document.getElementById('randomDraw');
  if (!modal) return;

  const RANDOM_URL = '/recipes/random.json';
  const SAVE_URL = '/recipes/save-external';
  const LOGIN_URL = '/auth/login';

  const cards = modal.querySelectorAll('.draw-card');
  const stage = modal.querySelector('.random-draw-stage');
  const statusEl = modal.querySelector('.random-draw-status');
  const rerollBtn = modal.querySelector('[data-mix-reroll]');
  const closeBtns = modal.querySelectorAll('[data-mix-close]');
  const dialog = modal.querySelector('.random-draw-modal');

  // Currently held draw payload, keyed by side (a/b).
  let drawData = { a: null, b: null };
  let returnFocus = null;
  let isAuthed = !!document.body.dataset.userAuthed;
  // Fall back: detect auth via presence of logout form in nav.
  if (!isAuthed) {
    isAuthed = !!document.querySelector('form[action$="/logout"]');
  }

  // --- form-dirty tracking on /recipe/create -------------------------
  let formDirty = false;
  const createForm = document.querySelector('main .create-form form');
  if (createForm) {
    createForm.addEventListener('input', () => { formDirty = true; }, { once: false });
    createForm.addEventListener('change', () => { formDirty = true; }, { once: false });
  }

  // --- helpers --------------------------------------------------------
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function setStatus(text, isError) {
    if (!statusEl) return;
    if (!text) {
      statusEl.hidden = true;
      statusEl.textContent = '';
      statusEl.classList.remove('is-error');
      return;
    }
    statusEl.hidden = false;
    statusEl.textContent = text;
    statusEl.classList.toggle('is-error', !!isError);
  }

  function resetCards() {
    drawData = { a: null, b: null };
    cards.forEach((card) => {
      card.classList.remove('is-flipped', 'is-chosen', 'is-faded');
      card.setAttribute('aria-busy', 'true');
      const face = card.querySelector('.draw-card-face');
      if (face) face.hidden = true;
      const pickWrap = card.querySelector('.draw-card-pick');
      if (pickWrap) pickWrap.hidden = false;
      const actions = card.querySelector('.draw-card-actions');
      if (actions) actions.hidden = true;
      const deselect = card.querySelector('[data-mix-deselect]');
      if (deselect) deselect.hidden = true;
    });
  }

  function renderCard(card, item) {
    const face = card.querySelector('.draw-card-face');
    const img = card.querySelector('.draw-card-img');
    const placeholder = card.querySelector('.draw-card-image-placeholder');
    const cassette = card.querySelector('.draw-card-cassette');
    const badge = card.querySelector('.draw-card-badge');
    const name = card.querySelector('.draw-card-name');
    const meta = card.querySelector('.draw-card-meta');

    const cat = (item.category || '').toLowerCase();

    if (item.image_url) {
      img.src = item.image_url;
      img.alt = item.name || '';
      img.hidden = false;
      if (placeholder) placeholder.hidden = true;
    } else {
      img.hidden = true;
      img.removeAttribute('src');
      if (placeholder) placeholder.hidden = false;
      if (cassette) {
        const cassetteSrc = '/static/images/placeholders/cassette-' + (cat === 'cocktail' ? 'cocktail' : 'food') + '.png';
        cassette.onerror = function () {
          cassette.hidden = true;
          cassette.onerror = null;
        };
        cassette.hidden = false;
        cassette.src = cassetteSrc;
      }
    }

    badge.textContent = cat === 'cocktail' ? 'Cocktail' : 'Food';
    badge.className = 'draw-card-badge ' + (cat === 'cocktail' ? 'badge-cocktail' : 'badge-food');

    name.textContent = item.name || 'Untitled';
    const isExternal = item.source_origin === 'api'
      || item.external_source === 'thecocktaildb'
      || item.external_source === 'themealdb';
    meta.textContent = isExternal ? 'from the wider web' : 'from your community';

    face.hidden = false;
  }

  function flipCard(card, delay) {
    return new Promise((resolve) => {
      setTimeout(() => {
        card.classList.add('is-flipped');
        card.setAttribute('aria-busy', 'false');
        resolve();
      }, delay);
    });
  }

  function showFatalError(message) {
    setStatus(message || 'Could not draw a pair right now. Try again in a moment.', true);
    cards.forEach((card) => card.setAttribute('aria-busy', 'false'));
  }

  // --- draw -----------------------------------------------------------
  async function draw() {
    setStatus('Mixing it up...', false);
    resetCards();
    let resp;
    try {
      resp = await fetch(RANDOM_URL, { headers: { 'Accept': 'application/json' } });
    } catch (err) {
      showFatalError('Network hiccup. Check your connection and try again.');
      return;
    }
    if (!resp.ok) {
      let msg = 'Could not draw a pair right now.';
      try {
        const data = await resp.json();
        if (data && data.message) msg = data.message;
      } catch (_) { /* ignore */ }
      showFatalError(msg);
      return;
    }

    let data;
    try {
      data = await resp.json();
    } catch (err) {
      showFatalError('Got a bad response from the server.');
      return;
    }

    drawData.a = data.side_a || null;
    drawData.b = data.side_b || null;

    if (data.fallback_used) {
      setStatus("Couldn't reach the wider web. Showing recipes from the community instead.", true);
    } else {
      setStatus('', false);
    }

    cards.forEach((card) => {
      const side = card.dataset.side;
      const item = drawData[side];
      if (item) renderCard(card, item);
    });

    // B2 stagger: side A first, then side B.
    flipCard(cards[0], 2000);
    flipCard(cards[1], 2250);
  }

  // --- pick / D1 fade-and-expand -------------------------------------
  function pickCard(chosen) {
    const side = chosen.dataset.side;
    const item = drawData[side];
    if (!item) return;

    cards.forEach((card) => {
      if (card === chosen) {
        card.classList.add('is-chosen');
        const pickWrap = card.querySelector('.draw-card-pick');
        if (pickWrap) pickWrap.hidden = true;
        const deselect = card.querySelector('[data-mix-deselect]');
        if (deselect) deselect.hidden = false;
        const actions = card.querySelector('.draw-card-actions');
        if (actions) {
          actions.hidden = false;
          const anonBlock = actions.querySelector('.draw-card-actions-anon');
          const authBlock = actions.querySelector('.draw-card-actions-auth');
          if (isAuthed) {
            if (anonBlock) anonBlock.hidden = true;
            if (authBlock) authBlock.hidden = false;
          } else {
            if (authBlock) authBlock.hidden = true;
            if (anonBlock) {
              anonBlock.hidden = false;
              const link = anonBlock.querySelector('.draw-card-login-link');
              if (link) {
                // Stash chosen item so after login we can reopen the modal
                // already on this card.
                link.onclick = (ev) => {
                  ev.preventDefault();
                  try {
                    sessionStorage.setItem('mixResume', JSON.stringify({
                      side: side,
                      draw: drawData,
                      path: window.location.pathname,
                    }));
                  } catch (_) { /* ignore */ }
                  const nextUrl = window.location.pathname + '?resume_mix=1';
                  window.location.href = LOGIN_URL + '?next=' + encodeURIComponent(nextUrl);
                };
              }
            }
          }
        }
      } else {
        card.classList.add('is-faded');
        const pickWrap = card.querySelector('.draw-card-pick');
        if (pickWrap) pickWrap.hidden = true;
      }
    });
  }

  // Reverse the pick: actions and deselect arrow fade out first, then
  // the card shrinks back, mirroring the order of the pick animation.
  function deselectCard() {
    // Phase 1: fade out actions and deselect button via .is-deselecting.
    // Card stays at the chosen height (.is-chosen still present) while
    // these fade out so it doesn't shrink underneath them.
    cards.forEach((card) => card.classList.add('is-deselecting'));

    const FADE_OUT_MS = 300;
    setTimeout(() => {
      // Phase 2: drop chosen/faded so the card height transitions back
      // and the sibling card fades back in. Then restore the pick UI.
      cards.forEach((card) => {
        card.classList.remove('is-chosen', 'is-faded', 'is-deselecting');
        const pickWrap = card.querySelector('.draw-card-pick');
        if (pickWrap) pickWrap.hidden = false;
        const actions = card.querySelector('.draw-card-actions');
        if (actions) actions.hidden = true;
        const deselect = card.querySelector('[data-mix-deselect]');
        if (deselect) deselect.hidden = true;
      });
    }, FADE_OUT_MS);
  }

  // --- save -----------------------------------------------------------
  async function postSave(card, confirmDuplicate) {
    const side = card.dataset.side;
    const item = drawData[side];
    if (!item) return;
    const visibility = getVisibility(card);

    const body = new URLSearchParams();
    body.set('csrf_token', getCsrfToken());
    body.set('external_source', item.external_source || '');
    body.set('external_id', item.external_id || '');
    body.set('visibility', visibility);
    if (confirmDuplicate) body.set('confirm_duplicate', '1');

    let resp;
    try {
      resp = await fetch(SAVE_URL, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': getCsrfToken(),
        },
        body: body.toString(),
      });
    } catch (err) {
      setStatus('Network error. Could not save right now.', true);
      return;
    }

    let data = {};
    try { data = await resp.json(); } catch (_) { /* ignore */ }

    if (resp.status === 201 && data.ok) {
      setStatus('Saved. Opening it now...', false);
      window.location.href = data.recipe_url;
      return;
    }
    if (resp.status === 409 && data.error === 'already_saved') {
      setStatus(data.message + ' ', true);
      const link = document.createElement('a');
      link.href = data.existing_recipe_url;
      link.textContent = 'View it';
      statusEl.appendChild(link);
      return;
    }
    if (resp.status === 409 && data.error === 'similar_recipe' && data.confirm_required) {
      const ok = window.confirm(data.message);
      if (ok) {
        await postSave(card, true);
      } else {
        setStatus('Save cancelled.', false);
      }
      return;
    }
    if (resp.status === 401 || resp.status === 302) {
      setStatus('Please log in to save.', true);
      return;
    }
    setStatus(data.message || 'Could not save. Please try again.', true);
  }

  function getVisibility(card) {
    const active = card.querySelector('.visibility-pill.is-active');
    return active && active.dataset.visibility === 'public' ? 'public' : 'private';
  }

  // --- edit and save (handoff to /recipe/create via prefill) ---------
  function editAndSave(card) {
    const side = card.dataset.side;
    const item = drawData[side];
    if (!item) return;
    if (!isAuthed) {
      window.location.href = LOGIN_URL + '?next=' + encodeURIComponent('/recipe/create');
      return;
    }
    const params = new URLSearchParams();
    params.set('source', item.external_source || '');
    params.set('external_id', item.external_id || '');
    window.location.href = '/recipes/external-prefill?' + params.toString();
  }

  // --- modal open/close -----------------------------------------------
  function openModal(triggerEl) {
    if (window.location.pathname === '/recipe/create' && formDirty) {
      const ok = window.confirm("You have unsaved changes on this form. Mix It Up will leave them behind. Continue?");
      if (!ok) return;
    }
    returnFocus = triggerEl || document.activeElement;
    modal.hidden = false;
    document.body.classList.add('mix-modal-open');
    setStatus('', false);
    if (dialog) dialog.focus();
    draw();
  }

  function closeModal() {
    modal.hidden = true;
    document.body.classList.remove('mix-modal-open');
    resetCards();
    setStatus('', false);
    if (returnFocus && typeof returnFocus.focus === 'function') {
      returnFocus.focus();
    }
  }

  // --- wiring ---------------------------------------------------------
  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('[data-mix-trigger]');
    if (trigger) {
      e.preventDefault();
      openModal(trigger);
    }
  });

  closeBtns.forEach((btn) => btn.addEventListener('click', closeModal));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.hidden) closeModal();
  });

  if (rerollBtn) rerollBtn.addEventListener('click', draw);

  cards.forEach((card) => {
    const pickBtn = card.querySelector('.draw-card-pick-btn');
    if (pickBtn) pickBtn.addEventListener('click', () => pickCard(card));

    const deselectBtn = card.querySelector('[data-mix-deselect]');
    if (deselectBtn) deselectBtn.addEventListener('click', deselectCard);

    card.querySelectorAll('.visibility-pill').forEach((pill) => {
      pill.addEventListener('click', () => {
        card.querySelectorAll('.visibility-pill').forEach((p) => p.classList.remove('is-active'));
        pill.classList.add('is-active');
      });
    });

    const saveBtn = card.querySelector('.draw-card-actions-auth .draw-card-save-btn');
    if (saveBtn) saveBtn.addEventListener('click', () => postSave(card, false));

    const editBtn = card.querySelector('.draw-card-edit-btn');
    if (editBtn) editBtn.addEventListener('click', () => editAndSave(card));
  });

  // --- resume after login ---------------------------------------------
  // If we just bounced an anon user to login and they came back, replay
  // the modal already on their picked card so they don't have to re-roll.
  function maybeResume() {
    if (!isAuthed) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get('resume_mix') !== '1') return;
    let stash = null;
    try {
      const raw = sessionStorage.getItem('mixResume');
      if (raw) stash = JSON.parse(raw);
    } catch (_) { /* ignore */ }
    if (!stash || !stash.draw || stash.path !== window.location.pathname) return;
    sessionStorage.removeItem('mixResume');

    // Strip the query param so a refresh is clean.
    const cleanUrl = window.location.pathname + window.location.hash;
    window.history.replaceState({}, '', cleanUrl);

    modal.hidden = false;
    document.body.classList.add('mix-modal-open');
    if (dialog) dialog.focus();

    drawData.a = stash.draw.a || null;
    drawData.b = stash.draw.b || null;

    let chosenCard = null;
    cards.forEach((card) => {
      const item = drawData[card.dataset.side];
      if (!item) return;
      renderCard(card, item);
      card.classList.add('is-flipped');
      card.setAttribute('aria-busy', 'false');
      if (card.dataset.side === stash.side) chosenCard = card;
    });
    if (chosenCard) pickCard(chosenCard);
    setStatus("You're back. Save it now or pick something else.", false);
  }
  maybeResume();
})();
