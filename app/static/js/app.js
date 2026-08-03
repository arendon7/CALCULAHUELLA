function getCookie(name) {
  const prefix = `${name}=`;
  for (const item of document.cookie.split(';')) {
    const value = item.trim();
    if (value.startsWith(prefix)) return decodeURIComponent(value.slice(prefix.length));
  }
  return '';
}

function attachCsrfTokens() {
  const token = getCookie('cth_csrf');
  if (!token) return;
  document.querySelectorAll('form').forEach((form) => {
    const method = (form.getAttribute('method') || 'get').toLowerCase();
    if (method === 'get' || form.querySelector('input[name="_csrf_token"]')) return;
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = '_csrf_token';
    input.value = token;
    form.appendChild(input);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const button = document.getElementById('menuButton');
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const closeSidebar = () => {
    sidebar?.classList.remove('open');
    button?.setAttribute('aria-expanded', 'false');
  };
  if (button && sidebar) button.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    button.setAttribute('aria-expanded', String(open));
  });
  if (backdrop) backdrop.addEventListener('click', closeSidebar);
  sidebar?.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeSidebar));
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeSidebar(); });

  const publicMenuButton = document.getElementById('publicMenuButton');
  const publicNav = document.getElementById('publicNav');
  const closePublicNav = () => {
    publicNav?.classList.remove('open');
    publicMenuButton?.setAttribute('aria-expanded', 'false');
  };
  if (publicMenuButton && publicNav) {
    publicMenuButton.addEventListener('click', () => {
      const open = publicNav.classList.toggle('open');
      publicMenuButton.setAttribute('aria-expanded', String(open));
    });
    publicNav.querySelectorAll('a').forEach((link) => link.addEventListener('click', closePublicNav));
  }
  attachCsrfTokens();
});

function initializeDiagnosisWizard() {
  const form = document.querySelector('[data-diagnosis-wizard]');
  if (!form) return;
  const steps = Array.from(form.querySelectorAll('[data-diagnosis-step]'));
  const indicators = Array.from(form.querySelectorAll('[data-diagnosis-indicator]'));
  const progress = form.querySelector('[data-diagnosis-progress]');
  const counter = form.querySelector('[data-diagnosis-counter]');
  const title = form.querySelector('[data-diagnosis-title]');
  const back = form.querySelector('[data-diagnosis-back]');
  const next = form.querySelector('[data-diagnosis-next]');
  const submit = form.querySelector('[data-diagnosis-submit]');
  const titles = ['Empresa y contacto', 'Escala y operación', 'Datos y madurez', 'Objetivo y profundidad'];
  let current = 0;

  const focusStep = () => {
    const heading = steps[current]?.querySelector('h2');
    heading?.setAttribute('tabindex', '-1');
    heading?.focus({ preventScroll: true });
  };
  const render = (focus = false) => {
    steps.forEach((step, index) => {
      step.hidden = index !== current;
      step.setAttribute('aria-hidden', String(index !== current));
    });
    indicators.forEach((indicator, index) => {
      indicator.classList.toggle('active', index === current);
      indicator.classList.toggle('complete', index < current);
      indicator.setAttribute('aria-current', index === current ? 'step' : 'false');
    });
    if (progress) progress.style.width = `${((current + 1) / steps.length) * 100}%`;
    if (counter) counter.textContent = `Paso ${current + 1} de ${steps.length}`;
    if (title) title.textContent = titles[current] || '';
    if (back) back.hidden = current === 0;
    if (next) next.hidden = current === steps.length - 1;
    if (submit) submit.hidden = current !== steps.length - 1;
    if (focus) focusStep();
  };
  const validateCurrent = () => {
    const controls = Array.from(steps[current].querySelectorAll('input, select, textarea'));
    for (const control of controls) {
      if (!control.checkValidity()) {
        control.reportValidity();
        control.focus();
        return false;
      }
    }
    return true;
  };

  next?.addEventListener('click', () => {
    if (!validateCurrent()) return;
    current = Math.min(current + 1, steps.length - 1);
    render(true);
    form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  back?.addEventListener('click', () => {
    current = Math.max(current - 1, 0);
    render(true);
    form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  form.addEventListener('submit', (event) => {
    if (!validateCurrent()) event.preventDefault();
  });
  render();
}

document.addEventListener('DOMContentLoaded', initializeDiagnosisWizard);

document.addEventListener('click', (event) => {
  const printButton = event.target.closest('[data-print-result]');
  if (printButton) window.print();
});

function initializeInventoryWizard() {
  const form = document.querySelector('[data-inventory-wizard]');
  if (!form) return;
  const steps = Array.from(form.querySelectorAll('[data-inventory-step]'));
  const indicators = Array.from(form.querySelectorAll('[data-inventory-indicator]'));
  const progress = form.querySelector('[data-inventory-progress]');
  const counter = form.querySelector('[data-inventory-counter]');
  const title = form.querySelector('[data-inventory-title]');
  const back = form.querySelector('[data-inventory-back]');
  const next = form.querySelector('[data-inventory-next]');
  const submit = form.querySelector('[data-inventory-submit]');
  const titles = ['Periodo y propósito', 'Punto de partida', 'Metodología', 'Límites y gobierno'];
  let current = 0;

  const validateCurrent = () => {
    const controls = Array.from(steps[current]?.querySelectorAll('input, select, textarea') || []);
    for (const control of controls) {
      if (!control.checkValidity()) {
        control.reportValidity();
        control.focus();
        return false;
      }
    }
    return true;
  };
  const render = (focus = false) => {
    steps.forEach((step, index) => {
      step.hidden = index !== current;
      step.setAttribute('aria-hidden', String(index !== current));
    });
    indicators.forEach((indicator, index) => {
      indicator.classList.toggle('active', index === current);
      indicator.classList.toggle('complete', index < current);
      indicator.setAttribute('aria-current', index === current ? 'step' : 'false');
    });
    if (progress) progress.style.width = `${((current + 1) / steps.length) * 100}%`;
    if (counter) counter.textContent = `Paso ${current + 1} de ${steps.length}`;
    if (title) title.textContent = titles[current] || '';
    if (back) back.hidden = current === 0;
    if (next) next.hidden = current === steps.length - 1;
    if (submit) submit.hidden = current !== steps.length - 1;
    if (focus) {
      const heading = steps[current]?.querySelector('h2');
      heading?.setAttribute('tabindex', '-1');
      heading?.focus({ preventScroll: true });
    }
  };

  next?.addEventListener('click', () => {
    if (!validateCurrent()) return;
    current = Math.min(current + 1, steps.length - 1);
    render(true);
    form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  back?.addEventListener('click', () => {
    current = Math.max(current - 1, 0);
    render(true);
    form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  indicators.forEach((indicator, index) => indicator.addEventListener('click', () => {
    if (index > current || !validateCurrent()) return;
    current = index;
    render(true);
  }));
  form.addEventListener('submit', (event) => {
    if (!validateCurrent()) event.preventDefault();
  });
  render();
}

function initializeActivityUnitSuggestion() {
  const form = document.querySelector('[data-activity-form]');
  if (!form) return;
  const source = form.querySelector('[data-activity-source]');
  const unit = form.querySelector('[data-activity-unit]');
  const hint = form.querySelector('[data-source-unit-hint]');
  const apply = () => {
    const preferred = source?.selectedOptions?.[0]?.dataset?.preferredUnit || '';
    if (preferred && unit) {
      const option = Array.from(unit.options).find((item) => item.value === preferred || item.textContent === preferred);
      if (option) unit.value = option.value;
    }
    if (hint) hint.textContent = preferred ? `Unidad sugerida: ${preferred}. Puedes cambiarla si el soporte usa otra.` : 'Define la unidad utilizada por el soporte.';
  };
  source?.addEventListener('change', apply);
  apply();
}

function initializeSourceInclusion() {
  document.querySelectorAll('.source-config-form').forEach((form) => {
    const included = form.querySelector('input[name="included"]');
    const reason = form.querySelector('input[name="exclusion_reason"]');
    if (!included || !reason) return;
    const apply = () => {
      reason.required = !included.checked;
      reason.closest('label')?.classList.toggle('required-exclusion', !included.checked);
    };
    included.addEventListener('change', apply);
    apply();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initializeInventoryWizard();
  initializeActivityUnitSuggestion();
  initializeSourceInclusion();
});


function initializeOperationalMapping() {
  const form = document.querySelector('[data-operational-mapping]');
  if (!form) return;
  const status = form.querySelector('[data-mapping-readiness]');
  const submit = form.querySelector('[data-mapping-submit]');
  const required = ['source', 'period_start', 'value'];
  const render = () => {
    const defaultSource = form.querySelector('[name="default_source_id"]')?.value || '';
    const missing = required.filter((field) => {
      if (field === 'source' && defaultSource) return false;
      return !(form.querySelector(`[name="map_${field}"]`)?.value || '');
    });
    if (status) {
      status.textContent = missing.length
        ? `Falta relacionar: ${missing.map((field) => ({ source: 'fuente', period_start: 'fecha inicial', value: 'valor' }[field])).join(', ')}.`
        : 'Mapeo mínimo completo. Ya puedes validar el lote.';
      status.classList.toggle('ready', missing.length === 0);
    }
    if (submit) submit.disabled = missing.length > 0;
  };
  form.querySelectorAll('select, input').forEach((control) => control.addEventListener('change', render));
  render();
}

function initializeOperationalRowEditors() {
  document.querySelectorAll('[data-row-editor-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const target = document.getElementById(button.dataset.rowEditorToggle || '');
      if (!target) return;
      target.hidden = !target.hidden;
      if (!target.hidden) target.querySelector('select, input')?.focus();
    });
  });
  document.querySelectorAll('[data-row-editor-close]').forEach((button) => {
    button.addEventListener('click', () => {
      const target = document.getElementById(button.dataset.rowEditorClose || '');
      if (target) target.hidden = true;
    });
  });
  document.querySelectorAll('.row-correction-form').forEach((form) => {
    const source = form.querySelector('select[name="source_id"]');
    const unit = form.querySelector('input[name="unit"]');
    source?.addEventListener('change', () => {
      const preferred = source.selectedOptions?.[0]?.dataset?.preferredUnit || '';
      if (preferred && unit && !unit.value.trim()) unit.value = preferred;
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initializeOperationalMapping();
  initializeOperationalRowEditors();
});
