# Screen 2 - the live silhouette on a second screen

/project1/screen2 renders the camera silhouette on its own (1280 x 720, landscape): you as a dark figure against one
soft light far behind drifting haze; the haze flows round the body, faint echoes trail the movement, the outline
catches the light. The pads (Stems) thicken the haze, the music's level breathes the light. Grey only, no flashes.

- **NIN style traces:** where the figure moved, its traces break up into analog noise (grain and line noise) and
  dissolve (Noise); older copies of the figure drift behind it (Ghosts, Ghostdelay); while it moves its rows tear
  sideways like a bad signal (Tear); faint scanlines over the screen (Scanlines).
- **Time slicing** (Timeslice): each row of the figure comes from a slightly different moment (the lower rows newer),
  some bands lag further - movement smears the body through time. The last 48 frames are kept in /screen2/history.
- **Buffer stutter** (Stutter = chance per strong hit, Stutterlength): the figure loops the 3-8 frames before the hit
  for a moment, like a stuck video buffer.
- **Scan-line displacement** (Lines, Lineheight, Linespacing): the figure drawn as horizontal lines lifted by the
  camera picture, like an analog video synthesizer.
- **Analog TV** (Chaos, Ambient): a tracking band of noise rolls down through the picture, the sync wobbles, the
  vertical hold slips now and then, faint snow over everything, thin dropouts streak across. Ambient = how much runs
  all the time, even when nothing moves; the rest comes with movement and strong hits.
- **Interlace** (odd / even lines pull apart while it moves) and **Snow** (where it moved, more on strong hits).
- **Tracking overlay** (Track 1.0, Trackcell 46 px): points lock onto the body's outline a few times a second -
  small boxes, rows of tiny data bars like coordinates, columns of data, hairlines joining neighbouring points.
  More of it when the figure moves and on hits.
- **Detail:** faint features inside the figure (eyes, folds, hands) - the camera's relief catches a little of the light.
- **Open Window** (page Screen 2) opens / closes it. With a second monitor or projector connected it fills Monitor 1
  (borderless); with only one monitor it opens as a 960 x 540 window right next to the main viewer.
- **Figure In Main Scene** off (default) = the figure is only on screen 2; on = on both screens.
- Figure, Echoes, Rim, Flow, Haze, Light, Lightsize, Lightx / Lighty, Scale, X / Y, Mirror, Resolution.
- The camera and the cut-out (Camera, Mode, Capture Empty Stage, Threshold, Softness, Trailtime) stay on the
  Silhouette page of /project1/scenes. Press Capture Empty Stage with nobody in view before the show.

Build: exec(open(project.folder + '/Screen2/build_screen2.py').read()) - files: build_screen2.py, screen2.glsl,
ghost_pack.glsl, screen2.tox. Earlier versions: screen2_v1 (plain), screen2_v2 (before Chaos / Snow), screen2_v3 (tracking band, sync wobble, dropouts), screen2_v4 (before Ambient).
