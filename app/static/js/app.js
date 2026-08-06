function getCookie(name) {
  const prefix = `${name}=`;
  let cookieValue = '';
  try { cookieValue = document.cookie || ''; } catch (_error) { return ''; }
  for (const item of cookieValue.split(';')) {
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
  const main = document.getElementById('aplicacion');
  let menuReturnFocus = null;

  const closeSidebar = ({ restoreFocus = false } = {}) => {
    const wasOpen = sidebar?.classList.contains('open');
    sidebar?.classList.remove('open');
    button?.setAttribute('aria-expanded', 'false');
    backdrop?.setAttribute('aria-hidden', 'true');
    backdrop?.setAttribute('tabindex', '-1');
    main?.removeAttribute('inert');
    if (wasOpen && restoreFocus) (menuReturnFocus || button)?.focus();
  };
  const openSidebar = () => {
    if (!button || !sidebar) return;
    menuReturnFocus = document.activeElement;
    sidebar.classList.add('open');
    button.setAttribute('aria-expanded', 'true');
    backdrop?.setAttribute('aria-hidden', 'false');
    backdrop?.setAttribute('tabindex', '0');
    main?.setAttribute('inert', '');
    const firstTarget = sidebar.querySelector('a, button, input, summary');
    window.requestAnimationFrame(() => firstTarget?.focus());
  };
  if (button && sidebar) button.addEventListener('click', () => {
    if (sidebar.classList.contains('open')) closeSidebar({ restoreFocus: true });
    else openSidebar();
  });
  if (backdrop) backdrop.addEventListener('click', () => closeSidebar({ restoreFocus: true }));
  sidebar?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => closeSidebar()));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && sidebar?.classList.contains('open')) {
      event.preventDefault();
      closeSidebar({ restoreFocus: true });
    }
  });

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


function initializeGuidedCaptureEvidence() {
  const form = document.querySelector('[data-guided-capture-form]');
  if (!form) return;
  const file = form.querySelector('input[name="evidence_file"]');
  const existing = form.querySelector('select[name="evidence_id"]');
  file?.addEventListener('change', () => {
    if (file.files?.length && existing) existing.value = '';
  });
  existing?.addEventListener('change', () => {
    if (existing.value && file) file.value = '';
  });
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
  initializeGuidedCaptureEvidence();
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

function initializeGuidedSetupWizard() {
  const form = document.querySelector('[data-guided-setup]');
  if (!form) return;
  const steps = Array.from(form.querySelectorAll('[data-guided-step]'));
  const indicators = Array.from(form.querySelectorAll('[data-guided-indicator]'));
  const progress = form.querySelector('[data-guided-progress]');
  const counter = form.querySelector('[data-guided-counter]');
  const title = form.querySelector('[data-guided-title]');
  const back = form.querySelector('[data-guided-back]');
  const next = form.querySelector('[data-guided-next]');
  const submit = form.querySelector('[data-guided-submit]');
  const titles = ['Propósito', 'Operación', 'Cobertura', 'Información', 'Gobierno'];
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
    if (index > current && !validateCurrent()) return;
    current = index;
    render(true);
  }));
  form.addEventListener('submit', (event) => {
    if (!validateCurrent()) event.preventDefault();
  });
  render();
}

document.addEventListener('DOMContentLoaded', initializeGuidedSetupWizard);


function initializeProgressiveDisclosure() {
  const details = Array.from(document.querySelectorAll('details[data-exclusive-details]'));
  details.forEach((item) => {
    item.addEventListener('toggle', () => {
      if (!item.open) return;
      const group = item.dataset.exclusiveDetails;
      details.forEach((other) => {
        if (other !== item && other.open && other.dataset.exclusiveDetails === group) other.open = false;
      });
    });
  });

  const revealTarget = () => {
    if (!window.location.hash) return;
    const target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    if (!target) return;
    let disclosure = target.closest('details');
    while (disclosure) {
      disclosure.open = true;
      disclosure = disclosure.parentElement?.closest('details') || null;
    }
  };
  window.addEventListener('hashchange', revealTarget);
  revealTarget();

  document.addEventListener('invalid', (event) => {
    let disclosure = event.target.closest?.('details');
    while (disclosure) {
      disclosure.open = true;
      disclosure = disclosure.parentElement?.closest('details') || null;
    }
  }, true);
}

document.addEventListener('DOMContentLoaded', initializeProgressiveDisclosure);

function initializeNavigationSearch() {
  const input = document.getElementById('navSearch');
  const sidebar = document.getElementById('sidebar');
  if (!input || !sidebar) return;
  const normalize = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  const items = Array.from(sidebar.querySelectorAll('.nav-item'));
  const groups = Array.from(sidebar.querySelectorAll('.nav-group'));
  const disclosures = Array.from(sidebar.querySelectorAll('.nav-disclosure'));
  const render = () => {
    const query = normalize(input.value);
    items.forEach((item) => item.classList.toggle('nav-filter-hidden', Boolean(query) && !normalize(item.textContent).includes(query)));
    groups.forEach((group) => {
      const visible = Array.from(group.querySelectorAll('.nav-item')).some((item) => !item.classList.contains('nav-filter-hidden'));
      group.classList.toggle('nav-filter-hidden', Boolean(query) && !visible);
    });
    disclosures.forEach((details) => {
      const visible = Array.from(details.querySelectorAll('.nav-item')).some((item) => !item.classList.contains('nav-filter-hidden'));
      details.classList.toggle('nav-filter-hidden', Boolean(query) && !visible);
      if (query && visible) details.open = true;
    });
  };
  input.addEventListener('input', render);
}

document.addEventListener('DOMContentLoaded', () => {
  initializeNavigationSearch();
  document.addEventListener('click', (event) => {
    document.querySelectorAll('.org-switcher[open]').forEach((details) => {
      if (!details.contains(event.target)) details.removeAttribute('open');
    });
  });
});

/* Iteración 12 · navegación por tareas y experiencia móvil */
function initializeTaskTabs() {
  const tabsets = Array.from(document.querySelectorAll('[data-task-tabs]'));
  if (!tabsets.length) return;

  const targetFromHash = () => {
    if (!window.location.hash) return '';
    const id = decodeURIComponent(window.location.hash.slice(1));
    const target = document.getElementById(id);
    return target?.dataset?.taskPanel || target?.closest?.('[data-task-panel]')?.dataset?.taskPanel || '';
  };

  tabsets.forEach((tabset) => {
    const tabs = Array.from(tabset.querySelectorAll('[data-task-target]'));
    const panels = Array.from(document.querySelectorAll('[data-task-panel]'));
    if (!tabs.length || !panels.length) return;

    const activate = (task, { updateHash = false, focus = false } = {}) => {
      const normalized = task || tabset.dataset.defaultTask || tabs[0].dataset.taskTarget;
      tabs.forEach((tab) => {
        const active = tab.dataset.taskTarget === normalized;
        tab.classList.toggle('active', active);
        tab.setAttribute('aria-selected', String(active));
        tab.setAttribute('tabindex', active ? '0' : '-1');
      });
      panels.forEach((panel) => {
        const active = panel.dataset.taskPanel === normalized;
        panel.hidden = !active;
        panel.classList.toggle('active-task-panel', active);
      });
      tabset.dataset.activeTask = normalized;
      if (updateHash) {
        const activeTab = tabs.find((tab) => tab.dataset.taskTarget === normalized);
        const hash = activeTab?.getAttribute('href') || '';
        if (hash.startsWith('#')) history.replaceState(null, '', hash);
      }
      if (focus) {
        const panel = panels.find((item) => item.dataset.taskPanel === normalized);
        panel?.querySelector('h2, h3, summary')?.focus?.({ preventScroll: true });
        panel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };

    tabs.forEach((tab) => tab.addEventListener('click', (event) => {
      event.preventDefault();
      activate(tab.dataset.taskTarget, { updateHash: true, focus: true });
    }));
    tabset.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      const current = Math.max(0, tabs.findIndex((tab) => tab.classList.contains('active')));
      const next = event.key === 'ArrowRight' ? (current + 1) % tabs.length : (current - 1 + tabs.length) % tabs.length;
      event.preventDefault();
      tabs[next].click();
    });
    tabset.setAttribute('role', 'tablist');
    tabs.forEach((tab) => tab.setAttribute('role', 'tab'));
    document.documentElement.classList.add('task-tabs-enhanced');
    activate(targetFromHash() || tabset.dataset.defaultTask);
  });

  window.addEventListener('hashchange', () => {
    const task = targetFromHash();
    if (!task) return;
    tabsets.forEach((tabset) => {
      const tab = tabset.querySelector(`[data-task-target="${CSS.escape(task)}"]`);
      if (tab) tab.click();
    });
  });
}

function initializeMobileTaskbar() {
  const button = document.querySelector('[data-open-mobile-menu]');
  const menuButton = document.getElementById('menuButton');
  if (!button || !menuButton) return;
  button.addEventListener('click', () => menuButton.click());
}

function initializeUnsavedFormGuard() {
  let dirtyForm = null;
  document.querySelectorAll('form[data-guard-unsaved]').forEach((form) => {
    form.addEventListener('input', () => { dirtyForm = form; form.classList.add('form-has-changes'); });
    form.addEventListener('change', () => { dirtyForm = form; form.classList.add('form-has-changes'); });
    form.addEventListener('submit', () => { dirtyForm = null; form.classList.remove('form-has-changes'); });
  });
  window.addEventListener('beforeunload', (event) => {
    if (!dirtyForm) return;
    event.preventDefault();
    event.returnValue = '';
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initializeTaskTabs();
  initializeMobileTaskbar();
  initializeUnsavedFormGuard();
});


/* Iteración 13 · accesibilidad, ayuda contextual y primer ingreso */
function announce(message) {
  const region = document.getElementById('live-region');
  if (!region || !message) return;
  region.textContent = '';
  window.requestAnimationFrame(() => { region.textContent = message; });
}

function openAccessibleDialog(dialog, trigger) {
  if (!dialog) return;
  dialog.__returnFocus = trigger || document.activeElement;
  if (typeof dialog.showModal === 'function') dialog.showModal();
  else dialog.setAttribute('open', '');
  const focusTarget = dialog.querySelector('[autofocus], h2, [data-tour-step]:not([hidden]), button, a, input, select, textarea');
  if (focusTarget?.matches('h2, [data-tour-step]')) focusTarget.setAttribute('tabindex', '-1');
  window.requestAnimationFrame(() => focusTarget?.focus());
}

function closeAccessibleDialog(dialog) {
  if (!dialog) return;
  if (typeof dialog.close === 'function' && dialog.open) dialog.close();
  else dialog.removeAttribute('open');
  const target = dialog.__returnFocus;
  if (target instanceof HTMLElement && document.contains(target)) target.focus();
}

function initializeAccessibleDialogs() {
  const helpDialog = document.getElementById('contextHelpDialog');
  const tourDialog = document.getElementById('welcomeTourDialog');
  const glossaryDialog = document.getElementById('plainLanguageDialog');
  document.querySelectorAll('[data-open-context-help]').forEach((button) => {
    button.addEventListener('click', () => openAccessibleDialog(helpDialog, button));
  });
  document.querySelectorAll('[data-open-glossary]').forEach((button) => {
    button.addEventListener('click', () => {
      const parentDialog = button.closest('dialog');
      const returnTarget = document.querySelector('.plain-language-button') || button;
      if (parentDialog?.open) closeAccessibleDialog(parentDialog);
      openAccessibleDialog(glossaryDialog, returnTarget);
    });
  });
  document.querySelectorAll('[data-open-tour]').forEach((button) => {
    button.addEventListener('click', () => {
      tourDialog?.dispatchEvent(new CustomEvent('tour:reset'));
      openAccessibleDialog(tourDialog, button);
    });
  });
  document.querySelectorAll('[data-close-dialog]').forEach((button) => {
    button.addEventListener('click', () => closeAccessibleDialog(button.closest('dialog')));
  });
  document.querySelectorAll('dialog').forEach((dialog) => {
    dialog.addEventListener('click', (event) => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      const inside = event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom;
      if (!inside) closeAccessibleDialog(dialog);
    });
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      closeAccessibleDialog(dialog);
    });
  });
}

function initializeWelcomeTour() {
  const dialog = document.getElementById('welcomeTourDialog');
  if (!dialog) return;
  const steps = Array.from(dialog.querySelectorAll('[data-tour-step]'));
  const back = dialog.querySelector('[data-tour-back]');
  const next = dialog.querySelector('[data-tour-next]');
  const finish = dialog.querySelector('[data-tour-finish]');
  const skipButtons = Array.from(dialog.querySelectorAll('[data-tour-skip]'));
  const status = dialog.querySelector('[data-tour-status]');
  const progress = dialog.querySelector('[data-tour-progress]');
  const storageKey = dialog.dataset.tourStorageKey || 'cth-tour-v14';
  let current = 0;

  const remember = () => {
    try { window.localStorage.setItem(storageKey, 'completed'); } catch (_error) { /* storage can be disabled */ }
  };
  const render = ({ focus = false } = {}) => {
    steps.forEach((step, index) => {
      step.hidden = index !== current;
      step.setAttribute('aria-hidden', String(index !== current));
    });
    if (back) back.hidden = current === 0;
    if (next) next.hidden = current === steps.length - 1;
    if (finish) finish.hidden = current !== steps.length - 1;
    if (status) status.textContent = `Paso ${current + 1} de ${steps.length}`;
    if (progress) progress.style.width = `${((current + 1) / steps.length) * 100}%`;
    if (focus) steps[current]?.focus();
    announce(`Recorrido guiado. Paso ${current + 1} de ${steps.length}.`);
  };
  const complete = () => {
    remember();
    closeAccessibleDialog(dialog);
    announce('Recorrido guiado completado.');
  };
  next?.addEventListener('click', () => {
    current = Math.min(current + 1, steps.length - 1);
    render({ focus: true });
  });
  back?.addEventListener('click', () => {
    current = Math.max(current - 1, 0);
    render({ focus: true });
  });
  finish?.addEventListener('click', complete);
  skipButtons.forEach((button) => button.addEventListener('click', complete));
  dialog.addEventListener('tour:reset', () => {
    current = 0;
    render();
  });
  dialog.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowRight' && !next?.hidden) next.click();
    if (event.key === 'ArrowLeft' && !back?.hidden) back.click();
  });
  render();

  let completed = false;
  try { completed = window.localStorage.getItem(storageKey) === 'completed'; } catch (_error) { completed = false; }
  if (!completed) window.setTimeout(() => openAccessibleDialog(dialog, document.querySelector('[data-open-tour]')), 350);
}

function initializeFormAccessibility() {
  const summary = document.getElementById('form-error-summary');
  const labelFor = (control) => {
    const explicit = control.id ? document.querySelector(`label[for="${CSS.escape(control.id)}"]`) : null;
    const wrapping = control.closest('label');
    const label = explicit || wrapping;
    if (!label) return control.name || 'Campo';
    const clone = label.cloneNode(true);
    clone.querySelectorAll('input, select, textarea, small, button').forEach((node) => node.remove());
    return clone.textContent.trim().replace(/\s+/g, ' ') || control.name || 'Campo';
  };
  const invalidControls = (form) => Array.from(form.querySelectorAll('input, select, textarea'))
    .filter((control) => control.matches(':invalid'));
  const showSummary = (form) => {
    if (!summary) return;
    const invalid = invalidControls(form);
    if (!invalid.length) {
      summary.hidden = true;
      summary.textContent = '';
      return;
    }
    summary.replaceChildren();
    const heading = document.createElement('strong');
    heading.textContent = `Revisa ${invalid.length === 1 ? 'el campo indicado' : 'los campos indicados'}.`;
    const list = document.createElement('ul');
    invalid.slice(0, 8).forEach((control, index) => {
      control.setAttribute('aria-invalid', 'true');
      if (!control.id) control.id = `invalid-field-${Date.now()}-${index}`;
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = `#${control.id}`;
      link.dataset.errorTarget = control.id;
      link.textContent = labelFor(control);
      item.appendChild(link);
      list.appendChild(item);
    });
    if (invalid.length > 8) {
      const item = document.createElement('li');
      item.textContent = `Y ${invalid.length - 8} campo(s) adicional(es).`;
      list.appendChild(item);
    }
    summary.append(heading, list);
    summary.hidden = false;
    summary.focus();
    invalid[0].closest('details')?.setAttribute('open', '');
    announce(`El formulario contiene ${invalid.length} campo${invalid.length === 1 ? '' : 's'} por corregir.`);
  };

  document.querySelectorAll('input[required], select[required], textarea[required]').forEach((control) => {
    control.setAttribute('aria-required', 'true');
    const label = control.closest('label') || (control.id && document.querySelector(`label[for="${CSS.escape(control.id)}"]`));
    if (label && !label.querySelector('.required-marker')) {
      const marker = document.createElement('span');
      marker.className = 'required-marker';
      marker.setAttribute('aria-hidden', 'true');
      marker.textContent = ' *';
      const firstText = Array.from(label.childNodes).find((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
      if (firstText) firstText.after(marker);
      else label.prepend(marker);
    }
    const clearInvalid = () => {
      if (control.checkValidity()) control.removeAttribute('aria-invalid');
    };
    control.addEventListener('input', clearInvalid);
    control.addEventListener('change', clearInvalid);
  });

  document.querySelectorAll('form').forEach((form) => {
    if ((form.getAttribute('method') || '').toLowerCase() === 'dialog') return;
    let renderTimer = null;
    form.addEventListener('invalid', (event) => {
      event.target?.setAttribute?.('aria-invalid', 'true');
      window.clearTimeout(renderTimer);
      renderTimer = window.setTimeout(() => showSummary(form), 0);
    }, true);
    form.addEventListener('submit', (event) => {
      const invalid = invalidControls(form);
      if (!invalid.length) {
        if (summary) summary.hidden = true;
        return;
      }
      event.preventDefault();
      showSummary(form);
    });
  });
  summary?.addEventListener('click', (event) => {
    const link = event.target.closest('[data-error-target]');
    if (!link) return;
    const control = document.getElementById(link.dataset.errorTarget || '');
    if (!control) return;
    event.preventDefault();
    control.closest('details')?.setAttribute('open', '');
    control.focus();
    control.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });
}
function initializeGlossarySearch() {
  const dialog = document.getElementById('plainLanguageDialog');
  const input = dialog?.querySelector('[data-glossary-search]');
  const items = Array.from(dialog?.querySelectorAll('[data-glossary-item]') || []);
  const status = dialog?.querySelector('[data-glossary-status]');
  const empty = dialog?.querySelector('[data-glossary-empty]');
  if (!input || !items.length) return;
  const normalize = (value) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const render = () => {
    const query = normalize(input.value.trim());
    let visible = 0;
    items.forEach((item) => {
      const match = !query || normalize(item.textContent || '').includes(query);
      item.hidden = !match;
      if (match) visible += 1;
    });
    if (status) status.textContent = query ? `${visible} término${visible === 1 ? '' : 's'} encontrado${visible === 1 ? '' : 's'}.` : `${items.length} términos disponibles.`;
    if (empty) empty.hidden = visible !== 0;
  };
  input.addEventListener('input', render);
  dialog.addEventListener('close', () => { input.value = ''; render(); });
  render();
}

function initializeFieldDescriptions() {
  let counter = 0;
  const appendDescription = (control, id) => {
    const existing = (control.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
    if (!existing.includes(id)) existing.push(id);
    control.setAttribute('aria-describedby', existing.join(' '));
  };
  document.querySelectorAll('label').forEach((label) => {
    const control = label.querySelector(':scope > input, :scope > select, :scope > textarea');
    const help = label.querySelector(':scope > small');
    if (!control || !help) return;
    if (!help.id) help.id = `field-help-${++counter}`;
    appendDescription(control, help.id);
  });
  document.querySelectorAll('input[type="number"]').forEach((control) => {
    if (!control.inputMode) control.inputMode = 'decimal';
  });
}

function initializeCapturePreview() {
  const form = document.querySelector('[data-guided-capture-form]');
  const preview = form?.querySelector('[data-capture-preview]');
  if (!form || !preview) return;
  const value = form.querySelector('[name="value"]');
  const unit = form.querySelector('[name="unit"]');
  const start = form.querySelector('[name="period_start"]');
  const end = form.querySelector('[name="period_end"]');
  const file = form.querySelector('[name="evidence_file"]');
  const existing = form.querySelector('[name="evidence_id"]');
  const estimated = form.querySelector('[name="is_estimated"]');
  const formatDate = (raw) => raw ? raw.split('-').reverse().join('/') : 'sin fecha';
  const render = () => {
    const amount = value?.value?.trim();
    const evidence = file?.files?.length ? `archivo ${file.files[0].name}` : existing?.selectedOptions?.[0]?.value ? `evidencia ${existing.selectedOptions[0].textContent.trim()}` : 'sin soporte asociado';
    const provisional = estimated?.checked ? ' El dato quedará marcado como estimado.' : '';
    const strong = preview.querySelector('strong');
    const detail = preview.querySelector('p');
    if (!amount) {
      if (strong) strong.textContent = 'Completa la cantidad para revisar el registro.';
      if (detail) detail.textContent = 'La aprobación metodológica seguirá siendo humana.';
      return;
    }
    if (strong) strong.textContent = `Registrarás ${amount} ${unit?.value || ''} para esta fuente.`;
    if (detail) detail.textContent = `Periodo ${formatDate(start?.value)} a ${formatDate(end?.value)}; ${evidence}.${provisional}`;
  };
  form.querySelectorAll('input, select, textarea').forEach((control) => {
    control.addEventListener('input', render);
    control.addEventListener('change', render);
  });
  render();
}

function initializeDisclosureAccessibility() {
  document.querySelectorAll('details').forEach((details) => {
    const summary = details.querySelector(':scope > summary');
    if (!summary) return;
    summary.setAttribute('aria-expanded', String(details.open));
    details.addEventListener('toggle', () => summary.setAttribute('aria-expanded', String(details.open)));
  });
}

function initializeFlashFocus() {
  const flash = document.querySelector('.flash[role="alert"]');
  if (flash) window.requestAnimationFrame(() => flash.focus());
}


function initializeTableAccessibility() {
  document.querySelectorAll('.responsive-table').forEach((wrapper, index) => {
    const table = wrapper.querySelector('table');
    if (!table) return;
    let caption = table.querySelector('caption');
    const container = wrapper.closest('section, article, .card') || wrapper.parentElement;
    const heading = container?.querySelector('h1, h2, h3, h4');
    const label = heading?.textContent?.trim() || `Tabla de datos ${index + 1}`;
    if (!caption) {
      caption = document.createElement('caption');
      caption.className = 'sr-only';
      caption.textContent = label;
      table.prepend(caption);
    }
    wrapper.setAttribute('role', 'region');
    wrapper.setAttribute('aria-label', `${label}. Desplaza horizontalmente si es necesario.`);
    wrapper.setAttribute('tabindex', '0');
  });
}

function initializeReducedMotion() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) document.documentElement.classList.add('reduce-motion');
}

document.addEventListener('DOMContentLoaded', () => {
  initializeAccessibleDialogs();
  initializeWelcomeTour();
  initializeGlossarySearch();
  initializeFieldDescriptions();
  initializeFormAccessibility();
  initializeCapturePreview();
  initializeDisclosureAccessibility();
  initializeFlashFocus();
  initializeTableAccessibility();
  initializeReducedMotion();
});
