(() => {
  const shell = document.querySelector('[data-preview-shell]');
  if (!shell) return;

  const titles = {
    trabajo: ['PRÓXIMA ACCIÓN', 'Completar información pendiente', '4 solicitudes requieren atención antes de cerrar la recopilación.'],
    informacion: ['INFORMACIÓN DEL INVENTARIO', 'Datos y evidencias por fuente', 'Consulta responsables, periodos, soportes y estado de recopilación.'],
    calidad: ['CONTROL DE CALIDAD', 'Resolver observaciones antes de aprobar', 'La calidad se revisa de forma explícita antes de consolidar y cerrar.'],
    calculo: ['RESULTADO Y TRAZABILIDAD', 'Construir un resultado reproducible', 'Cada resultado conserva su relación con datos, factores, fórmulas y versiones.'],
    analisis: ['LECTURA DEL INVENTARIO', 'Entender qué explica la huella', 'Prioriza hotspots, variaciones y señales que requieren una decisión.'],
    reduccion: ['PLAN DE ACCIÓN', 'Convertir hotspots en reducción gestionable', 'Separa potencial, implementación, seguimiento y resultado observado.'],
    control: ['PUERTAS DE CALIDAD', 'Saber qué impide aprobar', 'Completitud, calidad, metodología y segregación se revisan antes del cierre.'],
    informes: ['ENTREGABLES', 'Comunicar sin perder trazabilidad', 'Una misma versión controlada alimenta informes para distintos destinatarios.']
  };

  const roleFocus = {
    Consultor: ['Preparar y coordinar el inventario', 'El consultor conecta fuentes, responsables, calidad, cálculo y entregables sin perder trazabilidad.'],
    Administrador: ['Mantener estructura, usuarios y continuidad', 'La vista administrativa prioriza configuración, responsables, periodos y condiciones para que el trabajo pueda operar.'],
    Cliente: ['Responder solicitudes y aportar evidencia', 'La vista cliente reduce el trabajo a pendientes concretos: qué dato falta, qué soporte se espera y cuándo debe entregarse.'],
    Revisor: ['Evaluar calidad y resolver observaciones', 'La vista de revisión concentra suficiencia, consistencia, limitaciones, hallazgos y decisiones antes de aprobar internamente.'],
    Verificador: ['Recorrer evidencia y trazabilidad', 'La vista de verificación prioriza acceso ordenado a metodología, evidencia, hallazgos y cadena de cálculo sin asumir independencia automática.']
  };

  const navs = [...shell.querySelectorAll('[data-preview-view]')];
  const panels = [...shell.querySelectorAll('[data-preview-panel]')];
  const kicker = shell.querySelector('[data-preview-kicker]');
  const title = shell.querySelector('[data-preview-title]');
  const subtitle = shell.querySelector('[data-preview-subtitle]');
  const roleLabel = shell.querySelector('[data-preview-role]');
  const roleSelect = shell.querySelector('[data-preview-role-select]');
  const roleFocusTitle = shell.querySelector('[data-preview-role-focus-title]');
  const roleFocusText = shell.querySelector('[data-preview-role-focus-text]');

  const show = (view) => {
    navs.forEach(button => button.classList.toggle('active', button.dataset.previewView === view));
    panels.forEach(panel => {
      const active = panel.dataset.previewPanel === view;
      panel.hidden = !active;
      panel.classList.toggle('active', active);
    });
    const copy = titles[view] || titles.trabajo;
    kicker.textContent = copy[0];
    title.textContent = copy[1];
    subtitle.textContent = copy[2];
    try { localStorage.setItem('cth-pages-preview-view', view); } catch (_) {}
  };

  const applyRoleFocus = (role) => {
    const copy = roleFocus[role] || roleFocus.Consultor;
    if (roleLabel) roleLabel.textContent = role;
    if (roleFocusTitle) roleFocusTitle.textContent = copy[0];
    if (roleFocusText) roleFocusText.textContent = copy[1];
  };

  navs.forEach(button => button.addEventListener('click', () => show(button.dataset.previewView)));

  if (roleSelect) {
    try {
      const savedRole = localStorage.getItem('cth-pages-preview-role');
      if (savedRole && [...roleSelect.options].some(option => option.value === savedRole)) roleSelect.value = savedRole;
    } catch (_) {}
    applyRoleFocus(roleSelect.value);
    roleSelect.addEventListener('change', () => {
      applyRoleFocus(roleSelect.value);
      try { localStorage.setItem('cth-pages-preview-role', roleSelect.value); } catch (_) {}
    });
  }

  shell.querySelectorAll('[data-preview-action="resolve"]').forEach(button => {
    let resolved = false;
    try { resolved = localStorage.getItem('cth-pages-preview-resolved') === '1'; } catch (_) {}
    const apply = () => {
      button.textContent = resolved ? 'Gestionado ✓' : 'Marcar como gestionado';
      button.disabled = resolved;
      if (resolved) button.closest('.preview-card')?.classList.add('is-resolved');
    };
    apply();
    button.addEventListener('click', () => {
      resolved = true;
      try { localStorage.setItem('cth-pages-preview-resolved', '1'); } catch (_) {}
      apply();
    });
  });

  const qualityCard = shell.querySelector('[data-preview-quality-card]');
  const qualityDecision = shell.querySelector('[data-preview-quality-decision]');
  const qualityButtons = [...shell.querySelectorAll('[data-preview-quality-action]')];
  const qualityCopy = {
    improve: 'Mejora solicitada · el dato permanece abierto hasta recibir información de mayor calidad.',
    accept: 'Aceptado con limitación · la decisión y su justificación deben permanecer visibles en el cierre.'
  };
  const applyQualityDecision = (decision) => {
    if (!qualityDecision || !qualityCopy[decision]) return;
    qualityDecision.textContent = qualityCopy[decision];
    qualityCard?.classList.toggle('quality-needs-improvement', decision === 'improve');
    qualityCard?.classList.toggle('quality-accepted-limitation', decision === 'accept');
    qualityButtons.forEach(button => {
      const selected = button.dataset.previewQualityAction === decision;
      button.setAttribute('aria-pressed', String(selected));
    });
  };
  if (qualityButtons.length) {
    let savedDecision = '';
    try { savedDecision = localStorage.getItem('cth-pages-preview-quality-decision') || ''; } catch (_) {}
    if (qualityCopy[savedDecision]) applyQualityDecision(savedDecision);
    qualityButtons.forEach(button => button.addEventListener('click', () => {
      const decision = button.dataset.previewQualityAction;
      applyQualityDecision(decision);
      try { localStorage.setItem('cth-pages-preview-quality-decision', decision); } catch (_) {}
    }));
  }

  shell.querySelectorAll('[data-preview-download]').forEach(button => {
    button.addEventListener('click', () => {
      const original = button.textContent;
      button.textContent = 'Preview listo ✓';
      setTimeout(() => { button.textContent = original; }, 1500);
    });
  });

  const traceDialog = shell.querySelector('[data-preview-trace-dialog]');
  const traceOpen = shell.querySelector('[data-preview-trace-open]');
  const traceClose = shell.querySelector('[data-preview-trace-close]');
  if (traceDialog && traceOpen) {
    traceOpen.addEventListener('click', () => {
      if (typeof traceDialog.showModal === 'function') traceDialog.showModal();
      else traceDialog.setAttribute('open', '');
    });
    traceClose?.addEventListener('click', () => traceDialog.close());
    traceDialog.addEventListener('click', event => {
      if (event.target !== traceDialog) return;
      const rect = traceDialog.getBoundingClientRect();
      const inside = event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom;
      if (!inside) traceDialog.close();
    });
  }

  let initial = 'trabajo';
  try { initial = localStorage.getItem('cth-pages-preview-view') || initial; } catch (_) {}
  if (!titles[initial]) initial = 'trabajo';
  show(initial);
})();