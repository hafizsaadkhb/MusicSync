import os
import json
import yt_dlp
import requests
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# CONFIG
API_KEY = os.getenv('YOUTUBE_API_KEY')  # Use environment variable for API key
PLAYLIST_ID = 'PL0gojfB5PhyKd0rsD1IQMTMYR2AEc7B4e'
DATA_FILE = 'downloaded_ids.json'
DOWNLOAD_DIR = 'downloads'
ONEDRIVE_FOLDER = 'yt-music'

# Logging setup
logging.basicConfig(filename='music_sync.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create folders
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Load previously downloaded video IDs
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        downloaded_ids = json.load(f)
else:
    downloaded_ids = []

# Fetch playlist videos
url = f'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={PLAYLIST_ID}&key={API_KEY}'
response = requests.get(url)
if response.status_code != 200:
    logging.error(f"Failed to fetch playlist: {response.status_code} - {response.text}")
    exit(1)

items = response.json().get('items', [])

# Function to download a single video
def download_video(item):
    video_id = item['snippet']['resourceId']['videoId']
    if video_id not in downloaded_ids:
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        print(f'Downloading: {video_url}')
        logging.info(f"Downloading: {video_url}")
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': False
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            downloaded_ids.append(video_id)
        except Exception as e:
            logging.error(f"Error downloading {video_url}: {e}")

# Download videos in parallel
with ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(download_video, items)

# Save updated list
with open(DATA_FILE, 'w') as f:
    json.dump(downloaded_ids, f)

# Upload to OneDrive using Rclone
print("Uploading to OneDrive...")
logging.info("Uploading to OneDrive...")
subprocess.run([
    'rclone\\rclone.exe', 'copy', DOWNLOAD_DIR, f'onedrive:{ONEDRIVE_FOLDER}',
    '--progress'
])

# Cleanup local files
for file in os.listdir(DOWNLOAD_DIR):
    file_path = os.path.join(DOWNLOAD_DIR, file)
    try:
        os.remove(file_path)
        logging.info(f"Deleted local file: {file_path}")
    except Exception as e:
        logging.error(f"Error deleting file {file_path}: {e}")
