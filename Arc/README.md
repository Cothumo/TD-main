# Arc - the song's shape drives the scene

/project1/arc listens to the real audio (neith_live/audio_in, the Voicemeeter B1 feed) and neith's kick / hat /
snare detector, and follows the shape of the music. Page Arc shows what it hears in **State**:
calm / build / peak / breakdown / drop.

| state | detected from | what the scene does |
|---|---|---|
| build (tension) | the level rises over seconds, hats / snares get busier | the camera slowly pushes in, darkness closes in from the edges, scrim layers and echoes multiply, melt trails stretch |
| breakdown | clearly quieter than usual and no kick for 3 s | the scene holds back: the camera opens a little, darkness lifts, less ink, fewer echoes, longer trails |
| drop | after a build or breakdown the kick comes back hard and the level jumps | tension lets go with a spring (the camera springs back), echoes and ink burst, the act moves on (Auto acts), the black hole may appear (half the drops), screen 2 stutters. No flashes. |
| peak / calm | the level against the music's own recent range | the ink follows the energy |

Plus a camera that keeps drifting (up to ~5% of the frame), tilting (up to ~3 degrees) and breathing in zoom over the whole set (Drift). The zoom is computed every frame from the current tilt and drift so the edges of the picture never show (more tilt = a little more zoom).

Settings: Enable, Amount, Sensitivity (higher = builds / breakdowns / drops detected more easily), Buildtime (s to full
tension), Dropcooldown (s between drops), Buildzoom, Drift, Drop Changes Act, Drop Summons Sphere.
Outputs (/project1/arc/out): energy, tension, breakdown, drop, pulse, zoom, slope and the multipliers emul, smul,
dmul, madd, imul (they multiply on top of the acts, Stems and Grid).

Chain: ... sphere -> arc/camera -> arc/OUT -> viewer and Spout 'TDA Main' (obs_out/main_src).
Build: exec(open(project.folder + '/Arc/build_arc.py').read()) - run it again after rebuilding nin_stage, the ink or
the sphere. The energy range adapts over the first minute of music.
