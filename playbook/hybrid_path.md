# Hybrid Path

Optional. Never the silent default.

1. User sets `qualityMode=hybrid` and supplies a GLB (or local generator output).  
2. Blueprint sets `bodySource: "hybrid-glb"`.  
3. Import mesh into Three.js, normalize bbox, then apply gpthreejs materials, handles, and critique loop.  
4. Label all outputs as hybrid.  

Procedural code remains preferred for editability and game hierarchy.
