(() => {
  'use strict';

  const setup = () => {
    const game = window.__FLY_BRAIN__;
    if (!game || !game.rendererSystem) {
      requestAnimationFrame(setup);
      return;
    }

    const apply = () => {
      const mobile = window.innerWidth < 700;
      const renderer = game.rendererSystem.renderer;
      const dprCap = mobile ? 1.35 : 1.7;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, dprCap));
      renderer.setSize(window.innerWidth, window.innerHeight, false);

      // On small screens the character is already visually separated by the
      // pastel value structure, so a dynamic shadow pass is unnecessary.
      renderer.shadowMap.enabled = !mobile;
      game.rendererSystem.sun.castShadow = !mobile;
    };

    apply();
    window.addEventListener('resize', () => requestAnimationFrame(apply), { passive: true });
  };

  setup();
})();
