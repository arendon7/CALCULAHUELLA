(() => {
  const form = document.querySelector('[data-diagnostic-form]');
  const yearButtons = [...document.querySelectorAll('[data-year-route]')];
  const routePrices = {
    'Huella Esencial': '$1.300.000 COP / año',
    'Gestión de Carbono': '$3.300.000 COP / año',
    'Gestión Avanzada': '$8.300.000 COP / año'
  };
  const yearProfiles = {
    'Huella Esencial': {
      focus: 'Ordenar la primera medición, instalar responsables y dejar una base de alcances 1 y 2 que pueda actualizarse.',
      depth: 'Primera huella con recopilación asistida, revisión básica y recomendaciones iniciales.',
      output: 'Mapa de fuentes, expediente base, inventario, resultados e informe ejecutivo reutilizables.',
      next: 'Primer paso: confirmar límites, sedes, fuentes directas y energía adquirida.'
    },
    'Gestión de Carbono': {
      focus: 'Priorizar continuidad anual, alcance 3 material, calidad de evidencia, análisis y un plan de reducción con seguimiento.',
      depth: 'Gestión continua del inventario y sus decisiones.',
      output: 'Fuentes, responsables, expediente, resultados, hotspots y plan de acción reutilizables.',
      next: 'Primer paso: confirmar el mapa de fuentes y priorizar las categorías materiales de alcance 3.'
    },
    'Gestión Avanzada': {
      focus: 'Profundizar cadena de valor, año base, escenarios, incertidumbre y preparación documental para exigencias externas.',
      depth: 'Mayor profundidad metodológica y documental, con trabajo ampliado sobre alcance 3 y trazabilidad.',
      output: 'Inventario profundo, expediente técnico, escenarios, controles y paquete preparado para revisión específica.',
      next: 'Primer paso: definir el requerimiento externo y la profundidad documental que debe soportarlo.'
    }
  };
  const sectorLabels = {
    servicios: 'servicios y oficinas',
    industria: 'industria o manufactura',
    agro: 'agroindustria',
    logistica: 'transporte y logística',
    residuos: 'gestión de residuos'
  };

  const setText = (selector, value) => {
    const node = document.querySelector(selector);
    if (node) node.textContent = value;
  };

  const activateYearRoute = (route, persist = true) => {
    const profile = yearProfiles[route] || yearProfiles['Gestión de Carbono'];
    const selected = yearProfiles[route] ? route : 'Gestión de Carbono';
    yearButtons.forEach(button => {
      const active = button.dataset.yearRoute === selected;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
      button.tabIndex = active ? 0 : -1;
    });
    setText('[data-year-title]', selected);
    setText('[data-year-price]', routePrices[selected]);
    setText('[data-year-focus]', profile.focus);
    setText('[data-year-depth]', profile.depth);
    setText('[data-year-output]', profile.output);
    if (persist) {
      try { localStorage.setItem('cth-pages-year-route', selected); } catch (_) {}
    }
  };

  yearButtons.forEach((button, index) => {
    button.addEventListener('click', () => activateYearRoute(button.dataset.yearRoute));
    button.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let next = index;
      if (event.key === 'ArrowRight') next = (index + 1) % yearButtons.length;
      if (event.key === 'ArrowLeft') next = (index - 1 + yearButtons.length) % yearButtons.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = yearButtons.length - 1;
      yearButtons[next].focus();
      activateYearRoute(yearButtons[next].dataset.yearRoute);
    });
  });

  const computeDiagnostic = values => {
    const sector = String(values.sector || '');
    const sedes = Math.max(1, Math.min(100, Number(values.sedes || 1)));
    const primera = String(values.primera || 'si');
    const datos = String(values.datos || 'baja');
    const objetivo = String(values.objetivo || 'medir');
    const sectorBase = { servicios: 8, industria: 18, agro: 16, logistica: 14, residuos: 15 }[sector] || 10;
    const sources = Math.min(60, sectorBase + Math.max(0, sedes - 1) * 3 + (objetivo === 'verificacion' ? 4 : 0));
    const complexityScore = sedes + ((sector === 'industria' || sector === 'agro') ? 3 : 1) + (datos === 'baja' ? 4 : datos === 'media' ? 2 : 0) + (objetivo === 'verificacion' ? 4 : objetivo === 'reducir' ? 2 : 0);
    const complexity = complexityScore >= 12 ? 'Alta' : complexityScore >= 7 ? 'Media' : 'Baja';
    const maturity = primera === 'si' ? (datos === 'alta' ? 'Inicial organizada' : 'Inicial') : (objetivo === 'reducir' ? 'En gestión' : 'Intermedia');
    const route = objetivo === 'verificacion' || complexity === 'Alta' ? 'Gestión Avanzada' : (primera === 'si' && objetivo === 'medir' ? 'Huella Esencial' : 'Gestión de Carbono');
    const areas = Math.min(12, 3 + Math.ceil(sources / 7));
    const reasons = [];

    if (sedes > 1) reasons.push(`${sedes} sedes elevan la coordinación de responsables, periodos y evidencias.`);
    else reasons.push('Una sola sede permite concentrar el arranque y reducir coordinación inicial.');

    if (datos === 'baja') reasons.push('Los datos dispersos hacen necesario instalar primero estructura, responsables y control de faltantes.');
    if (datos === 'media') reasons.push('La información existe, pero todavía requiere normalización, evidencia y control de versiones.');
    if (datos === 'alta') reasons.push('La información relativamente centralizada permite dedicar más esfuerzo a calidad, análisis y decisiones.');

    if (objetivo === 'verificacion') reasons.push('Preparar una revisión externa exige mayor profundidad documental y trazabilidad desde el inicio.');
    if (objetivo === 'reducir') reasons.push('El objetivo de reducción requiere conectar el inventario con hotspots, acciones, responsables y seguimiento.');
    if (objetivo === 'cliente') reasons.push('Responder a clientes o licitaciones requiere una salida controlada y suficientemente documentada para terceros.');
    if (objetivo === 'medir') reasons.push(primera === 'si' ? 'Al ser la primera huella, la prioridad es construir una base defendible antes de ampliar complejidad.' : 'Ya existe una medición y conviene convertirla en una estructura actualizable.');

    if (['industria', 'agro', 'logistica', 'residuos'].includes(sector)) reasons.push(`La simulación asigna mayor diversidad probable de fuentes a una operación de ${sectorLabels[sector]}.`);

    return { sector, sedes, primera, datos, objetivo, maturity, complexity, sources, areas, route, price: routePrices[route], reasons: reasons.slice(0, 4) };
  };

  const renderDiagnostic = result => {
    const profile = yearProfiles[result.route] || yearProfiles['Gestión de Carbono'];
    setText('[data-result-heading]', `Ruta sugerida: ${result.route}`);
    setText('[data-result-maturity]', result.maturity);
    setText('[data-result-complexity]', result.complexity);
    setText('[data-result-sources]', String(result.sources));
    setText('[data-result-areas]', String(result.areas));
    setText('[data-result-route]', result.route);
    setText('[data-result-price]', `Referencia estándar: ${result.price}`);
    setText('[data-result-year-focus]', profile.focus);
    setText('[data-result-next]', profile.next);
    setText('[data-result-note]', 'La ruta es orientativa. El alcance final depende de materialidad, fuentes reales, calidad de evidencia y requerimientos específicos.');
    const why = document.querySelector('[data-result-why]');
    if (why) why.innerHTML = result.reasons.map(reason => `<li>${reason}</li>`).join('');
    const card = document.querySelector('[data-diagnostic-result]');
    if (card) card.classList.add('has-result');
    activateYearRoute(result.route);
  };

  const valuesFromForm = () => {
    if (!form) return null;
    const fd = new FormData(form);
    return {
      sector: fd.get('sector'),
      sedes: fd.get('sedes'),
      primera: fd.get('primera'),
      datos: fd.get('datos'),
      objetivo: fd.get('objetivo')
    };
  };

  if (form) {
    form.addEventListener('submit', event => {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (!form.reportValidity()) return;
      const values = valuesFromForm();
      if (!values?.sector) return;
      const result = computeDiagnostic(values);
      renderDiagnostic(result);
      try { localStorage.setItem('cthDiagnostic', JSON.stringify(result)); } catch (_) {}
    }, true);

    try {
      const saved = JSON.parse(localStorage.getItem('cthDiagnostic') || 'null');
      if (saved && saved.sector) {
        const fields = ['sector', 'sedes', 'primera', 'datos', 'objetivo'];
        fields.forEach(name => {
          const field = form.elements.namedItem(name);
          if (field && saved[name] !== undefined) field.value = String(saved[name]);
        });
        renderDiagnostic(computeDiagnostic(saved));
      }
    } catch (_) {}
  }

  if (!document.querySelector('[data-year-route].active')) {
    activateYearRoute('Gestión de Carbono', false);
  } else {
    let savedRoute = '';
    try { savedRoute = localStorage.getItem('cth-pages-year-route') || ''; } catch (_) {}
    activateYearRoute(yearProfiles[savedRoute] ? savedRoute : (document.querySelector('[data-year-route].active')?.dataset.yearRoute || 'Gestión de Carbono'), false);
  }
})();