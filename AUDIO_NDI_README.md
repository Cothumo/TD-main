# Audio from Ableton to TouchDesigner over NDI

Ableton stays on the UMC (ASIO). The **NDI Output** plugin (NDI Tools, VST3) on Ableton's Master sends the mix as an
NDI stream named "<computer> (VST Output)".

TouchDesigner: /project1/audio_ndi (saved as audio_ndi.tox)
- sources (NDI DAT) lists the NDI streams; ndi_in (NDI In TOP) receives "NOTTHEONEYOUCAMELOOKINGFOR (VST Output)";
  audio (Audio NDI CHOP, time sliced) -> trim (Math CHOP, gain = the Trim parameter on the audio_ndi Audio page, 0.4) -> rename chan1 chan2 -> out.
  Trim lowers the signal only for the analysis (kick/snare/hat onsets); raise it if the hits get weak, lower it if they fire constantly.
- neith_live/audio_in is now a Select CHOP of /project1/audio_ndi/out, so the detailed analysis (kick, snare, hat,
  low / mid / high, level) and the Arc (song shape) listen to it. The old device input is neith_live/audio_in_device
  (inactive) - to go back, delete the select, rename audio_in_device to audio_in and switch it on.
- The NDI Output plugin sits before the master fader, so the fader does not change what it sends: set its level
  (Audio level in the plugin, about -8 dB) so the peaks stay below 0 dB, otherwise low / mid / high / level sit at their maximum.
- If the computer name or the plugin's output name changes, pick the new stream in ndi_in (Name).
