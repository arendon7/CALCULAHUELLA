(() => {
  const LANDING_CONTEXT_KEY = 'cth_landing_context_v1';
  const LANDING_CONTEXT_SCHEMA = 'cth.landing_context.v1';

  const menuButton = document.querySelector('[data-menu-button]');
  const mobilePanel = document.querySelector('[data-mobile-panel]');

  const closeMenu = () => {
    if (!menuButton || !mobilePanel) return;
    mobilePanel.classList.remove('open');
    menuButton.setAttribute('aria-expanded', 'false');
  };

  if (menuButton && mobilePanel) {
    menuButton.addEventListener('click', () => {
      const open = mobilePanel.classList.toggle('open');
      menuButton.setAttribute('aria-expanded', String(open));
    });
    mobilePanel.querySelectorAll('a').forEach(a => a.addEventListener('click', closeMenu));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        closeMenu();
        menuButton.focus();
      }
    });
  }

  const tabs = [...document.querySelectorAll('[data-tab]')];
  const panels = [...document.querySelectorAll('[data-panel]')];

  const activateTab = tab => {
    const target = tab.dataset.tab;
    tabs.forEach(t => {
      const active = t === tab;
      t.classList.toggle('active', active);
      t.setAttribute('aria-selected', String(active));
      t.tabIndex = active ? 0 : -1;
    });
    panels.forEach(p => {
      const active = p.dataset.panel === target;
      p.classList.toggle('active', active);
      p.hidden = !active;
    });
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activateTab(tab));
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let next = index;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      tabs[next].focus();
      activateTab(tabs[next]);
    });
  });
  if (tabs[0]) activateTab(tabs.find(t => t.classList.contains('active')) || tabs[0]);

  document.querySelectorAll('a[href^="#"]').forEach(link => link.addEventListener('click', event => {
    const id = link.getAttribute('href');
    if (id === '#') return;
    const target = document.querySelector(id);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({
      behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      block: 'start'
    });
    history.replaceState(null, '', id);
  }));

  const processSteps = [...document.querySelectorAll('[data-process]')];
  const processPanels = [...document.querySelectorAll('[data-process-panel]')];
  const visualTitle = document.querySelector('[data-process-visual-title]');
  const visual = document.querySelector('[data-process-visual]');
  const processVisuals = {
    diagnostico: ['Diagnóstico inicial', [['Madurez','Inicial'],['Complejidad','Media'],['Fuentes probables','14'],['Áreas participantes','5']], 'Definir alcance'],
    configuracion: ['Planificación del inventario', [['Periodo','2026'],['Sedes','2'],['Alcances','1 y 2'],['Responsables','7']], 'Aprobar plan de trabajo'],
    recopilacion: ['Datos y evidencias', [['Solicitudes abiertas','9'],['Responsables','7'],['Datos registrados','126'],['Cobertura de evidencia','64 %']], 'Completar expediente'],
    metodologia: ['Metodología documentada', [['Factores versionados','18'],['Supuestos','4'],['Exclusiones','2'],['Fuentes metodológicas','6']], 'Revisar criterios'],
    calculo: ['Trazabilidad del cálculo', [['Fuentes calculadas','14'],['Factores aprobados','18'],['Conversiones','3'],['Alertas críticas','2']], 'Revisar cálculos'],
    revision: ['Revisión profesional', [['Fuentes revisadas','12'],['Observaciones','6'],['Puertas aprobadas','4'],['Alistamiento','62 %']], 'Resolver observaciones'],
    informes: ['Informe y cierre', [['Entregables','6'],['Borradores','2'],['En revisión','1'],['Versión cerrada','1']], 'Cerrar entrega'],
    accion: ['Plan de reducción', [['Oportunidades','8'],['Priorizadas','3'],['En ejecución','1'],['Seguimiento','4']], 'Gestionar acciones']
  };

  const renderProcessVisual = key => {
    if (!visual || !visualTitle || !processVisuals[key]) return;
    const [title, rows, route] = processVisuals[key];
    visualTitle.textContent = title;
    visual.innerHTML = `<small>RESULTADO DE LA ETAPA</small><h4>${title}</h4>${rows.map(([a,b]) => `<div class="diagnostic-line"><span>${a}</span><b>${b}</b></div>`).join('')}<div class="diagnostic-route">${route} <span>→</span></div>`;
  };

  const activateProcess = step => {
    const key = step.dataset.process;
    processSteps.forEach(s => {
      const active = s === step;
      s.classList.toggle('active', active);
      s.setAttribute('aria-selected', String(active));
      s.tabIndex = active ? 0 : -1;
    });
    processPanels.forEach(p => {
      const active = p.dataset.processPanel === key;
      p.classList.toggle('active', active);
      p.hidden = !active;
    });
    renderProcessVisual(key);
  };

  processSteps.forEach((step, index) => {
    step.addEventListener('click', () => activateProcess(step));
    step.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let next = index;
      if (event.key === 'ArrowRight') next = (index + 1) % processSteps.length;
      if (event.key === 'ArrowLeft') next = (index - 1 + processSteps.length) % processSteps.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = processSteps.length - 1;
      processSteps[next].focus();
      activateProcess(processSteps[next]);
    });
  });
  if (processSteps[0]) activateProcess(processSteps.find(step => step.classList.contains('active')) || processSteps[0]);

  const traceContent = {
    dato:['DATO DE ACTIVIDAD','12.450 kWh','Consumo registrado para la sede Yarumal durante enero de 2026.','Registrado · pendiente de revisión'],
    evidencia:['EVIDENCIA','Factura de energía · enero 2026','Documento relacionado directamente con el consumo registrado.','Aceptada internamente'],
    unidad:['UNIDAD Y CONVERSIÓN','kWh · unidad compatible','El dato conserva su unidad original y no requiere conversión para el factor seleccionado.','Compatibilidad confirmada'],
    factor:['FACTOR DE EMISIÓN','Versión documentada y aprobada','El factor registra fuente, año, región, unidad, gases, vigencia y responsable de aprobación.','Aprobado para esta fuente'],
    formula:['FÓRMULA','Dato de actividad × factor','La operación conserva valores originales, reglas de conversión y precisión aplicada.','Cálculo reproducible'],
    resultado:['RESULTADO','Emisiones expresadas en tCO₂e','La cifra muestra periodo, alcance, estado, advertencias y fecha de actualización.','Resultado preliminar'],
    revision:['CALIDAD Y REVISIÓN','Decisión profesional registrada','Completitud, evidencia, representatividad, estimaciones y observaciones se evalúan antes del cierre.','Aprobación interna pendiente']
  };
  const traceNodes = [...document.querySelectorAll('[data-trace]')];
  traceNodes.forEach(node => node.addEventListener('click', () => {
    const value = traceContent[node.dataset.trace];
    if (!value) return;
    traceNodes.forEach(n => n.classList.toggle('active', n === node));
    const [kicker, title, text, state] = value;
    const kickerTarget = document.querySelector('[data-trace-kicker]');
    const titleTarget = document.querySelector('[data-trace-title]');
    const textTarget = document.querySelector('[data-trace-text]');
    const stateTarget = document.querySelector('[data-trace-state]');
    if (kickerTarget) kickerTarget.textContent = kicker;
    if (titleTarget) titleTarget.textContent = title;
    if (textTarget) textTarget.textContent = text;
    if (stateTarget) stateTarget.textContent = state;
  }));

  const landingContextForm = document.querySelector('[data-landing-context-form]');
  if (landingContextForm) {
    landingContextForm.addEventListener('submit', event => {
      event.preventDefault();
      if (!landingContextForm.reportValidity()) return;

      const sector = landingContextForm.elements.landing_sector?.value || '';
      const objective = landingContextForm.elements.landing_objective?.value || '';
      const status = landingContextForm.querySelector('[data-landing-context-status]');
      if (!sector || !objective) return;

      const context = {
        schema: LANDING_CONTEXT_SCHEMA,
        version: '1.0',
        source: 'public_home_v1.6',
        created_at: new Date().toISOString(),
        reusable: { sector, objective },
        destination: '/diagnostico'
      };

      let saved = false;
      try {
        window.localStorage.setItem(LANDING_CONTEXT_KEY, JSON.stringify(context));
        saved = true;
      } catch (_) {
        saved = false;
      }
      if (status) {
        status.textContent = saved
          ? 'Contexto preparado. Continuamos al diagnóstico.'
          : 'Continuamos al diagnóstico sin reutilizar respuestas.';
      }
      window.location.assign('/diagnostico');
    });
  }

  const resources = {
    alcances:['ALCANCES 1, 2 Y 3','Cómo organizar las fuentes','Alcance 1 reúne emisiones directas; alcance 2, las asociadas con energía adquirida; alcance 3, otras emisiones indirectas de la cadena de valor. La priorización depende de la operación, materialidad y objetivos.'],
    evidencias:['DATOS Y EVIDENCIAS','Qué respalda un inventario','Facturas, certificados, registros de medidor, reportes operativos y otros documentos pueden respaldar datos. Cada evidencia debe vincularse con la fuente, el periodo y el responsable correspondiente.'],
    verificacion:['REVISIÓN Y VERIFICACIÓN','No son el mismo proceso','La revisión interna evalúa coherencia y suficiencia dentro del servicio. La verificación independiente corresponde a un tercero competente y a un alcance específico.']
  };
  const resourcePanel = document.querySelector('[data-resource-panel]');
  document.querySelectorAll('[data-resource]').forEach(btn => btn.addEventListener('click', () => {
    const value = resources[btn.dataset.resource];
    if (!value || !resourcePanel) return;
    resourcePanel.hidden = false;
    const kicker = resourcePanel.querySelector('[data-resource-kicker]');
    const title = resourcePanel.querySelector('[data-resource-title]');
    const text = resourcePanel.querySelector('[data-resource-text]');
    if (kicker) kicker.textContent = value[0];
    if (title) title.textContent = value[1];
    if (text) text.textContent = value[2];
    resourcePanel.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block:'nearest'});
  }));
  const resourceClose = document.querySelector('.resource-close');
  if (resourceClose && resourcePanel) resourceClose.addEventListener('click', () => { resourcePanel.hidden = true; });
})();
