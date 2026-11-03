# Thorns - thorn web and barbed bursts

Chain: ink_layer -> **thorns** -> nin_stage (nin_stage/src points here). Settings: /project1/thorns, page Thorns.

- **Thorn web** (Web 0.7, Webcell 70 px, Barbs, Depth, Inkthreshold): sharp strands with small barbs strung between
  the dense spots of the Ambient Ink, some sharp, some soft as if out of focus. Strongest in the inverted (white)
  picture, where they read as black barbed drawing; in the dark picture they are faint pale strands.
  No ink = no web.
- **Barbed bursts** (Bursts 0.9, Burstsize 60 px): on hits (nin_stage/echo), five spiky star-shaped thorn marks shoot
  out where the ink is, smeared along the drift of the echoes, gone within half a second.

Build: exec(open(project.folder + '/Thorns/build_thorns.py').read()) - run it again after rebuilding nin_stage
(its build points nin_stage/src back at ink_layer/OUT). Files: build_thorns.py, thorns.glsl, thorns.tox.
