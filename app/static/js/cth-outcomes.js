/* Calcula tu Huella · Frontend Kit v1 · Resultados y decisiones. */

const CTH_OUTCOME_STEPS = [
  { key: 'calculation', title: 'Cálculo', detail: 'Consolidar CO₂e', href: '/calculos' },
  { key: 'control', title: 'Control', detail: 'Validar y aprobar', href: '/control' },
  { key: 'reports', title: 'Informes', detail: 'Documentar resultados', href: '/reportes' },
  { key: 'reduction', title: 'Reducción', detail: 'Priorizar medidas', href: '/reduccion' },
  { key: 'scenarios', title: 'Escenarios', detail: 'Comparar trayectorias', href: '/escenarios' },
];

const CTH_OUTCOME_CONTEXT = {
  calculation: {
    eyebrow: 'LECTURA METODOLÓGICA',
    title: 'Confirma que el resultado sea calculable y trazable.',
    detail: 'Resuelve errores de conversión, factores o GWP antes de iniciar la revisión profesional.',
    action: 'Revisar condiciones',
    href: '/control',
  },
  control: {
    eyebrow: 'ASEGURAMIENTO',
    title: 'Convierte el resultado técnico en una versión aprobable.',
    detail: 'Las observaciones, puertas de calidad y segregación de funciones gobiernan el cierre del inventario.',
    action: 'Preparar informes',
    href: '/reportes',
  },
  reports: {
    eyebrow: 'COMUNICACIÓN TRAZABLE',
    title: 'Selecciona el entregable según la decisión que debe soportar.',
    detail: 'El informe ejecutivo, el técnico y la memoria de cálculo conservan estados, versiones e integridad.',
    action: 'Gestionar reducción',
    href: '/reduccion',
  },
  reduction: {
    eyebrow: 'DECISIÓN CLIMÁTICA',
    title: 'Prioriza medidas por impacto, viabilidad, inversión y retorno.',
    detail: 'Asigna responsables y fechas antes de comparar el portafolio dentro de una trayectoria.',
    action: 'Comparar escenarios',
    href: '/escenarios',
  },
  scenarios: {
    eyebrow: 'PORTAFOLIO Y TRAYECTORIA',
    title: 'Compara combinaciones de medidas, adopción y año de implementación.',
    detail: 'La curva marginal y la trayectoria permiten discutir costo, riesgo y emisiones proyectadas.',
    action: 'Volver al plan',
    href: '/reduccion',
  },
};

function currentOutcomeKey() {
  const path = window.location.pathname;
  if (path === '/calculos') return 'calculation';
  if (path === '/control') return 'control';
  if (path === '/reportes') return 'reports';
  if (path === '/reduccion') return 'reduction';
  if (path === '/escenarios') return 'scenarios';
  return null;
}

function initializeOutcomeNavigation() {
  const current = currentOutcomeKey();
  if (!current || document.querySelector('[data-outcome-flow-nav]')) return;
  const heading = document.querySelector('.page-head, .page-heading');
  if (!heading) return;

  // Cálculo es la salida del flujo de captura y la entrada del flujo de decisiones.
  document.querySelector('[data-data-flow-nav]')?.remove();

  const nav = document.createElement('nav');
  nav.className = 'outcome-flow-nav';
  nav.dataset.outcomeFlowNav = '';
  nav.setAttribute('aria-label', 'Flujo de resultados y decisiones');

  const list = document.createElement('ol');
  list.className = 'outcome-flow-list';
  CTH_OUTCOME_STEPS.forEach((step, index) => {
    const item = document.createElement('li');
    item.className = 'outcome-flow-step';
    if (step.key === current) item.classList.add('active');

    const link = document.createElement('a');
    link.href = step.href;
    if (step.key === current) link.setAttribute('aria-current', 'step');

    const number = document.createElement('span');
    number.className = 'outcome-flow-step-number';
    number.textContent = String(index + 1);
    number.setAttribute('aria-hidden', 'true');

    const copy = document.createElement('span');
    const title = document.createElement('strong');
    title.textContent = step.title;
    const detail = document.createElement('small');
    detail.textContent = step.detail;
    copy.append(title, detail);
    link.append(number, copy);
    item.append(link);
    list.append(item);
  });

  nav.append(list);
  heading.insertAdjacentElement('afterend', nav);
  document.body.classList.add('outcome-page');

  const context = CTH_OUTCOME_CONTEXT[current];
  if (!context) return;
  const section = document.createElement('section');
  section.className = 'outcome-context';
  section.setAttribute('aria-label', 'Orientación para la etapa actual');

  const copy = document.createElement('div');
  copy.className = 'outcome-context-copy';
  const eyebrow = document.createElement('small');
  eyebrow.textContent = context.eyebrow;
  const title = document.createElement('strong');
  title.textContent = context.title;
  const detail = document.createElement('p');
  detail.textContent = context.detail;
  copy.append(eyebrow, title, detail);

  const action = document.createElement('a');
  action.className = 'btn btn-outline';
  action.href = context.href;
  action.textContent = context.action;
  section.append(copy, action);
  nav.insertAdjacentElement('afterend', section);
}

function numericWidth(element) {
  const raw = element?.style?.width || '';
  const parsed = Number.parseFloat(raw);
  if (!Number.isFinite(parsed)) return null;
  return Math.max(0, Math.min(100, parsed));
}

function enhanceOutcomeProgressBars() {
  document.querySelectorAll('.outcome-page .progress').forEach((progress, index) => {
    if (progress.dataset.outcomeProgress === 'true') return;
    const value = numericWidth(progress.querySelector('i'));
    if (value === null) return;
    progress.dataset.outcomeProgress = 'true';
    progress.tabIndex = 0;
    progress.setAttribute('role', 'progressbar');
    progress.setAttribute('aria-valuemin', '0');
    progress.setAttribute('aria-valuemax', '100');
    progress.setAttribute('aria-valuenow', String(Math.round(value)));
    const cardTitle = progress.closest('article, .card')?.querySelector('h2, h3, strong')?.textContent?.trim();
    progress.setAttribute('aria-label', cardTitle ? `Avance de ${cardTitle}` : `Indicador de avance ${index + 1}`);
  });
}

function enhanceScenarioTracks() {
  document.querySelectorAll('.macc-row, .trajectory-row').forEach((row) => {
    if (row.dataset.outcomeTrack === 'true') return;
    row.dataset.outcomeTrack = 'true';
    row.tabIndex = 0;
    row.setAttribute('role', 'group');
    row.setAttribute('aria-label', row.textContent.replace(/\s+/g, ' ').trim());
  });
}

function normalizedOutcomeText(value) {
  return (value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es');
}

function createFilterToolbox(container, items, options) {
  if (!container || !items.length || container.parentElement?.querySelector('[data-outcome-toolbox]')) return;
  const toolbox = document.createElement('div');
  toolbox.className = 'outcome-card-toolbox';
  toolbox.dataset.outcomeToolbox = '';

  const label = document.createElement('label');
  label.setAttribute('aria-label', options.label);
  const input = document.createElement('input');
  input.type = 'search';
  input.placeholder = options.placeholder;
  input.autocomplete = 'off';
  label.append(input);

  const count = document.createElement('span');
  count.className = 'outcome-card-count';
  count.setAttribute('aria-live', 'polite');

  const empty = document.createElement('p');
  empty.className = 'outcome-card-empty';
  empty.hidden = true;
  empty.textContent = options.empty;

  const render = () => {
    const query = normalizedOutcomeText(input.value.trim());
    let visible = 0;
    items.forEach((item) => {
      const matches = !query || normalizedOutcomeText(item.textContent).includes(query);
      item.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = query ? `${visible} de ${items.length}` : `${items.length} elementos`;
    empty.hidden = visible > 0;
  };

  input.addEventListener('input', render);
  toolbox.append(label, count);
  container.insertAdjacentElement('beforebegin', toolbox);
  container.insertAdjacentElement('afterend', empty);
  render();
}

function initializeOutcomeCardFilters() {
  const path = window.location.pathname;
  if (path === '/reduccion') {
    const container = document.querySelector('.action-card-grid');
    const items = Array.from(container?.querySelectorAll(':scope > .action-card') || []);
    createFilterToolbox(container, items, {
      label: 'Buscar medidas de reducción',
      placeholder: 'Buscar medida, fuente, responsable, prioridad o estado',
      empty: 'No hay medidas que coincidan con la búsqueda.',
    });
  }
  if (path === '/control') {
    const container = document.querySelector('.observation-list');
    const items = Array.from(container?.querySelectorAll(':scope > .observation-item') || []);
    createFilterToolbox(container, items, {
      label: 'Buscar observaciones de revisión',
      placeholder: 'Buscar observación, severidad, responsable o estado',
      empty: 'No hay observaciones que coincidan con la búsqueda.',
    });
  }
}

function outcomeTableConfiguration() {
  const path = window.location.pathname;
  if (path === '/calculos') {
    return {
      table: 'section.card:not(.engine-rules) .responsive-table table',
      placeholder: 'Buscar fuente, alcance, alerta o resultado',
      label: 'resultados de cálculo',
    };
  }
  if (path === '/reportes') {
    return {
      table: '.report-history .responsive-table table',
      placeholder: 'Buscar tipo, versión, estado, autor o fecha',
      label: 'documentos generados',
    };
  }
  if (path === '/escenarios') {
    return {
      table: '.scenario-main .table-wrap table',
      placeholder: 'Buscar medida, costo, retorno, riesgo o viabilidad',
      label: 'medidas del escenario',
    };
  }
  return null;
}

function initializeOutcomeTableFilter() {
  const configuration = outcomeTableConfiguration();
  if (!configuration) return;
  const table = document.querySelector(configuration.table);
  const body = table?.querySelector('tbody');
  const container = table?.closest('.responsive-table, .table-wrap');
  const card = table?.closest('.card');
  if (!table || !body || !container || !card || card.querySelector('[data-outcome-toolbox]')) return;
  const rows = Array.from(body.querySelectorAll(':scope > tr'));
  if (!rows.length) return;

  const toolbox = document.createElement('div');
  toolbox.className = 'outcome-card-toolbox';
  toolbox.dataset.outcomeToolbox = '';
  const label = document.createElement('label');
  label.setAttribute('aria-label', `Buscar en ${configuration.label}`);
  const input = document.createElement('input');
  input.type = 'search';
  input.placeholder = configuration.placeholder;
  input.autocomplete = 'off';
  label.append(input);
  const count = document.createElement('span');
  count.className = 'outcome-card-count';
  count.setAttribute('aria-live', 'polite');
  const empty = document.createElement('p');
  empty.className = 'outcome-card-empty';
  empty.hidden = true;
  empty.textContent = 'No hay resultados para esta búsqueda.';

  const render = () => {
    const query = normalizedOutcomeText(input.value.trim());
    let visible = 0;
    rows.forEach((row) => {
      const matches = !query || normalizedOutcomeText(row.textContent).includes(query);
      row.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = query ? `${visible} de ${rows.length}` : `${rows.length} registros`;
    empty.hidden = visible > 0;
  };

  input.addEventListener('input', render);
  toolbox.append(label, count);
  const head = card.querySelector('.card-head');
  if (head) head.insertAdjacentElement('afterend', toolbox);
  else card.prepend(toolbox);
  container.insertAdjacentElement('afterend', empty);
  render();
}

function enhanceReportDeliverables() {
  const grid = document.querySelector('.deliverable-grid');
  if (!grid) return;
  grid.setAttribute('role', 'list');
  grid.querySelectorAll(':scope > .deliverable-card').forEach((card) => {
    card.setAttribute('role', 'listitem');
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initializeOutcomeNavigation();
  enhanceOutcomeProgressBars();
  enhanceScenarioTracks();
  initializeOutcomeCardFilters();
  initializeOutcomeTableFilter();
  enhanceReportDeliverables();
});
