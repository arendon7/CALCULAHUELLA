(() => {
  const sections = [
    "hero-trust.html",
    "value-depth.html",
    "problem-platform.html",
    "process-trace.html",
    "reports-decision.html",
    "preview-app.html",
    "reduction-solutions.html",
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
      host.setAttribute("aria-busy", "false");
      const cfg = window.CALCULA_TU_HUELLA_CONFIG || {};
      const base = String(cfg.appBaseUrl || "").replace(/\/$/, "");
      document.querySelectorAll("[data-app-link]").forEach(link => {
        if (base) { link.href = `${base}/login`; link.removeAttribute("aria-disabled"); }
        else { link.title = "La URL de la aplicación se configurará al desplegar el backend"; }
      });
      await loadScript("app-runtime.js");
      await loadScript("preview-app.js");
    } catch (error) {
      host.setAttribute("aria-busy", "false");
      host.innerHTML = `<section class="diagnostic-cta"><div class="container diagnostic-shell"><div class="diagnostic-copy"><div class="eyebrow">ERROR DE CARGA</div><h1>No pudimos cargar la experiencia pública.</h1><p>Recarga la página o consulta la aplicación desplegada.</p></div></div></section>`;
      console.error(error);
    }
  };
  load();
})();