from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
import sys
import os
import re
import requests
import time
import subprocess

try:
    import pychromecast
    from pychromecast.controllers.youtube import YouTubeController
    HAS_CHROMECAST = True
except ImportError:
    HAS_CHROMECAST = False

HTTP_PORT = 8080
httpd_server = None

def print_banner():
    banner = """
                 _ _     _____ _____
     _____ ___ _| |_|___|_   _|  |  |
    |     | -_| . | | .'| | | |  |  |
    |_|_|_|___|___|_|__,| |_|  \\___/"""
    print(banner)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def scan_network():
    print(" [...] Searching")
    local_ip = get_local_ip()
    ip_prefix = ".".join(local_ip.split(".")[:3]) + "."

    devices = []
    ports_to_scan = [5555, 8008, 8009, 1900, 8060, 36866, 7676]

    def check_port(ip, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.8)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                return {"ip": ip, "port": port}
        except Exception:
            pass
        return None

    tasks = []
    for i in range(1, 255):
        ip = f"{ip_prefix}{i}"
        for port in ports_to_scan:
            tasks.append((ip, port))

    with ThreadPoolExecutor(max_workers=75) as executor:
        futures = {executor.submit(check_port, ip, port): ip for ip, port in tasks}
        for future in as_completed(futures):
            res = future.result()
            if res:
                devices.append(res)

    return devices

def extract_video_id(url):
    regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\\/\\s?#]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None

def force_max_volume_adb(ip):
    os.system(f"adb -s {ip}:5555 shell media volume --set 15 > /dev/null 2>&1")
    os.system(f"adb -s {ip}:5555 shell media volume --set 100 > /dev/null 2>&1")

def force_max_volume_catt(ip):
    if os.system("command -v catt > /dev/null 2>&1") == 0:
        os.system(f"catt -d {ip} volume 100 > /dev/null 2>&1")

def play_via_adb(ip, video_id):
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
        res = requests.post(url, data=payload, headers=headers, timeout=3)
        if res.status_code in [200, 201, 202]:
            return True
    except Exception:
        pass
    return os.system(f"catt -d {ip} cast 'https://youtu.be/{video_id}' > /dev/null 2>&1") == 0

def play_via_cast(ip, video_id):
    if not HAS_CHROMECAST:
        return os.system(f"catt -d {ip} cast 'https://youtu.be/{video_id}' > /dev/null 2>&1") == 0
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


def play_local_media(ip, port, file_path):
    clean_path = os.path.abspath(file_path)

    if not os.path.exists(clean_path):
        print(f" [!] Error: File not found: {clean_path}")
        return False

    print(f" [+] Casting local media (MP3/MP4): {os.path.basename(clean_path)}")
    
    if port in [1900, 36866, 7676]:
        cmd = f'catt -d {ip} cast -f dlna_video "{clean_path}"'
    else:
        cmd = f'catt -d {ip} cast "{clean_path}"'
        
    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True

def main():
    print_banner()
    devices = scan_network()

    if not devices:
        print(" [-] No devices found.")
        return

    print(" ╭───The devices were found")
    print(" ╰─ IP            Port")
    for index, dev in enumerate(devices, 1):
        print(f" {index}- {dev['ip']:<13} {dev['port']}")
        
    print(" [Port support: 8008 <url_ytp> <mp3_mp4>, 8009 <url_ytp> <mp3_mp4>]")
    print("               [5555 <url>, 8060, 7676, 1900, 36866 <mp3_mp4>]")

    try:
        choice = int(input(" [?] Please select your device: "))
        if choice < 1 or choice > len(devices):
            return
    except ValueError:
        return

    selected_dev = devices[choice - 1]
    port = selected_dev["port"]
    ip = selected_dev["ip"]

    youtube_url = ""
    media_path = ""

    if port in [8008, 8009]:
        ans = input(" [?] Enter the YouTube video link (leave blank for local file): ").strip()
        if ans:
            youtube_url = ans
        else:
            media_path = input(" [?] Path to the file folder <mp3-mp4>: ").strip()
    elif port == 5555:
        youtube_url = input(" [?] Enter the YouTube video link: ").strip()
    else:
        media_path = input(" [?] Path to the file folder <mp3-mp4>: ").strip()

    if media_path:
        media_path = media_path.replace('"', '').replace("'", "")

    if not youtube_url and not media_path:
        return

    print(" [...] Increasing the volume")
    if port == 5555:
        force_max_volume_adb(ip)
    else:
        force_max_volume_catt(ip)
    print(" [*] Sound levels have been increased.")

    time.sleep(2)
    print(" [...] Video is playing")

    success = False
    if youtube_url:
        video_id = extract_video_id(youtube_url)
        if video_id:
            if port == 5555:
                success = play_via_adb(ip, video_id)
            elif port == 8009:
                success = play_via_cast(ip, video_id)
            elif port == 8008:
                success = play_via_dial(ip, video_id)
                
        if success:
            print(f" [*] Link: {youtube_url} Successfully broadcast!")

    elif media_path:
        success = play_local_media(ip, port, media_path)
        if success:
            print(f" [*] File path: {media_path} Successfully broadcast!")

    if success:
        print("      Processing complete, By: mediaTV")
    else:
        print(" [-] Broadcast failed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n [-] Cancelled by user.")
        sys.exit()

