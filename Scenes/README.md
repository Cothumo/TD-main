# Scenes - NIN live performance elements

Chain: ink_layer -> nin_stage -> **scenes** -> sphere -> viewer. Settings: /project1/scenes (pages Scenes, Silhouette).

The acts of nin_stage now have four acts (auto rotation 1 > 2 > 3 > 4, Go to Act 1-4, Ableton scene n = act n):
1 Static, 2 Melt, 3 Scrim, **4 Backlit haze**. The acts fade Backlight in and out.

- **Backlit haze** (Backlight; after Cold and Black and Infinite): one soft light far behind drifting haze (Lightx,
  Lighty, Lightsize); everything in the scene becomes a dark form against it. Hazedensity, thickened by the pads
  (Stems, track 2). No rays, no strobes.
- **Live camera silhouette** (every act; Silhouette 0.7): the performer as a dark figure in the scene, the picture
  flowing round the body (Silflow), faint echoes trailing the movement (Siltrail, Trailtime); against the backlight its
  outline catches a little light.
  - Camera: Camera menu (Integrated Camera, OBS Virtual Camera, GoPro Webcam), Camera On.
  - Mode **AI person detection** (default): the NVIDIA Background TOP (/scenes/nv) recognises the person in the camera
    picture - no empty stage needed, the room is ignored. Needs an NVIDIA RTX card (20-50 series) and NVIDIA's
    Video Effects SDK (https://www.nvidia.com/en-us/geforce/broadcasting/broadcast-sdk/resources/), then restart
    TouchDesigner. While it reports an error the silhouette falls back to Difference automatically.
  - Mode **Difference**: the figure is whatever differs from the empty stage. Press **Capture Empty Stage**
    with nobody in view (the stage is also learned slowly, Learn 40 s - set 0 to keep only the captured one).
  - Mode **Dark figure**: when you are lit from behind (darker than what is behind you).
  - Threshold / Softness: how much difference (or darkness) counts; Silscale, Silx, Sily, Mirror place the figure.
  - The camera is read at half resolution (detailed outline); holes inside the figure are closed (sil_fill.glsl).
  - Self-repair: if more than 70% of the frame counts as the figure for 2 s (the empty stage was lost), it is captured again.

Files: build_scenes.py (rebuild: exec(open(project.folder + '/Scenes/build_scenes.py').read())), scenes.glsl,
sil_bg.glsl, sil_diff.glsl, sil_trail.glsl, scenes.tox. build_nin.py has the four acts; build_sphere.py reads scenes/OUT.
Earlier: scenes_v1_screens.glsl / build_scenes_v1_screens.py (with the layered screens, removed).
