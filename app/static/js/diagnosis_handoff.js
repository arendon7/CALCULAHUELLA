(() => {
  const STORAGE_KEY = 'cth_landing_context_v1';
  const SCHEMA = 'cth.landing_context.v1';
  const MAX_AGE_MS = 30 * 60 * 1000;

  function readContext(now = Date.now()) {
    let raw = '';
    try {
      raw = window.localStorage.getItem(STORAGE_KEY) || '';
    } catch (_error) {
      return null;
    }
    if (!raw) return null;

    let context;
    try {
      context = JSON.parse(raw);
    } catch (_error) {
      return null;
    }
    if (!context || context.schema !== SCHEMA) return null;

    const createdAt = Date.parse(context.created_at || '');
    if (!Number.isFinite(createdAt)) return null;
    const age = now - createdAt;
    if (age < 0 || age > MAX_AGE_MS) return null;
    return context;
  }

  function setSelectValue(select, value) {
    if (!select || typeof value !== 'string' || !value) return false;
    const option = Array.from(select.options).find(
      (item) => item.value === value || item.textContent.trim() === value
    );
    if (!option) return false;
    select.value = option.value;
    return true;
  }

  function showPrefillNotice(form, applied) {
    if (!form || applied < 1 || form.querySelector('[data-diagnosis-prefill]')) return;
    const note = document.createElement('div');
    note.className = 'diagnosis-prefill-note';
    note.dataset.diagnosisPrefill = '';
    note.setAttribute('role', 'status');
    note.setAttribute('aria-live', 'polite');

    const title = document.createElement('strong');
    title.textContent = 'Continuamos desde la landing.';
    const description = document.createElement('span');
    description.textContent = applied === 2
      ? 'Aplicamos sector y objetivo desde la landing. Puedes cambiarlos antes de enviar.'
      : 'Aplicamos una respuesta desde la landing. Puedes cambiarla antes de enviar.';
    note.append(title, description);

    const progress = form.querySelector('.diagnosis-wizard-progress');
    form.insertBefore(note, progress || form.firstChild);
  }

  function applyLandingContext() {
    const form = document.querySelector('[data-diagnosis-wizard]');
    if (!form) return 0;
    const context = readContext();
    if (!context) return 0;

    const reusable = context.reusable || {};
    const allowed = {
      sector: form.querySelector('select[name="sector"]'),
      objective: form.querySelector('select[name="objective"]'),
    };

    let applied = 0;
    Object.entries(allowed).forEach(([field, select]) => {
      if (setSelectValue(select, reusable[field])) applied += 1;
    });
    showPrefillNotice(form, applied);
    return applied;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyLandingContext, { once: true });
  } else {
    applyLandingContext();
  }
})();
