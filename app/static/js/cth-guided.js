/* Calcula tu Huella · Frontend Kit v1 · Experiencias guiadas. */

document.addEventListener('DOMContentLoaded', () => {
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
});
