(() => {
  const dialog = document.querySelector('[data-route-card-dialog]');
  const openButton = document.querySelector('[data-route-card-open]');
  if (!dialog || !openButton) return;

  const cfg = window.CALCULA_TU_HUELLA_CONFIG || {};
  const appBaseUrl = String(cfg.appBaseUrl || '').replace(/\/$/, '');
  const appBridge = dialog.querySelector('[data-route-app-bridge]');
  const appOffline = dialog.querySelector('[data-route-app-offline]');
  const appDiagnostic = dialog.querySelector('[data-route-app-diagnostic]');
  const contactOpen = dialog.querySelector('[data-route-contact-open]');
  const contactPrivacy = dialog.querySelector('[data-contact-privacy]');
  const status = dialog.querySelector('[data-route-card-status]');
  const printSurface = document.querySelector('[data-route-print-surface]');

  const sectorLabels = {
    servicios: 'Servicios y oficinas',
    industria: 'Industria o manufactura',
    agro: 'Agroindustria',
    logistica: 'Transporte y logística',
    residuos: 'Gestión de residuos'
  };
  const objectiveLabels = {
    medir: 'Construir la primera huella',
    cliente: 'Responder a cliente o licitación',
    reducir: 'Gestionar un plan de reducción',
    verificacion: 'Preparar revisión externa'
  };
  const allowedRoutes = new Set(['Huella Esencial', 'Gestión de Carbono', 'Gestión Avanzada']);

  let current = null;

  const readDiagnostic = () => {
    try {
      const parsed = JSON.parse(localStorage.getItem('cthDiagnostic') || 'null');
      if (!parsed || !parsed.sector || !parsed.route) return null;
      const safe = {
        sector: String(parsed.sector || ''),
        sedes: Math.max(1, Math.min(100, Number(parsed.sedes || 1))),
        primera: String(parsed.primera || ''),
        datos: String(parsed.datos || ''),
        objetivo: String(parsed.objetivo || ''),
        maturity: String(parsed.maturity || ''),
        complexity: String(parsed.complexity || ''),
        sources: Math.max(0, Number(parsed.sources || 0)),
        areas: Math.max(0, Number(parsed.areas || 0)),
        route: String(parsed.route || ''),
        price: String(parsed.price || ''),
        reasons: Array.isArray(parsed.reasons) ? parsed.reasons.slice(0, 4).map(String) : []
      };
      if (!allowedRoutes.has(safe.route) || !sectorLabels[safe.sector]) return null;
      return safe;
    } catch (_) {
      return null;
    }
  };

  const contactUrl = result => {
    if (!appBaseUrl || !result) return '';
    const url = new URL(`${appBaseUrl}/contacto`);
    url.searchParams.set('plan', result.route);
    url.searchParams.set('sector', sectorLabels[result.sector]);
    url.searchParams.set('sites', String(result.sedes));
    const objective = objectiveLabels[result.objetivo];
    if (objective) url.searchParams.set('objective', objective);
    return url.toString();
  };

  const setText = (selector, text) => {
    const node = dialog.querySelector(selector);
    if (node) node.textContent = text;
  };

  const briefText = result => {
    const reasons = result.reasons.length
      ? result.reasons.map(item => `• ${item}`).join('\n')
      : '• La recomendación es orientativa y debe validarse con el alcance real.';
    const yearFocus = document.querySelector('[data-result-year-focus]')?.textContent?.trim() || '';
    const next = document.querySelector('[data-result-next]')?.textContent?.trim() || '';
    return [
      'CALCULA TU HUELLA · FICHA DE RUTA ORIENTATIVA', '',
      `Ruta sugerida: ${result.route}`, `Precio estándar de referencia: ${result.price}`,
      `Sector: ${sectorLabels[result.sector]}`, `Sedes: ${result.sedes}`,
      `Madurez: ${result.maturity}`, `Complejidad: ${result.complexity}`,
      `Fuentes probables: ${result.sources}`, `Áreas participantes: ${result.areas}`,
      `Objetivo: ${objectiveLabels[result.objetivo] || 'Por definir'}`, '',
      'Por qué esta ruta:', reasons, '', 'Foco del primer año:', yearFocus, next, '',
      'Resultado orientativo. El alcance y precio definitivos dependen de materialidad, fuentes reales, evidencia y requerimientos específicos. No constituye certificación ni verificación independiente.', '',
      'https://arendon7.github.io/CALCULAHUELLA/'
    ].join('\n');
  };

  const renderBrief = result => {
    current = result;
    setText('[data-brief-route]', result.route);
    setText('[data-brief-price]', result.price);
    setText('[data-brief-sector]', sectorLabels[result.sector]);
    setText('[data-brief-sites]', String(result.sedes));
    setText('[data-brief-maturity]', result.maturity);
    setText('[data-brief-complexity]', result.complexity);
    setText('[data-brief-sources]', String(result.sources));
    setText('[data-brief-areas]', String(result.areas));
    setText('[data-brief-year]', document.querySelector('[data-result-year-focus]')?.textContent?.trim() || '—');
    setText('[data-brief-next]', document.querySelector('[data-result-next]')?.textContent?.trim() || '—');
    setText('[data-brief-date]', new Intl.DateTimeFormat('es-CO', { dateStyle: 'long' }).format(new Date()));
    const reasons = dialog.querySelector('[data-brief-reasons]');
    if (reasons) {
      reasons.replaceChildren(...result.reasons.map(reason => {
        const item = document.createElement('li');
        item.textContent = reason;
        return item;
      }));
    }
    if (contactOpen && appBaseUrl) contactOpen.href = contactUrl(result);
  };

  const syncAvailability = () => {
    const result = readDiagnostic();
    openButton.disabled = !result;
    openButton.setAttribute('aria-disabled', String(!result));
    if (result) renderBrief(result);
  };

  const setStatus = message => { if (status) status.textContent = message; };
  const copyText = async text => {
    if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(text);
    const area = document.createElement('textarea');
    area.value = text; area.setAttribute('readonly', ''); area.style.position = 'fixed'; area.style.opacity = '0';
    document.body.append(area); area.select(); document.execCommand('copy'); area.remove();
  };

  if (appBaseUrl) {
    if (appBridge) appBridge.hidden = false;
    if (appOffline) appOffline.hidden = true;
    if (appDiagnostic) appDiagnostic.href = `${appBaseUrl}/diagnostico`;
    if (contactPrivacy) contactPrivacy.href = `${appBaseUrl}/legal/privacidad`;
  } else {
    if (appBridge) appBridge.hidden = true;
    if (appOffline) appOffline.hidden = false;
  }

  openButton.addEventListener('click', () => {
    const result = readDiagnostic();
    if (!result) return;
    renderBrief(result); setStatus('');
    if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
  });
  dialog.querySelector('[data-route-card-close]')?.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    const inside = event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom;
    if (!inside) dialog.close();
  });
  dialog.querySelector('[data-route-copy]')?.addEventListener('click', async () => {
    if (!current) return;
    try { await copyText(briefText(current)); setStatus('Resumen copiado. No incluye datos personales.'); }
    catch (_) { setStatus('No fue posible copiar automáticamente. Usa Imprimir / guardar PDF.'); }
  });
  dialog.querySelector('[data-route-share]')?.addEventListener('click', async () => {
    if (!current) return;
    const text = briefText(current);
    try {
      if (navigator.share) {
        await navigator.share({ title: `Calcula tu Huella · ${current.route}`, text, url: 'https://arendon7.github.io/CALCULAHUELLA/#diagnostico' });
        setStatus('Ficha compartida desde el dispositivo.');
      } else { await copyText(text); setStatus('Tu navegador no ofrece compartir: copiamos la ficha al portapapeles.'); }
    } catch (error) { if (error?.name !== 'AbortError') setStatus('No se completó el envío. Puedes copiar o imprimir la ficha.'); }
  });
  dialog.querySelector('[data-route-print]')?.addEventListener('click', () => {
    if (!current || !printSurface) return;
    const sheet = dialog.querySelector('[data-route-card-sheet]'); if (!sheet) return;
    printSurface.replaceChildren(sheet.cloneNode(true)); document.body.classList.add('route-card-printing');
    printSurface.setAttribute('aria-hidden', 'false'); window.print();
  });
  window.addEventListener('afterprint', () => {
    document.body.classList.remove('route-card-printing');
    if (printSurface) { printSurface.setAttribute('aria-hidden', 'true'); printSurface.replaceChildren(); }
  });
  document.addEventListener('submit', event => {
    if (event.target?.matches?.('[data-diagnostic-form]')) setTimeout(syncAvailability, 0);
  }, true);
  syncAvailability();
})();