(() => {
  const sections = [
    "hero-trust.html",
    "value-depth.html",
    "problem-platform.html",
    "process-trace.html",
    "reports-decision.html",
    "preview-app.html",
    "reduction-solutions.html",
    "proof-scenarios.html",
    "plans-trust.html",
    "experience-resources-diagnostic.html"
  ];
  const host = document.querySelector("[data-section-host]");
  const loadScript = src => new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.defer = true;
    script.onload = resolve;
    script.onerror = reject;
    document.body.appendChild(script);
  });
  const load = async () => {
    try {
      const responses = await Promise.all(sections.map(name => fetch(`sections/${name}`)));
      if (responses.some(response => !response.ok)) throw new Error("No fue posible cargar una sección pública.");
      host.innerHTML = (await Promise.all(responses.map(response => response.text()))).join("\n");

      /* El CTA de cierre pertenece al final del recorrido, después del diagnóstico. */
      const finalCta = host.querySelector('.craft-final-cta');
      const prototypeNote = host.querySelector('.craft-prototype-note');
      if (finalCta && prototypeNote) prototypeNote.before(finalCta);

      host.setAttribute("aria-busy", "false");
      const cfg = window.CALCULA_TU_HUELLA_CONFIG || {};
      const base = String(cfg.appBaseUrl || "").replace(/\/$/, "");
      document.querySelectorAll("[data-app-link]").forEach(link => {
        if (base) {
          link.href = `${base}/login`;
          link.removeAttribute("aria-disabled");
        } else {
          link.href = "#demo-app";
          link.title = "Abrir la vista navegable de la plataforma en GitHub Pages";
        }
      });
      await loadScript("app-runtime.js");
      await loadScript("preview-app.js");
    } catch (error) {
      host.setAttribute("aria-busy", "false");
      host.innerHTML = `<section class="diagnostic-cta"><div class="container diagnostic-shell"><div class="diagnostic-copy"><h1>No pudimos cargar la experiencia pública.</h1><p>Recarga la página o consulta la aplicación desplegada.</p></div></div></section>`;
      console.error(error);
    }
  };
  load();
})();