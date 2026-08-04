/* Calcula tu Huella · Frontend Kit v1 · Experiencias guiadas. */

const CTH_DATA_FLOW_STEPS = [
  { key: 'sources', title: 'Fuentes', detail: 'Definir el mapa' },
  { key: 'data', title: 'Datos', detail: 'Capturar actividad' },
  { key: 'evidence', title: 'Evidencias', detail: 'Respaldar valores' },
  { key: 'quality', title: 'Calidad', detail: 'Resolver hallazgos' },
  { key: 'calculation', title: 'Cálculo', detail: 'Consolidar CO₂e' },
];

function currentDataFlowKey() {
  const path = window.location.pathname;
  if (/^\/fuentes\/\d+/.test(path) || path === '/calculos') return 'calculation';
  if (path === '/calidad-datos') return 'quality';
  if (path.startsWith('/cargas-operativas') || path.startsWith('/informacion/importar')) return 'data';
  if (path === '/informacion') return window.location.hash === '#evidencias' ? 'evidence' : 'data';
  if (/^\/inventarios\/\d+\/fuentes/.test(path)) return 'sources';
  return null;
}

function resolveSourcesHref() {
  const existing = document.querySelector('a[href^="/inventarios/"][href$="/fuentes"]');
  if (existing) return existing.getAttribute('href');
  if (/^\/inventarios\/\d+\/fuentes/.test(window.location.pathname)) return window.location.pathname;
  return '/inventarios';
}

function dataFlowHref(key) {
  const hrefs = {
    sources: resolveSourcesHref(),
    data: '/informacion#datos',
    evidence: '/informacion#evidencias',
    quality: '/calidad-datos',
    calculation: '/calculos',
  };
  return hrefs[key];
}

function syncDataFlowNavigation() {
  const current = currentDataFlowKey();
  document.querySelectorAll('[data-data-flow-step]').forEach((item) => {
    const active = item.dataset.dataFlowStep === current;
    item.classList.toggle('active', active);
    const link = item.querySelector('a');
    if (active) link?.setAttribute('aria-current', 'step');
    else link?.removeAttribute('aria-current');
  });
}

function initializeDataFlowNavigation() {
  const current = currentDataFlowKey();
  if (!current || document.querySelector('[data-data-flow-nav]')) return;
  const heading = document.querySelector('.page-head, .page-heading');
  if (!heading) return;

  const nav = document.createElement('nav');
  nav.className = 'data-flow-nav';
  nav.dataset.dataFlowNav = '';
  nav.setAttribute('aria-label', 'Flujo de preparación del inventario');

  const list = document.createElement('ol');
  list.className = 'data-flow-list';
  CTH_DATA_FLOW_STEPS.forEach((step, index) => {
    const item = document.createElement('li');
    item.className = 'data-flow-step';
    item.dataset.dataFlowStep = step.key;

    const link = document.createElement('a');
    link.href = dataFlowHref(step.key);

    const number = document.createElement('span');
    number.className = 'data-flow-step-number';
    number.textContent = String(index + 1);
    number.setAttribute('aria-hidden', 'true');

    const text = document.createElement('span');
    const title = document.createElement('strong');
    title.textContent = step.title;
    const detail = document.createElement('small');
    detail.textContent = step.detail;
    text.append(title, detail);
    link.append(number, text);
    item.append(link);
    list.append(item);
  });

  nav.append(list);
  heading.insertAdjacentElement('afterend', nav);
  document.body.classList.add('data-flow-page');
  syncDataFlowNavigation();
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 1) return '0 KB';
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function initializeFileIntakes() {
  document.querySelectorAll('input[type="file"]').forEach((input, index) => {
    if (input.dataset.fileIntakeEnhanced === 'true') return;
    const label = input.closest('label');
    if (!label) return;

    input.dataset.fileIntakeEnhanced = 'true';
    label.classList.add('file-intake-control');
    const status = document.createElement('small');
    status.className = 'file-intake-status';
    status.id = `file-intake-status-${index + 1}`;
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    status.textContent = 'Ningún archivo seleccionado.';
    input.insertAdjacentElement('afterend', status);

    const describedBy = [input.getAttribute('aria-describedby'), status.id].filter(Boolean).join(' ');
    input.setAttribute('aria-describedby', describedBy);

    const render = () => {
      const files = Array.from(input.files || []);
      status.classList.remove('ready', 'warning');
      if (!files.length) {
        status.textContent = 'Ningún archivo seleccionado.';
        return;
      }
      const total = files.reduce((sum, file) => sum + file.size, 0);
      status.textContent = files.length === 1
        ? `Seleccionado: ${files[0].name} · ${formatFileSize(total)}.`
        : `${files.length} archivos seleccionados · ${formatFileSize(total)}.`;
      status.classList.add(total > 10 * 1024 * 1024 ? 'warning' : 'ready');
      if (total > 10 * 1024 * 1024) status.textContent += ' Verifica el límite permitido antes de cargar.';
    };
    input.addEventListener('change', render);
    render();
  });
}

function normalizedSearchText(value) {
  return (value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es');
}

function tableFilterConfiguration() {
  const path = window.location.pathname;
  if (/^\/inventarios\/\d+\/fuentes/.test(path)) {
    return {
      card: '.source-management-layout .table-card',
      placeholder: 'Buscar fuente, sede, responsable o estado',
      label: 'Fuentes',
    };
  }
  if (path === '/informacion') {
    return {
      card: '#datos .information-layout > .card',
      placeholder: 'Buscar fuente, periodo, origen o estado',
      label: 'Registros',
    };
  }
  if (path === '/cargas-operativas') {
    return {
      card: '.operational-layout .table-card',
      placeholder: 'Buscar lote, archivo, perfil o estado',
      label: 'Lotes operativos',
    };
  }
  if (path === '/calidad-datos') {
    return {
      card: '.inventory-layout .table-card',
      placeholder: 'Buscar lote, archivo, estado o puntaje',
      label: 'Lotes de calidad',
    };
  }
  return null;
}

function initializePrimaryTableFilter() {
  const configuration = tableFilterConfiguration();
  if (!configuration) return;
  const card = document.querySelector(configuration.card);
  const table = card?.querySelector('.responsive-table table');
  const body = table?.querySelector('tbody');
  if (!card || !table || !body || card.querySelector('[data-table-toolbox]')) return;

  const rows = Array.from(body.querySelectorAll(':scope > tr')).filter((row) => !row.classList.contains('row-editor-line'));
  if (!rows.length) return;

  const toolbox = document.createElement('div');
  toolbox.className = 'table-toolbox';
  toolbox.dataset.tableToolbox = '';

  const label = document.createElement('label');
  label.className = 'table-search-label';
  label.setAttribute('aria-label', `Buscar en ${configuration.label}`);
  const input = document.createElement('input');
  input.type = 'search';
  input.placeholder = configuration.placeholder;
  input.autocomplete = 'off';
  label.append(input);

  const count = document.createElement('span');
  count.className = 'table-filter-count';
  count.setAttribute('aria-live', 'polite');

  const empty = document.createElement('p');
  empty.className = 'table-filter-empty';
  empty.hidden = true;
  empty.textContent = 'No hay resultados para esta búsqueda.';

  const render = () => {
    const query = normalizedSearchText(input.value.trim());
    let visible = 0;
    rows.forEach((row) => {
      const matches = !query || normalizedSearchText(row.textContent).includes(query);
      row.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = query ? `${visible} de ${rows.length}` : `${rows.length} registros`;
    empty.hidden = visible > 0;
  };

  input.addEventListener('input', render);
  toolbox.append(label, count);
  const cardHead = card.querySelector('.card-head');
  if (cardHead) cardHead.insertAdjacentElement('afterend', toolbox);
  else card.prepend(toolbox);
  table.closest('.responsive-table')?.insertAdjacentElement('afterend', empty);
  render();
}

function initializeResponsiveTableLabels() {
  document.querySelectorAll('.responsive-table').forEach((container, index) => {
    if (container.hasAttribute('tabindex')) return;
    const heading = container.closest('.card, section')?.querySelector('h2, h3');
    container.tabIndex = 0;
    container.setAttribute('role', 'region');
    container.setAttribute('aria-label', heading?.textContent?.trim() || `Tabla de datos ${index + 1}`);
  });
}

function initializeInventoryWizardAccessibility() {
  document.querySelectorAll('[data-inventory-wizard]').forEach((wizard) => {
    const indicators = Array.from(wizard.querySelectorAll('[data-inventory-indicator]'));
    const progress = wizard.querySelector('[data-inventory-progress-container]');
    if (!indicators.length || !progress) return;

    const sync = () => {
      let current = indicators.findIndex((indicator) => indicator.getAttribute('aria-current') === 'step');
      if (current < 0) current = 0;
      const value = current + 1;
      progress.setAttribute('aria-valuenow', String(value));
      progress.setAttribute('aria-valuetext', `Paso ${value} de ${indicators.length}`);
      indicators.forEach((indicator, index) => {
        indicator.setAttribute('aria-expanded', String(index === current));
      });
    };

    indicators.forEach((indicator) => {
      new MutationObserver(sync).observe(indicator, {
        attributes: true,
        attributeFilter: ['aria-current', 'class'],
      });
    });
    sync();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initializeInventoryWizardAccessibility();
  initializeDataFlowNavigation();
  initializeFileIntakes();
  initializePrimaryTableFilter();
  initializeResponsiveTableLabels();
});

window.addEventListener('hashchange', syncDataFlowNavigation);
