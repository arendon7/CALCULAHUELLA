(() => {
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
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
      if (event.key === 'Escape' && mobilePanel.classList.contains('open')) {
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
    target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
    history.replaceState(null, '', id);
  }));

  const processSteps = [...document.querySelectorAll('[data-process]')];
  const processPanels = [...document.querySelectorAll('[data-process-panel]')];
  const visualTitle = document.querySelector('[data-process-visual-title]');
  const visual = document.querySelector('[data-process-visual]');
  const processVisuals = {
    diagnostico: ['Diagnóstico inicial', [['Madurez','Inicial'],['Complejidad','Media'],['Fuentes probables','14'],['Áreas participantes','5']], 'Huella Esencial'],
    configuracion: ['Configuración del inventario', [['Periodo','2026'],['Sedes','2'],['Alcances','1 y 2'],['Fuentes identificadas','24']], 'Plan de trabajo'],
    recopilacion: ['Centro de solicitudes', [['Solicitudes abiertas','9'],['Responsables','7'],['Datos registrados','126'],['Cobertura de evidencia','64 %']], 'Completar información'],
    calculo: ['Trazabilidad del cálculo', [['Fuentes calculadas','14'],['Factores aprobados','18'],['Conversiones','3'],['Alertas críticas','2']], 'Revisar cálculos'],
    revision: ['Revisión profesional', [['Fuentes revisadas','12'],['Observaciones','6'],['Puertas aprobadas','4'],['Alistamiento','62 %']], 'Resolver observaciones'],
    informes: ['Centro de informes', [['Entregables','6'],['Borradores','2'],['En revisión','1'],['Aprobados','1']], 'Preparar publicación'],
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
    processSteps.forEach(s => { const active=s===step; s.classList.toggle('active',active); s.setAttribute('aria-selected',String(active)); s.tabIndex=active?0:-1; });
    processPanels.forEach(p => { const active=p.dataset.processPanel===key; p.classList.toggle('active',active); p.hidden=!active; });
    renderProcessVisual(key);
  };
  processSteps.forEach((step,index) => {
    step.addEventListener('click',()=>activateProcess(step));
    step.addEventListener('keydown',event=>{
      if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
      event.preventDefault(); let next=index;
      if(event.key==='ArrowRight') next=(index+1)%processSteps.length;
      if(event.key==='ArrowLeft') next=(index-1+processSteps.length)%processSteps.length;
      if(event.key==='Home') next=0;
      if(event.key==='End') next=processSteps.length-1;
      processSteps[next].focus(); activateProcess(processSteps[next]);
    });
  });
  if(processSteps[0]) activateProcess(processSteps[0]);

  const traceContent = {
    dato:['DATO DE ACTIVIDAD','12.450 kWh','Consumo registrado para la sede Yarumal durante enero de 2026.','Registrado · pendiente de revisión'],
    evidencia:['EVIDENCIA','Factura de energía · enero 2026','Documento relacionado directamente con el consumo registrado.','Aceptada internamente'],
    unidad:['UNIDAD Y CONVERSIÓN','kWh · unidad compatible','El dato conserva su unidad original y no requiere conversión para el factor seleccionado.','Compatibilidad confirmada'],
    factor:['FACTOR DE EMISIÓN','Versión documentada y aprobada','El factor registra fuente, año, región, unidad, gases, vigencia y responsable de aprobación.','Aprobado para esta fuente'],
    formula:['FÓRMULA','Dato de actividad × factor','La operación conserva valores originales, reglas de conversión y precisión aplicada.','Cálculo reproducible'],
    resultado:['RESULTADO','Emisiones expresadas en tCO₂e','La cifra muestra periodo, alcance, estado, advertencias y fecha de actualización.','Resultado preliminar'],
    revision:['CALIDAD Y REVISIÓN','Decisión profesional registrada','Completitud, evidencia, representatividad, estimaciones y observaciones se evalúan antes del cierre.','Aprobación interna pendiente']
  };
  const traceNodes=[...document.querySelectorAll('[data-trace]')];
  traceNodes.forEach(node=>node.addEventListener('click',()=>{
    const value=traceContent[node.dataset.trace]; if(!value) return;
    traceNodes.forEach(n=>n.classList.toggle('active',n===node));
    const [k,t,x,s]=value;
    document.querySelector('[data-trace-kicker]').textContent=k;
    document.querySelector('[data-trace-title]').textContent=t;
    document.querySelector('[data-trace-text]').textContent=x;
    document.querySelector('[data-trace-state]').textContent=s;
  }));

  const diagnosticForm = document.querySelector('[data-diagnostic-form]');
  const routePrices = {
    'Huella Esencial': '$1.300.000 COP / año',
    'Gestión de Carbono': '$3.300.000 COP / año',
    'Gestión Avanzada': '$8.300.000 COP / año'
  };
  if (diagnosticForm) {
    diagnosticForm.addEventListener('submit', event => {
      event.preventDefault();
      const fd = new FormData(diagnosticForm);
      const sector = fd.get('sector');
      const sedes = Math.max(1, Number(fd.get('sedes') || 1));
      const primera = fd.get('primera');
      const datos = fd.get('datos');
      const objetivo = fd.get('objetivo');
      if (!sector) return;
      const sectorBase = {servicios:8, industria:18, agro:16, logistica:14, residuos:15}[sector] || 10;
      const sources = Math.min(60, sectorBase + Math.max(0, sedes-1)*3 + (objetivo==='verificacion'?4:0));
      const complexityScore = sedes + (sector==='industria'||sector==='agro'?3:1) + (datos==='baja'?4:datos==='media'?2:0) + (objetivo==='verificacion'?4:objetivo==='reducir'?2:0);
      const complexity = complexityScore >= 12 ? 'Alta' : complexityScore >= 7 ? 'Media' : 'Baja';
      const maturity = primera==='si' ? (datos==='alta'?'Inicial organizada':'Inicial') : (objetivo==='reducir'?'En gestión':'Intermedia');
      const route = objetivo==='verificacion' || complexity==='Alta' ? 'Gestión Avanzada' : (primera==='si' && objetivo==='medir' ? 'Huella Esencial' : 'Gestión de Carbono');
      const areas = Math.min(12, 3 + Math.ceil(sources/7));
      document.querySelector('[data-result-maturity]').textContent=maturity;
      document.querySelector('[data-result-complexity]').textContent=complexity;
      document.querySelector('[data-result-sources]').textContent=String(sources);
      document.querySelector('[data-result-areas]').textContent=String(areas);
      document.querySelector('[data-result-route]').textContent=route;
      const priceNode = document.querySelector('[data-result-price]');
      if (priceNode) priceNode.textContent=`Referencia estándar: ${routePrices[route]}`;
      document.querySelector('[data-result-note]').textContent=`Esta ruta es orientativa. El precio final depende de sedes, fuentes, calidad de información, alcance 3 y requerimientos documentales.`;
      const result = document.querySelector('[data-diagnostic-result]');
      if (result) {
        result.classList.add('has-result');
        if (!reducedMotion) result.animate([
          { opacity:.72, transform:'translateY(8px)' },
          { opacity:1, transform:'translateY(0)' }
        ], { duration:220, easing:'cubic-bezier(0.23, 1, 0.32, 1)' });
      }
      try { localStorage.setItem('cthDiagnostic', JSON.stringify({sector,sedes,primera,datos,objetivo,maturity,complexity,sources,areas,route,price:routePrices[route]})); } catch (_) {}
    });
  }

  const resources = {
    alcances:['ALCANCES 1, 2 Y 3','Cómo organizar las fuentes','Alcance 1 reúne emisiones directas; alcance 2, las asociadas con energía adquirida; alcance 3, otras emisiones indirectas de la cadena de valor. La priorización depende de la operación, materialidad y objetivos.'],
    evidencias:['DATOS Y EVIDENCIAS','Qué respalda un inventario','Facturas, certificados, registros de medidor, reportes operativos y otros documentos pueden respaldar datos. Cada evidencia debe vincularse con la fuente, el periodo y el responsable correspondiente.'],
    verificacion:['REVISIÓN Y VERIFICACIÓN','No son el mismo proceso','La revisión interna evalúa coherencia y suficiencia dentro del servicio. La verificación independiente corresponde a un tercero competente y a un alcance específico.']
  };
  const resourcePanel=document.querySelector('[data-resource-panel]');
  document.querySelectorAll('[data-resource]').forEach(btn=>btn.addEventListener('click',()=>{
    const v=resources[btn.dataset.resource]; if(!v||!resourcePanel) return;
    resourcePanel.hidden=false;
    resourcePanel.querySelector('[data-resource-kicker]').textContent=v[0];
    resourcePanel.querySelector('[data-resource-title]').textContent=v[1];
    resourcePanel.querySelector('[data-resource-text]').textContent=v[2];
    if (!reducedMotion) resourcePanel.animate([
      { opacity:0, transform:'translateY(8px)' },
      { opacity:1, transform:'translateY(0)' }
    ], { duration:180, easing:'cubic-bezier(0.23, 1, 0.32, 1)' });
    resourcePanel.scrollIntoView({behavior:reducedMotion?'auto':'smooth',block:'nearest'});
  }));
  const resourceClose=document.querySelector('.resource-close');
  if(resourceClose) resourceClose.addEventListener('click',()=>{resourcePanel.hidden=true;});

  /* Emil-style authored motion: one hero moment, plus direct press feedback in CSS. */
  const craftStage = document.querySelector('[data-craft-stage]');
  if (craftStage && !reducedMotion) {
    requestAnimationFrame(() => craftStage.classList.add('is-ready'));
    const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
    if (finePointer) {
      let tx = 0, ty = 0, cx = 0, cy = 0, raf = 0;
      const tick = () => {
        cx += (tx - cx) * .09;
        cy += (ty - cy) * .09;
        craftStage.style.setProperty('--stage-x', `${cx.toFixed(2)}deg`);
        craftStage.style.setProperty('--stage-y', `${cy.toFixed(2)}deg`);
        if (Math.abs(tx-cx) > .01 || Math.abs(ty-cy) > .01) raf = requestAnimationFrame(tick); else raf = 0;
      };
      craftStage.addEventListener('pointermove', event => {
        const r = craftStage.getBoundingClientRect();
        tx = ((event.clientY-r.top)/r.height - .5) * -1.2;
        ty = ((event.clientX-r.left)/r.width - .5) * 1.4;
        if (!raf) raf = requestAnimationFrame(tick);
      });
      craftStage.addEventListener('pointerleave', () => { tx = 0; ty = 0; if (!raf) raf = requestAnimationFrame(tick); });
    }
  } else if (craftStage) {
    craftStage.classList.add('is-ready');
  }
})();