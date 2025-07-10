# Pod Poster

A simple, flexible Python script to automatically fetch the latest items from any media-based RSS feed, compress the enclosed audio, and post them to a Discord channel via a webhook.


---

### Dependencies

Before running, you need to install the required Python libraries and FFmpeg.

1.  **Python Libraries**:
    ```bash
    pip install requests pydub
    ```

2.  **FFmpeg**:
    Pydub requires FFmpeg for audio processing. You can install it on your system using a package manager.
    * **macOS**: `brew install ffmpeg`
    * **Debian/Ubuntu**: `sudo apt install ffmpeg`
    * **Windows**: Download from the [official FFmpeg site](https://ffmpeg.org/download.html) and add the `bin` folder to your system's PATH.

---

### How to Use

**Basic Usage:**
```bash
python pod-poster.py -u <FEED_URL> -w <WEBHOOK_URL> -r <ROOT_PATH>
```

Example:
```bash
python pod-poster.py \
    -u "https://feeds.megaphone.fm/yourpodcast" \
    -w "https://discord.com/api/webhooks/your/webhook" \
    -r ".//channel/item" \
    -n 3 \
    -q 64 \
    -l 1
```

---

### Command-Line Parameters
**Required Arguments**

`-u`, `--url`: The URL of the RSS feed.

`-w`, `--webhook`: The Discord webhook URL.

`-r`, `--root`: The root XPath to find episode items.

**Optional Arguments**

`-n`, `--number`: The number of newest episodes to upload. Default: 1.

`-q`, `--quality`: The bitrate for audio compression in kbps (32, 48, 64, 96). Default: 64.

`-l`, `--level`: Discord server boost level (1=25MB, 2=50MB, 3=100MB). Default: 1.

`-e`, `--embed`: Send the message as an embed instead of plain text.

**XML Structure Arguments (for advanced feeds)**

`-t`, `--title`: The XML tag for the episode title. Default: 'title'.

`-d`, `--description`: The XML tag for the episode description. If not used, no description is sent. Default: 'description'

`--media_tag`: The XML tag for the media enclosure. Default: 'enclosure'.

`--media_attr`: The attribute in the media tag holding the URL. Default: 'url'.
