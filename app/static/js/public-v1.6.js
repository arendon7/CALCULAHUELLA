(() => {
  const visualTitle = document.querySelector('[data-process-visual-title]');
  const visual = document.querySelector('[data-process-visual]');
  if (!visualTitle || !visual) return;

  const processVisualsV16 = {
    diagnostico: ['Diagnóstico inicial', [['Madurez','Inicial'],['Complejidad','Media'],['Fuentes probables','14'],['Áreas participantes','5']], 'Definir alcance'],
    configuracion: ['Planificación del inventario', [['Periodo','2026'],['Sedes','2'],['Alcances','1 y 2'],['Responsables','7']], 'Aprobar plan de trabajo'],
    recopilacion: ['Datos y evidencias', [['Solicitudes abiertas','9'],['Responsables','7'],['Datos registrados','126'],['Cobertura de evidencia','64 %']], 'Completar expediente'],
    metodologia: ['Metodología documentada', [['Factores versionados','18'],['Supuestos','4'],['Exclusiones','2'],['Fuentes metodológicas','6']], 'Revisar criterios'],
    calculo: ['Trazabilidad del cálculo', [['Fuentes calculadas','14'],['Factores aprobados','18'],['Conversiones','3'],['Alertas críticas','2']], 'Revisar cálculos'],
    revision: ['Revisión profesional', [['Fuentes revisadas','12'],['Observaciones','6'],['Puertas aprobadas','4'],['Alistamiento','62 %']], 'Resolver observaciones'],
    informes: ['Informe y cierre', [['Entregables','6'],['Borradores','2'],['En revisión','1'],['Versión cerrada','1']], 'Cerrar entrega'],
    accion: ['Plan de reducción', [['Oportunidades','8'],['Priorizadas','3'],['En ejecución','1'],['Seguimiento','4']], 'Gestionar acciones']
  };

  const render = key => {
    const data = processVisualsV16[key];
    if (!data) return;
    const [title, rows, route] = data;
    visualTitle.textContent = title;
    visual.innerHTML = `<small>RESULTADO DE LA ETAPA</small><h4>${title}</h4>${rows.map(([a,b]) => `<div class="diagnostic-line"><span>${a}</span><b>${b}</b></div>`).join('')}<div class="diagnostic-route">${route} <span>→</span></div>`;
  };

  const syncFromActive = () => {
    const active = document.querySelector('[data-process].active');
    if (active) render(active.dataset.process);
  };

  document.querySelectorAll('[data-process]').forEach(step => {
    step.addEventListener('click', () => queueMicrotask(syncFromActive));
    step.addEventListener('keydown', () => queueMicrotask(syncFromActive));
  });

  syncFromActive();
})();
