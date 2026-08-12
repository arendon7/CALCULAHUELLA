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

  const navs = [...shell.querySelectorAll('[data-preview-view]')];
  const panels = [...shell.querySelectorAll('[data-preview-panel]')];
  const kicker = shell.querySelector('[data-preview-kicker]');
  const title = shell.querySelector('[data-preview-title]');
  const subtitle = shell.querySelector('[data-preview-subtitle]');
  const roleLabel = shell.querySelector('[data-preview-role]');
  const roleSelect = shell.querySelector('[data-preview-role-select]');

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

  navs.forEach(button => button.addEventListener('click', () => show(button.dataset.previewView)));

  if (roleSelect) {
    try {
      const savedRole = localStorage.getItem('cth-pages-preview-role');
      if (savedRole && [...roleSelect.options].some(option => option.value === savedRole)) roleSelect.value = savedRole;
    } catch (_) {}
    roleLabel.textContent = roleSelect.value;
    roleSelect.addEventListener('change', () => {
      roleLabel.textContent = roleSelect.value;
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

  shell.querySelectorAll('[data-preview-download]').forEach(button => {
    button.addEventListener('click', () => {
      const original = button.textContent;
      button.textContent = 'Preview listo ✓';
      setTimeout(() => { button.textContent = original; }, 1500);
    });
  });

  let initial = 'trabajo';
  try { initial = localStorage.getItem('cth-pages-preview-view') || initial; } catch (_) {}
  if (!titles[initial]) initial = 'trabajo';
  show(initial);
})();
