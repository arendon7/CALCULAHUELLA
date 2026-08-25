(() => {
  const shell = document.querySelector('[data-preview-shell]');
  if (!shell || shell.querySelector('[data-preview-view="cierre"]')) return;
  const sidebar = shell.querySelector('.preview-sidebar');
  const main = shell.querySelector('.preview-main');
  if (!sidebar || !main) return;

  sidebar.insertAdjacentHTML('beforeend', `
    <button class="preview-nav" data-preview-view="cierre"><span class="preview-nav-mark" aria-hidden="true"></span>Cierre</button>
  `);

  main.insertAdjacentHTML('beforeend', `
    <section class="preview-view" data-preview-panel="cierre" hidden>
      <div class="preview-close-summary">
        <article><span>Periodo</span><strong>2026</strong><small>Inventario corporativo</small></article>
        <article><span>Estado</span><strong>NO LISTO</strong><small>Hay condiciones pendientes</small></article>
        <article><span>Próximo periodo</span><strong>2027</strong><small>Estructura reutilizable</small></article>
      </div>
      <div class="preview-close-layout">
        <div class="preview-close-gates" aria-label="Condiciones de cierre demostrativas">
          <article><span>01</span><div><strong>Completitud crítica</strong><small>4 solicitudes todavía afectan el inventario.</small></div><em>PENDIENTE</em></article>
          <article><span>02</span><div><strong>Calidad y observaciones</strong><small>3 observaciones requieren resolución o aceptación documentada.</small></div><em>PENDIENTE</em></article>
          <article><span>03</span><div><strong>Snapshot metodológico</strong><small>Versión y factores del periodo registrados.</small></div><em class="ok">LISTO</em></article>
          <article><span>04</span><div><strong>Segregación y aprobación</strong><small>Revisor asignado; aprobación final todavía no emitida.</small></div><em>PENDIENTE</em></article>
          <article><span>05</span><div><strong>Entregables controlados</strong><small>Borradores disponibles; publicación final bloqueada hasta aprobar.</small></div><em>PENDIENTE</em></article>
        </div>
        <article class="preview-card preview-close-rule">
          <small>REGLA DE CIERRE</small>
          <h4>El periodo no se bloquea mientras exista una condición crítica pendiente.</h4>
          <p>Cuando el cierre procede, la aplicación conserva snapshot, aprobaciones, entregables y trazabilidad; las fuentes y responsables pueden reutilizarse en el siguiente periodo sin copiar una cifra anterior como si fuera nueva.</p>
          <div class="preview-close-continuity"><span>2026 · cerrar</span><i aria-hidden="true">→</i><strong>2027 · reutilizar estructura</strong></div>
          <button type="button" disabled aria-disabled="true">Cerrar periodo · bloqueado</button>
        </article>
      </div>
    </section>
  `);
})();