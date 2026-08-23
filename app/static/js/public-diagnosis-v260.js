function initializeV260DiagnosisWizard() {
  const form = document.querySelector('[data-v260-diagnosis-wizard]');
  if (!form) return;

  const steps = Array.from(form.querySelectorAll('[data-diagnosis-step]'));
  const indicators = Array.from(form.querySelectorAll('[data-diagnosis-indicator]'));
  const counter = form.querySelector('[data-diagnosis-counter]');
  const title = form.querySelector('[data-diagnosis-title]');
  const back = form.querySelector('[data-diagnosis-back]');
  const next = form.querySelector('[data-diagnosis-next]');
  const submit = form.querySelector('[data-diagnosis-submit]');
  const titles = ['Empresa y contacto', 'Escala y operación', 'Datos y madurez', 'Objetivo y profundidad'];
  const requestedStep = Number.parseInt(form.dataset.diagnosisInitialStep || '1', 10);
  const reducedMotion = Boolean(
    window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
  let current = Math.max(0, Math.min(steps.length - 1, (Number.isFinite(requestedStep) ? requestedStep : 1) - 1));

  const focusStep = () => {
    const heading = steps[current]?.querySelector('h2');
    heading?.setAttribute('tabindex', '-1');
    heading?.focus({ preventScroll: true });
  };

  const scrollToForm = () => {
    form.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
  };

  const render = (focus = false) => {
    steps.forEach((step, index) => {
      step.hidden = index !== current;
      step.setAttribute('aria-hidden', String(index !== current));
    });
    indicators.forEach((indicator, index) => {
      indicator.classList.toggle('active', index === current);
      indicator.classList.toggle('complete', index < current);
      indicator.setAttribute('aria-current', index === current ? 'step' : 'false');
    });
    form.dataset.diagnosisProgressStep = String(current + 1);
    if (counter) counter.textContent = `Paso ${current + 1} de ${steps.length}`;
    if (title) title.textContent = titles[current] || '';
    if (back) back.hidden = current === 0;
    if (next) next.hidden = current === steps.length - 1;
    if (submit) submit.hidden = current !== steps.length - 1;
    if (focus) focusStep();
  };

  const validateCurrent = () => {
    const controls = Array.from(steps[current]?.querySelectorAll('input, select, textarea') || []);
    for (const control of controls) {
      if (!control.checkValidity()) {
        control.reportValidity();
        control.focus();
        return false;
      }
    }
    return true;
  };

  next?.addEventListener('click', () => {
    if (!validateCurrent()) return;
    current = Math.min(current + 1, steps.length - 1);
    render(true);
    scrollToForm();
  });

  back?.addEventListener('click', () => {
    current = Math.max(current - 1, 0);
    render(true);
    scrollToForm();
  });

  form.addEventListener('submit', (event) => {
    if (!validateCurrent()) event.preventDefault();
  });

  render(Boolean(form.querySelector('[role="alert"]')));
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeV260DiagnosisWizard);
} else {
  initializeV260DiagnosisWizard();
}
