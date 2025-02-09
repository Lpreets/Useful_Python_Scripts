#!/usr/bin/env python3
import os
import re
import subprocess
from yt_dlp import YoutubeDL

# Directory where the notes will be saved
NOTES_DIR = os.path.expanduser("~/Documents/Notes")
TIMEOUT_DURATION = 1200  # 20 minutes timeout for Fabric process

def sanitize_filename(title):
    """
    Remove characters that are illegal in file names and replace spaces with underscores.
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    return sanitized.replace(" ", "_")

def run_extract_wisdom(video_url, output_path, timeout=TIMEOUT_DURATION):
    """
    Runs the Fabric command to extract the transcript (or wisdom) for the given video URL.
    This function suppresses Fabric’s output.
    """
    command = f'fabric -y "{video_url}" --pattern=extract_wisdom -o "{output_path}"'
    try:
        subprocess.run(
            command,
            shell=True,
            check=True,
            timeout=timeout,
            stdout=subprocess.DEVNULL,  # Suppress standard output
            stderr=subprocess.DEVNULL   # Suppress error output
        )
        return True
    except subprocess.TimeoutExpired:
        print(f"Video processing timed out for: {video_url}")
    except subprocess.CalledProcessError as e:
        print(f"Error processing {video_url}: {e}")
    return False

def get_video_title(url):
    """
    Uses yt-dlp to fetch video metadata and returns the title.
    """
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info.get('title', None)

def main():
    # Ensure that the notes directory exists
    os.makedirs(NOTES_DIR, exist_ok=True)
    
    # Collect URLs from the user
    video_urls = []
    while True:
        url = input("Enter YouTube URL (or type 'done' to finish): ").strip()
        if url.lower() == "done":
            break
        if url:
            video_urls.append(url)
    
    total_videos = len(video_urls)
    if total_videos == 0:
        print("No URLs provided. Exiting.")
        return
    
    # Process each video URL and show only minimal progress messages
    for idx, url in enumerate(video_urls, start=1):
        print(f"Processing video {idx}/{total_videos}")
        try:
            title = get_video_title(url)
            if not title:
                print(f"Video {idx}/{total_videos}: Failed to fetch title. Skipping.")
                continue
        except Exception as e:
            print(f"Video {idx}/{total_videos}: Failed to fetch title: {e}")
            continue
        
        # Sanitize title to create a safe filename
        sanitized_title = sanitize_filename(title)
        output_path = os.path.join(NOTES_DIR, f"{sanitized_title}.txt")
        
        # Skip if a note with the same name already exists
        if os.path.exists(output_path):
            print(f"Video {idx}/{total_videos}: Note already exists. Skipping.")
            continue
        
        # Run Fabric command to process the video and save the note
        if run_extract_wisdom(url, output_path):
            print(f"Video {idx}/{total_videos}: Note saved.")
        else:
            print(f"Video {idx}/{total_videos}: Failed to create note.")
    
    print("Done processing all links.")

if __name__ == "__main__":
    main()
