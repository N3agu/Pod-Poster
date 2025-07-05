import requests
import xml.etree.ElementTree as ET
import os
import argparse
import time
import re
from pydub import AudioSegment

def compress_mp3(file_path, output_path, bitrate="64k"):
    print(f"Compressing {file_path} with bitrate {bitrate}...")
    try:
        audio = AudioSegment.from_mp3(file_path)
        audio.export(output_path, format="mp3", bitrate=bitrate)
        print(f"Compressed file saved as {output_path}")
        return True
    except Exception as e:
        print(f"Could not compress file: {e}")
        return False

def send_to_discord(webhook_url, title, description, file_path):
    print(f"Uploading '{os.path.basename(file_path)}' to Discord...")
    try:
        # Format the message with a bold title and the description after an empty line
        message_content = f"**{title}**\n\n{description}"

        with open(file_path, 'rb') as f:
            payload = {"content": message_content}
            files = {'file': (os.path.basename(file_path), f)}
            response = requests.post(webhook_url, data=payload, files=files)
            
            # Handle Discord rate limiting
            if response.status_code == 429:
                retry_after = response.json().get('retry_after', 1)
                print(f"Rate limited. Waiting for {retry_after} seconds.")
                time.sleep(retry_after)
                # Retry the request
                response = requests.post(webhook_url, data=payload, files=files)

        return response
    except Exception as e:
        print(f"Error sending to discord: {e}")
        return None

def sanitize_filename(name):
    # Remove illegal characters
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
    # Replace spaces with underscores
    sanitized = sanitized.replace(" ", "_")
    # Limit length to avoid OS errors (max ~255 bytes on win10)
    return sanitized[:230]

def process_episode(episode, webhook_url, bitrate, max_size_mb, title_tag, description_tag, media_tag, media_attr):
    original_file = None
    compressed_file = None
    
    try:
        title_element = episode.find(title_tag)
        if title_element is None:
            print(f"Error: Could not find title tag '{title_tag}' in item. Skipping.")
            return
        title = title_element.text

        description_element = episode.find(description_tag)
        # Use description if it exists, otherwise use an empty string.
        description = description_element.text.strip() if description_element is not None and description_element.text else ""
        # Truncate description to keep Discord message clean
        if len(description) > 500:
            description = description[:500] + "..."
        
        media_element = episode.find(media_tag)
        if media_element is None:
            print(f"Error: Could not find media tag '{media_tag}' in item. Skipping.")
            return
        
        media_url = media_element.get(media_attr)
        if media_url is None:
            print(f"Error: Could not find media attribute '{media_attr}' in tag '{media_tag}'. Skipping.")
            return

        # Create a valid filename from the episode title
        base_filename = sanitize_filename(title)
        original_file = f"{base_filename}.mp3"
        compressed_file = f"{base_filename}_compressed.mp3"

        print("-" * 50)
        print(f"Processing episode: {title}")

        # 1. Download the original audio file
        print(f"Downloading audio from: {media_url}")
        audio_response = requests.get(media_url, stream=True)
        audio_response.raise_for_status()

        with open(original_file, 'wb') as f:
            for chunk in audio_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Audio downloaded and saved as {original_file}")

        # 2. Compress the downloaded file
        bitrate_str = f"{bitrate}k"
        if not compress_mp3(original_file, compressed_file, bitrate=bitrate_str):
            return # Skip if compression fails

        # 3. Check file size before uploading
        file_size_mb = os.path.getsize(compressed_file) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            print(f"Warning: Compressed file '{compressed_file}' ({file_size_mb:.2f}MB) is too large for the server's limit of {max_size_mb}MB. Skipping upload.")
            return

        # 4. Send the compressed file to Discord
        discord_response = send_to_discord(webhook_url, title, description, compressed_file)

        if discord_response and discord_response.status_code in [200, 204]:
            print("Successfully sent to Discord!")
        else:
            status = discord_response.status_code if discord_response else 'N/A'
            text = discord_response.text if discord_response else 'No response'
            print(f"Failed to send to Discord. Status code: {status}")
            print(f"Response: {text}")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading episode '{title}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred while processing episode: {e}")
    finally:
        # 5. Clean up files for this episode
        if original_file and os.path.exists(original_file):
            os.remove(original_file)
        if compressed_file and os.path.exists(compressed_file):
            os.remove(compressed_file)
        print("Cleaned up temporary files.")

def main(args):
    level_to_size = {1: 25, 2: 50, 3: 100}
    max_size_mb = level_to_size[args.level]
    print(f"Server level set to {args.level}, max upload size is {max_size_mb}MB.")

    try:
        # Fetch the RSS feed
        print(f"Fetching RSS feed from: {args.url}")
        response = requests.get(args.url)
        response.raise_for_status()
        rss_content = response.content

        # Parse the XML
        root = ET.fromstring(rss_content)
        
        # Find all elements using the root path
        all_episodes = root.findall(args.root)
        if not all_episodes:
            print(f"Could not find any episodes using the root path '{args.root}'.")
            return

        # Select the 'n' newest episodes
        newest_episodes = all_episodes[:args.number]
        
        # Reverse this smaller list to process from oldest to newest within the selection
        episodes_to_process = list(reversed(newest_episodes))
        
        print(f"Found {len(all_episodes)} total episodes. Processing the {len(episodes_to_process)} most recent ones.")

        for episode in episodes_to_process:
            process_episode(episode, args.webhook, args.quality, max_size_mb, args.title_tag, args.description_tag, args.media_tag, args.media_attr)
            # Add a small delay between posts to avoid spamming Discord's API
            time.sleep(2)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the RSS feed: {e}")
    except ET.ParseError as e:
        print(f"Error parsing the XML feed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch podcast episodes from an RSS feed and post them to a Discord webhook.")
    # Required arguments
    parser.add_argument("-u", "--url", required=True, help="The URL of the RSS feed.")
    parser.add_argument("-w", "--webhook", required=True, help="The Discord webhook URL.")
    parser.add_argument("-r", "--root", required=True, help="The root XPath to find episode items.")
    
    # Optional arguments
    parser.add_argument("-n", "--number", type=int, default=1, help="The number of newest episodes to upload (default: 1).")
    parser.add_argument("-q", "--quality", type=int, default=64, choices=[32, 48, 64, 96], help="The bitrate for audio compression in kbps. Default: 64.")
    parser.add_argument("-l", "--level", type=int, default=1, choices=[1, 2, 3], help="Discord server boost level (1=25MB, 2=50MB, 3=100MB). Default: 1.")
    
    # XML structure arguments
    parser.add_argument("-t", "--title_tag", default="title", help="The XML tag for the episode title. Default: 'title'.")
    parser.add_argument("-d", "--description_tag", default="description", help="The XML tag for the episode description. Default: 'description'.")
    parser.add_argument("--media_tag", default="enclosure", help="The XML tag for the media enclosure. Default: 'enclosure'.")
    parser.add_argument("--media_attr", default="url", help="The attribute in the media tag holding the URL. Default: 'url'.")

    args = parser.parse_args()
    
    main(args)
