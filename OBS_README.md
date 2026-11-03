# OBS - the visuals as Spout sources

/project1/obs_out (saved as obs_out.tox) sends both screens over Spout:
- **TDA Main** - the main scene (sphere/OUT, 720 x 1280 portrait)
- **TDA Silhouette** - screen 2 (screen2/OUT, 1280 x 720 landscape)

In OBS (with the Spout2 plugin by Off World Live): Sources + -> Spout2 Capture -> Spout Senders: TDA Main
(again for TDA Silhouette). Composite Mode: Default. Audio: add Ableton's output as Desktop Audio / audio input.

## Cameras - TouchDesigner owns both, OBS takes them over Spout
- Laptop **Integrated Camera** -> the silhouette (/project1/scenes, Silhouette page).
- **Android Webcam** (Pixel) -> /project1/camera2 (saved as camera2.tox): plain video, sent as Spout **TDA Android**.
  Page Camera: Camera On, Camera (menu), Mirror, Spout Sender.
- In OBS use **no Video Capture Device** sources at all (a webcam can only be opened by one program);
  add Spout2 Capture -> TDA Android instead.
- Both cameras together: the laptop camera runs at 640 x 360 and the phone at 1280 x 720 (Media Foundation driver).
  With the laptop camera at a higher format the phone stays stuck at "Initializing" (USB bandwidth).
