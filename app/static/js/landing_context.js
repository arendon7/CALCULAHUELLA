(() => {
  const STORAGE_KEY = 'cth_landing_context_v1';
  const SCHEMA = 'cth.landing_context.v1';

  const sectorOptions = [
    'Servicios y oficinas',
    'Manufactura',
    'Agroindustria',
    'Transporte y logística',
    'Gestión de residuos',
    'Construcción',
    'Salud',
    'Energía',
    'Otro',
  ];

  const objectiveOptions = [
    'Conocer la huella corporativa',
    'Requisito de clientes y estrategia de reducción',
    'Licitación o cadena de suministro',
    'Preparación para verificación',
    'Reporte regulatorio o sostenibilidad',
    'Información para dirección o financiadores',
  ];

  function optionMarkup(values, placeholder) {
    return [
      `<option value="">${placeholder}</option>`,
      ...values.map((value) => `<option value="${value}">${value}</option>`),
    ].join('');
  }

  function buildSection() {
    const anchor = document.querySelector('.public-audience-strip');
    const hero = document.querySelector('.public-hero');
    if (!anchor || !hero || document.querySelector('[data-landing-context-form]')) return null;

    const section = document.createElement('section');
    section.className = 'public-section landing-context-section';
    section.id = 'preconfiguracion';
    section.innerHTML = `
      <div class="public-section-head">
        <span>PRECONFIGURACIÓN · 2 DECISIONES</span>
        <h2>Empieza con lo que realmente cambia la ruta</h2>
        <p>Selecciona sector y objetivo. El diagnóstico oficial completará empresa, operación, datos, soportes, alcance y nivel de revisión.</p>
      </div>
      <form class="landing-context-form" data-landing-context-form>
        <label>
          <span>1 · Sector</span>
          <select name="landing_sector" required aria-label="Sector de la organización">
            ${optionMarkup(sectorOptions, 'Selecciona un sector')}
          </select>
        </label>
        <label>
          <span>2 · Objetivo principal</span>
          <select name="landing_objective" required aria-label="Objetivo principal de la medición">
            ${optionMarkup(objectiveOptions, 'Selecciona un objetivo')}
          </select>
        </label>
        <div class="landing-context-action">
          <button class="button primary large" type="submit">Continuar al diagnóstico →</button>
          <small>Solo reutilizamos estas dos respuestas. No enviamos datos personales por URL.</small>
        </div>
        <p class="landing-context-status" data-landing-context-status role="status" aria-live="polite"></p>
      </form>
      <div class="landing-context-boundary" aria-label="Qué se define ahora y qué se completa después">
        <div><strong>Ahora</strong><span>Sector · objetivo</span></div>
        <i>→</i>
        <div><strong>Diagnóstico</strong><span>Empresa · operación · datos · alcance · revisión</span></div>
        <i>→</i>
        <div><strong>Puesta en marcha</strong><span>Configuración confirmada antes de aplicarse al inventario</span></div>
      </div>`;

    anchor.insertAdjacentElement('afterend', section);

    const primaryHeroCta = hero.querySelector('.public-cta-row .button.primary[href="/diagnostico"]');
    if (primaryHeroCta) {
      primaryHeroCta.href = '#preconfiguracion';
      primaryHeroCta.textContent = 'Preconfigurar diagnóstico';
    }
    return section;
  }

  function initializeLandingContext() {
    const section = buildSection();
    if (!section) return;
    const form = section.querySelector('[data-landing-context-form]');
    const status = section.querySelector('[data-landing-context-status]');

    form?.addEventListener('submit', (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;

      const sector = form.elements.landing_sector.value;
      const objective = form.elements.landing_objective.value;
      const context = {
        schema: SCHEMA,
        version: '1.0',
        source: 'public_home_v1.4.10',
        created_at: new Date().toISOString(),
        reusable: { sector, objective },
        destination: '/diagnostico',
      };

      let saved = false;
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(context));
        saved = true;
      } catch (_error) {
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeLandingContext, { once: true });
  } else {
    initializeLandingContext();
  }
})();
