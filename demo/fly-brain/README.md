# FLY BRAIN

A small 2.5D endless browser game built with HTML, CSS, JavaScript and Three.js only.

## Controls

- Mouse click
- Touch / tap
- Space

Every input performs the same flap action.

## Run

Open `index.html` directly, or serve the folder with any static HTTP server.

The packaged release includes `vendor/three.min.js`, so the game does not require a network connection. The source branch also has a CDN fallback for convenience.

## Design / engineering notes

- Orthographic side-view camera
- Primitive-only mascot model, no GLB/GLTF or image assets
- Delta-time movement with max 1/60 physics substeps
- Object-pooled obstacles and particles
- Shared obstacle geometry; no raycaster collision
- Conservative fly collision radius for fair play
- Procedural Web Audio effects after first user interaction
- Pixel ratio capped for Retina / high-DPI devices
- Responsive desktop and mobile layout
- Local high-score persistence

## Meme context

The game lightly references the September 2026 wave of experiments built around a 166,700-neuron adult male fruit-fly connectome. The science is only used as background humor; gameplay is intentionally simple.
