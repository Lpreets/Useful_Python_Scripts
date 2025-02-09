#!/usr/bin/env python3
import os
import re
import datetime
import subprocess
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ---------------------------
# Configuration & Constants
# ---------------------------

# Define configuration in a dictionary.
WINDOWS_PATHS = {
    "crypto_credentials": "/mnt/c/Users/lpree/google_drive_crypto/YouTube_Crypto/client_secret.json",
    "business_credentials": "/mnt/c/Users/lpree/google_drive_business/YouTube_Business/client_secret.json",
    "crypto_save_path": "/mnt/c/Users/lpree/google_drive_crypto/YouTube_Crypto/Notes",
    "business_save_path": "/mnt/c/Users/lpree/google_drive_business/YouTube_Business/Notes",
}

DAYS_THRESHOLD = 7
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
TIMEOUT_DURATION = 1200  # seconds (20 minutes)
MAX_RETRIES = 2  # Number of retries for each video if processing fails

# Set up logging to file and to console.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        # Optionally, write logs to a file:
        # logging.FileHandler("youtube_to_notes.log"),
    ],
)

# ---------------------------
# Helper Functions
# ---------------------------

def windows_to_wsl_path(windows_path):
    """
    Converts a Windows-style path to a WSL-compatible path.
    If the path is already in WSL format, it returns it unchanged.
    """
    if windows_path.startswith("/mnt/"):
        return windows_path
    try:
        drive, path = windows_path.split(":/", 1)
        wsl_path = f"/mnt/{drive.lower()}/{path.replace(os.sep, '/')}"
        return wsl_path
    except ValueError:
        logging.error(f"Invalid Windows path format: {windows_path}")
        raise

def authenticate_youtube_oauth(credentials_path):
    """
    Authenticates with the YouTube API using OAuth and returns a service object.
    """
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, YOUTUBE_SCOPES)
    credentials = flow.run_local_server(port=8080)
    youtube = build("youtube", "v3", credentials=credentials)
    return youtube

def fetch_recent_videos(youtube):
    """
    Fetches recent videos from channels that the user is subscribed to.
    Only videos published in the past DAYS_THRESHOLD days are considered.
    This function currently retrieves up to 50 subscriptions and 10 videos per channel.
    Pagination may be added in the future if needed.
    """
    threshold_date = (datetime.datetime.utcnow() - datetime.timedelta(days=DAYS_THRESHOLD)).isoformat("T") + "Z"
    try:
        subscriptions_response = youtube.subscriptions().list(
            part="snippet",
            mine=True,
            maxResults=50
        ).execute()
    except Exception as e:
        logging.error(f"Failed to fetch subscriptions: {e}")
        return []

    videos = []
    for subscription in subscriptions_response.get("items", []):
        channel_id = subscription["snippet"]["resourceId"]["channelId"]
        try:
            channel_videos = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                publishedAfter=threshold_date,
                maxResults=10,
                order="date",
                type="video"
            ).execute()
        except Exception as e:
            logging.warning(f"Failed to fetch videos for channel {channel_id}: {e}")
            continue

        for video in channel_videos.get("items", []):
            title = video["snippet"]["title"]
            video_id = video["id"]["videoId"]
            if "#shorts" not in title.lower():
                videos.append({"title": title, "url": f"https://www.youtube.com/watch?v={video_id}"})
    return videos

def run_extract_wisdom(video_url, output_path, timeout=TIMEOUT_DURATION):
    """
    Executes the Fabric command to process a video using the 'extract_wisdom' pattern.
    Returns True if successful; otherwise, returns False.
    """
    command = f'fabric -y "{video_url}" --pattern=extract_wisdom -o "{output_path}"'
    try:
        logging.info(f"Running Fabric for {video_url} ...")
        subprocess.run(command, shell=True, check=True, timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout expired for video: {video_url}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error processing {video_url}: {e}")
    return False

def process_videos(videos, save_path):
    """
    Processes a list of videos: creates a sanitized file name for each video,
    checks if a note already exists, and calls Fabric to process the video.
    Retries up to MAX_RETRIES if processing fails.
    """
    for video in videos:
        # Sanitize the video title to create a safe file name.
        safe_title = re.sub(r'[<>:"/\\|?*]', '', video["title"]).replace(" ", "_")
        output_path = os.path.join(save_path, f"{safe_title}.txt")

        # Skip processing if the note file already exists.
        if os.path.exists(output_path):
            logging.info(f"Skipping '{video['title']}' - Note already exists.")
            continue

        success = False
        for attempt in range(MAX_RETRIES):
            logging.info(f"Processing '{video['title']}' (Attempt {attempt + 1}/{MAX_RETRIES})")
            if run_extract_wisdom(video["url"], output_path):
                logging.info(f"Saved '{video['title']}' to {output_path}")
                success = True
                break
            else:
                logging.info(f"Retrying '{video['title']}'...")
        if not success:
            logging.error(f"Failed to process '{video['title']}' after {MAX_RETRIES} attempts.")

# ---------------------------
# Main Execution
# ---------------------------

def main():
    # Convert Windows paths to WSL-compatible paths.
    oauth2_cred_crypto = windows_to_wsl_path(WINDOWS_PATHS["crypto_credentials"])
    oauth2_cred_business = windows_to_wsl_path(WINDOWS_PATHS["business_credentials"])
    crypto_save_path = windows_to_wsl_path(WINDOWS_PATHS["crypto_save_path"])
    business_save_path = windows_to_wsl_path(WINDOWS_PATHS["business_save_path"])

    # Authenticate and process for the crypto account.
    logging.info("Authenticating for Crypto account...")
    youtube_crypto = authenticate_youtube_oauth(oauth2_cred_crypto)
    crypto_videos = fetch_recent_videos(youtube_crypto)
    logging.info(f"Found {len(crypto_videos)} videos for Crypto account.")
    process_videos(crypto_videos, crypto_save_path)

    # Authenticate and process for the business account.
    logging.info("Authenticating for Business account...")
    youtube_business = authenticate_youtube_oauth(oauth2_cred_business)
    business_videos = fetch_recent_videos(youtube_business)
    logging.info(f"Found {len(business_videos)} videos for Business account.")
    process_videos(business_videos, business_save_path)

if __name__ == "__main__":
    main()
