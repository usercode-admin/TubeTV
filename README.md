# 📺 TubeTV
A lightweight Python utility designed to scan your local network and
remotely trigger YouTube video playback on Smart TVs, Android Boxes,
or Chromecast devices exposing their control ports.
---
## ✨ Features
* **Automated Network Scanning:** Instantly detects your local IP
subnet and performs a fast port scan (`5555`, `8008`, `8009`).
* **Multi-Protocol Support:**
* **ADB (Android Debug Bridge):** Controls Android TV/Boxes over
port `5555`.
* **DIAL Protocol:** Launches the native YouTube app on Smart TVs
via port `8008`.
* **Google Cast:** Streams directly to Chromecast-enabled devices
over port `8009` (utilizes `pychromecast`).
* **Smart URL Parsing:** Robust regex extraction pulls the
11-character `Video ID` from almost any valid YouTube URL format.
---
## 🛠 Prerequisites & Dependencies
Make sure you have the required Python library installed before
running the script:
```bash
pip install requests
```
(Optional) If you plan to use Google Cast features, install the Chromecast controller library:
```
pip install pychromecast
```
⚠️ Note for ADB Targets: If interacting with an Android Box over port 5555, the script attempts
to auto-install android-tools via pkg (ideal for environments like Termux). For Linux or Windows
desktops, ensure the adb binary is manually installed and added to your system's PATH.
🚀 How to Use
1. Fire up the tool:
python tubetv.py
2. Scan & Target: The tool will list all discovered active multimedia targets. Just type the
index number of your target:
[!] Here's our target!
[1] [192.168.1.15] [8008]
[2] [192.168.1.22] [5555]
[?] Choose your goal: 1
3. Drop the Link: Paste your YouTube URL into the prompt and hit Enter to trigger the
playback.
[?] Enter the YouTube video link:
[https://www.youtube.com/watch?v=dQw4w9WgXcQ](https://www.youtube.
com/watch?v=dQw4w9WgXcQ)
[...] Waiting for processing
Link:
[https://www.youtube.com/watch?v=dQw4w9WgXcQ](https://www.youtube.
com/watch?v=dQw4w9WgXcQ) successful
The video has been played.
📁 Code Overview

● scan_network(): Grabs the local interface IP and executes a non-blocking
socket.connect_ex scan across the /24 subnet.

● extract_video_id(): Cleans up inputs using regular expressions to isolate the exact
YouTube video identifier.

● play_via_adb() / play_via_dial() / play_via_cast(): Underlying execution methods tailored
to the respective device hardware protocols.

📜 Disclaimer
This tool is strictly intended for educational exercises, home lab testing, or harmless pranks on
devices you legally own or have explicit authorization to control. Please use responsibly and do
not deploy it on unauthorized networks.
