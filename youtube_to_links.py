import os
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configuration
WINDOWS_PATHS = {
    "crypto_credentials": "/mnt/c/Users/lpree/google_drive_crypto/YouTube_Crypto/client_secret.json",
    "business_credentials": "/mnt/c/Users/lpree/google_drive_business/YouTube_Business/client_secret.json",
    "crypto_save_path": "/mnt/c/Users/lpree/google_drive_crypto/YouTube_Crypto/YouTube_Links",
    "business_save_path": "/mnt/c/Users/lpree/google_drive_business/YouTube_Business/YouTube_Links",
}

DAYS_THRESHOLD = 7
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

OAUTH2_CREDENTIALS_PATH_CRYPTO = WINDOWS_PATHS["crypto_credentials"]
OAUTH2_CREDENTIALS_PATH_BUSINESS = WINDOWS_PATHS["business_credentials"]
CRYPTO_SAVE_PATH = WINDOWS_PATHS["crypto_save_path"]
BUSINESS_SAVE_PATH = WINDOWS_PATHS["business_save_path"]

def authenticate_youtube_oauth(credentials_path):
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, YOUTUBE_SCOPES)
    credentials = flow.run_local_server(port=8080)
    youtube = build("youtube", "v3", credentials=credentials)
    return youtube

def fetch_recent_videos(youtube):
    threshold_date = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=DAYS_THRESHOLD)).isoformat("T") + "Z"
    subscriptions = youtube.subscriptions().list(part="snippet", mine=True, maxResults=50).execute()

    video_links = []
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
            video_id = video["id"]["videoId"]
            video_links.append(f"https://www.youtube.com/watch?v={video_id}")

    return video_links

def save_links_to_file(links, save_path):
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    file_name = f"YouTube_Links_{date_str}.txt"
    file_path = os.path.join(save_path, file_name)

    with open(file_path, "w") as file:
        for link in links:
            file.write(link + "\n")

    print(f"Saved links to {file_path}")

def main():
    youtube_crypto = authenticate_youtube_oauth(OAUTH2_CREDENTIALS_PATH_CRYPTO)
    crypto_links = fetch_recent_videos(youtube_crypto)
    save_links_to_file(crypto_links, CRYPTO_SAVE_PATH)

    youtube_business = authenticate_youtube_oauth(OAUTH2_CREDENTIALS_PATH_BUSINESS)
    business_links = fetch_recent_videos(youtube_business)
    save_links_to_file(business_links, BUSINESS_SAVE_PATH)

if __name__ == "__main__":
    main()
