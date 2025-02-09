import os
import re
import datetime
import subprocess
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configuration
WINDOWS_PATHS = {
    "crypto_credentials": "J:/My Drive/YouTube_Crypto/client_secret.json",
    "business_credentials": "I:/My Drive/YouTube_Business/client_secret.json",
    "crypto_save_path": "J:/My Drive/YouTube_Crypto/Notes",
    "business_save_path": "I:/My Drive/YouTube_Business/Notes",
}

DAYS_THRESHOLD = 7
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
TIMEOUT_DURATION = 1200  # 20 minutes
MAX_RETRIES = 2  # Number of retries for each video if processing fails

def windows_to_wsl_path(windows_path):
    """Converts Windows paths to WSL-compatible paths."""
    drive, path = windows_path.split(":/")
    wsl_path = f"/mnt/{drive.lower()}/{path.replace(os.sep, '/')}"
    return wsl_path

# Update paths for WSL
OAUTH2_CREDENTIALS_PATH_CRYPTO = windows_to_wsl_path(WINDOWS_PATHS["crypto_credentials"])
OAUTH2_CREDENTIALS_PATH_BUSINESS = windows_to_wsl_path(WINDOWS_PATHS["business_credentials"])
CRYPTO_SAVE_PATH = windows_to_wsl_path(WINDOWS_PATHS["crypto_save_path"])
BUSINESS_SAVE_PATH = windows_to_wsl_path(WINDOWS_PATHS["business_save_path"])

def authenticate_youtube_oauth(credentials_path):
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, YOUTUBE_SCOPES)
    credentials = flow.run_local_server(port=8080)
    youtube = build("youtube", "v3", credentials=credentials)
    return youtube

def fetch_recent_videos(youtube):
    threshold_date = (datetime.datetime.utcnow() - datetime.timedelta(days=DAYS_THRESHOLD)).isoformat("T") + "Z"
    subscriptions = youtube.subscriptions().list(part="snippet", mine=True, maxResults=50).execute()

    videos = []
    for subscription in subscriptions.get("items", []):
        channel_id = subscription["snippet"]["resourceId"]["channelId"]
        channel_videos = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            publishedAfter=threshold_date,
            maxResults=10,
            order="date",
            type="video"
        ).execute()

        for video in channel_videos.get("items", []):
            title = video["snippet"]["title"]
            video_id = video["id"]["videoId"]
            if "#shorts" not in title.lower():
                videos.append({"title": title, "url": f"https://www.youtube.com/watch?v={video_id}"})

    return videos

def run_extract_wisdom(video_url, output_path, timeout=TIMEOUT_DURATION):
    command = f'fabric -y "{video_url}" --pattern=extract_wisdom -o "{output_path}"'
    try:
        print(f"Running Fabric for {video_url} with extract_wisdom pattern...")
        subprocess.run(command, shell=True, check=True, timeout=timeout)
        return True  # Indicates success
    except subprocess.TimeoutExpired:
        print(f"Timeout expired for video: {video_url}")
    except subprocess.CalledProcessError as e:
        print(f"Error processing {video_url}: {e}")
    return False  # Indicates failure

def process_videos(videos, save_path):
    for video in videos:
        title = video["title"]
        title = re.sub(r'[<>:"/\\|?*]', '', title).replace(" ", "_")
        output_path = os.path.join(save_path, f"{title}.txt")

        # Check if note already exists
        if os.path.exists(output_path):
            print(f"Skipping '{video['title']}' - Note already exists.")
            continue

        # Attempt to process video with retries
        success = False
        for attempt in range(MAX_RETRIES):
            print(f"Processing '{video['title']}' (Attempt {attempt + 1}/{MAX_RETRIES})")
            if run_extract_wisdom(video["url"], output_path):
                print(f"Saved '{video['title']}' to {output_path}")
                success = True
                break
            else:
                print(f"Retrying '{video['title']}'...")

        if not success:
            print(f"Failed to process '{video['title']}' after {MAX_RETRIES} attempts.")

# Authenticate and process for both accounts
def main():
    youtube_crypto = authenticate_youtube_oauth(OAUTH2_CREDENTIALS_PATH_CRYPTO)
    crypto_videos = fetch_recent_videos(youtube_crypto)
    process_videos(crypto_videos, CRYPTO_SAVE_PATH)

    youtube_business = authenticate_youtube_oauth(OAUTH2_CREDENTIALS_PATH_BUSINESS)
    business_videos = fetch_recent_videos(youtube_business)
    process_videos(business_videos, BUSINESS_SAVE_PATH)

if __name__ == "__main__":
    main()
