# Ableton Reactive: default TouchDesigner template

This template builds `/project1/ableton_reactive`, a component whose visuals react live to **two Ableton tracks at
once**: track 1 punches (ring size, zoom, flash) and track 2 paints (noise texture, rotation, warp, colour). It
works the same way as the Neith scripts in the repo root: one Python build script that you run in the Textport.

| File | What it is |
| --- | --- |
| `build_ableton_reactive.py` | Builds the component and saves `ableton_reactive.tox` next to itself |
| `analysis.py` | Per-track analysis (levels, low/mid/high, onsets, song clock). Pure Python + numpy |
| `test_analysis.py` | `python test_analysis.py` checks the analysis outside TouchDesigner |

## Build it

1. Unzip `ableton_reactive.zip` anywhere, e.g. `Documents/TD Visuals/Ableton Reactive`. Keep the files
   together; the build script looks for `analysis.py` next to itself.
2. Open TouchDesigner (a new project is fine) and **drag `build_ableton_reactive.py` into the network**. A Text
   DAT appears. **Right-click it → Run Script.**
   - Alternative: open the Textport (Alt+T) and run
     `exec(open(r'C:/…/Ableton Reactive/build_ableton_reactive.py').read())`. If it says `analysis.py not found`,
     first run `AR_DIR = r'C:/…/Ableton Reactive'`.
3. A new component, `ableton_reactive`, appears. Dive in (select it, press `i`) and view `OUT`. The Textport also
   prints `ar_log`, a list of anything it couldn't set (parameter names occasionally change between builds),
   plus any node errors.
4. The build also saves **`ableton_reactive.tox`** next to the script. That's your reusable template: in any
   later project, drag the .tox straight in. You don't need to run the script again unless you change it.

The component starts in **Source = Test signal**: built-in kick (track 1) and off-beat bass (track 2) patterns at
the BPM parameter. You see it move straight away, before Ableton is even open.

`TRACKS = 2` at the top of the script sets how many track analyzers to build. Track 3 has a hi-hat test pattern
and track 4 a pad. Extra tracks show up as channels you can map yourself.

## What you get to map

The `TRACKS` CHOP inside the component (also shown on the `scope` trail) has these channels:

| Channel | Meaning |
| --- | --- |
| `tN_level` | track N loudness, 0..1 |
| `tN_low`, `tN_mid`, `tN_high` | bands (<250 Hz, 250 Hz–2 kHz, >2 kHz), 0..1, balance kept |
| `tN_pulse` | jumps to 1 on every onset (kick, note), then decays (`Pulse decay`) |
| `tN_hits` | onset counter, handy for "next colour / next shape on every hit" |
| `bpm`, `play`, `beat`, `phase`, `barphase` | song clock (from abletonSong, or internal at BPM) |

Use them in any parameter expression, e.g. `op('TRACKS')['t1_pulse']`. The **React** page sets gain, smoothing
(attack/release), onset threshold, and which band triggers onsets. **Auto gain** (on by default) normalises each
track to its recent peak, so quiet and loud sources both use the full 0..1 range. The **Look** page sets per-track
amount, feedback, and hue speed.

## Connecting Ableton

### A) TDAbleton (recommended if you have Max for Live)

TDAbleton is TouchDesigner's link to Ableton Live: an Ableton *MIDI Remote Script* plus Max for Live devices. It
needs Live 11.1.5+ and TouchDesigner 2021.20k+. The level devices (`TDA Level`, `TDA Audio Analyzer` rack) are
**Max for Live** devices, so you need Live **Suite**, or **Standard + the Max for Live add-on**. Intro and Lite
can't run them; use option B instead.

1. Install the TDAbleton remote script and select **TDAbleton** as a Control Surface in Live's
   *Settings → Link, Tempo & MIDI*. Follow the install section of the
   [TDAbleton page](https://derivative.ca/UserGuide/TDAbleton). The remote script has to match your
   TouchDesigner build, so update it whenever you update TouchDesigner.
2. The build script tries to load `abletonLevel` (one per track) and `abletonSong` from the Palette into
   `/project1` and points the component's **Track 1 / Track 2 / Song** parameters at them. If it logs
   "not found", drag them yourself from *Palette → TDAbleton* and drop them on those parameters. A parameter can
   take the component itself or its Out CHOP.
3. On each `abletonLevel`, pick the Ableton track (e.g. *1 Drums*, *2 Bass*). Then either press **Add TDA Level
   Device** (one level per track) or **Add TDA Audio Analyzer Rack** (low/mid/high per track; set its Output to
   the rack mode). The template detects which one you used from the channel names.
4. On `abletonSong`, turn on time data (Include Time Data) so the clock follows Live's transport.
5. Set **Source = TDAbleton** on the component.

Without Max for Live you can still point Track 1/2 at **abletonTrack** components with *Include Audio Data* on
(the template reads their `output_meter_*` channels). Ableton only sends those meters while they're **visible in
Live's window**, though, so this is a fallback.

### B) Audio device (any Live edition, no Max for Live)

Send each Ableton track to its own output pair (track *Audio To → Ext. Out → 3/4*, …) on an audio interface with
loopback or a multi-channel virtual device (e.g. VB-Audio VoiceMeeter on Windows, BlackHole 16ch on macOS). In
the component, select that device on the `audio_in` node. Check that **Track 1 audio chans** / **Track 2 audio
chans** (default `chan1 chan2` / `chan3 chan4`) match its channel names, then set **Source = Audio device**. The
template runs its own FFT for the bands, so this mode actually has finer frequency detail than TDAbleton's levels.

## Free (Non-Commercial) TouchDesigner limits that matter here

- **Resolution is capped at 1280×1280** for every TOP. The template renders 1280×720 (`W`, `H` in the script).
  For portrait, swap to 720×1280 as in `build_neith.py`.
- **Non-commercial use only.** If anyone pays you for the visuals (a paid gig, a commissioned video), you need a
  Commercial licence.
- A subset of pro operators is missing (Shared Memory, C++, SDI, …), and Blob Track is limited to 2 blobs.
  Nothing here uses them.
- Keys are tied to one machine; each account gets 10.
- TDAbleton, MIDI, OSC, audio and Python aren't on the Non-Commercial restriction list, so this template runs on
  the free version.

See [TouchDesigner Non-Commercial](https://derivative.ca/UserGuide/TouchDesigner_Non-Commercial) and
[Licensing](https://derivative.ca/UserGuide/Licensing).

## Notes

- `analysis.py` is the only place the signal processing lives. Edit it, rerun `test_analysis.py`, then rebuild,
  or paste it into the `analysis` DAT for a quick experiment.
- Untested inside TouchDesigner: the network parameter names follow the 2025 builds the Neith scripts were
  made with. Anything that didn't apply is listed in `ar_log` rather than stopping the build.
