# Grid - the Ableton MIDI track "GRID" as pads for the visuals

The TDA_MIDI device sits on the GRID track in Live (first device). TouchDesigner reads its notes
(/project1/grid_midi) and each pad (MIDI note) does one thing. Chain: ... sphere -> **grid** (freeze, blackout) -> viewer.

| note | action | what it does |
|---|---|---|
| 36 (C1) | act1 | Act 1 Static (acts switch to manual) |
| 37 | act2 | Act 2 Melt |
| 38 | act3 | Act 3 Scrim |
| 39 | act4 | Act 4 Backlit haze |
| 40 | auto | acts rotate by themselves again |
| 41 | sphere | summon the black hole / send it away |
| 42 | beam | flash its two beams (only while the sphere is there) |
| 43 | freeze | hold: the picture freezes and slowly sinks into darkness; release: back to live |
| 44 | blackout | fade to black / back (toggle, Blackout Fade 3 s) |
| 45 | silhouette | camera silhouette on / off |
| 46 | capture | capture the empty stage for the silhouette |

- Different pads? Press a pad and read **Last Note** on the Grid page of /project1/grid, then put that number in the
  table /project1/grid/map (column note). Last Action shows what the pad did.
- Pads also work from clips on the GRID track: put notes in a clip and the visuals follow the arrangement.
- Settings (page Grid): Enable, Blackout Fade, Freeze In / Out, Freeze Decay.

Build: exec(open(project.folder + '/Grid/build_grid.py').read())  - files: build_grid.py, freeze.glsl, grid.tox.
