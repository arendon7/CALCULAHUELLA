/* Calcula tu Huella · Frontend Kit v1 · Control complementario del shell. */

document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');
  const menuButton = document.getElementById('menuButton');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (!sidebar || !menuButton || !backdrop) return;

  let previouslyFocused = null;
  let wasOpen = sidebar.classList.contains('open');

  const syncShellState = () => {
    const open = sidebar.classList.contains('open');
    document.body.classList.toggle('sidebar-open', open);
    backdrop.setAttribute('aria-hidden', String(!open));
    backdrop.tabIndex = open ? 0 : -1;
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Cerrar menú' : 'Abrir menú');

    if (open && !wasOpen) {
      previouslyFocused = document.activeElement;
      window.requestAnimationFrame(() => {
        const target = sidebar.querySelector('[aria-current="page"], a, button, summary');
        target?.focus({ preventScroll: true });
      });
    }

    if (!open && wasOpen && sidebar.contains(document.activeElement)) {
      const target = previouslyFocused instanceof HTMLElement ? previouslyFocused : menuButton;
      target.focus({ preventScroll: true });
    }
    wasOpen = open;
  };

  new MutationObserver(syncShellState).observe(sidebar, {
    attributes: true,
    attributeFilter: ['class'],
  });

  const desktop = window.matchMedia('(min-width: 981px)');
  const closeAtDesktop = (event) => {
    if (!event.matches) return;
    sidebar.classList.remove('open');
    syncShellState();
  };
  desktop.addEventListener?.('change', closeAtDesktop);
  syncShellState();
});
