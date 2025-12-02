"""
YouTube to MP3 conversion with metadata preservation
"""

import yt_dlp
import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, COMM, APIC, WXXX
from PIL import Image
import io
import requests
from datetime import datetime

def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL"""
    import re
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return url.strip()

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def format_duration(seconds: int) -> str:
    """Format duration as MM:SS or HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def embed_metadata(mp3_path: str, metadata: dict, video_info: dict):
    """
    Embed ID3 tags and album art into MP3 file

    Args:
        mp3_path: Path to MP3 file
        metadata: Metadata dictionary
        video_info: Full video info from yt-dlp
    """
    try:
        # Load or create ID3 tags
        try:
            audio = MP3(mp3_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
        except Exception as e:
            audio = MP3(mp3_path)
            if audio.tags is None:
                audio.add_tags()

        # Basic tags (delete existing to avoid conflicts)
        for tag in ['TIT2', 'TPE1', 'TALB', 'TDRC']:
            try:
                del audio.tags[tag]
            except KeyError:
                pass

        audio.tags['TIT2'] = TIT2(encoding=3, text=metadata['title'])  # Title
        audio.tags['TPE1'] = TPE1(encoding=3, text=metadata['artist'])  # Artist
        audio.tags['TALB'] = TALB(encoding=3, text=metadata['album'])   # Album

        # Date (format: YYYYMMDD -> YYYY)
        if metadata.get('date'):
            year = metadata['date'][:4]
            try:
                del audio.tags['TDRC']
            except KeyError:
                pass
            audio.tags['TDRC'] = TDRC(encoding=3, text=year)

        # Comments (description)
        if metadata.get('description'):
            desc = metadata['description'][:1000]  # Truncate to 1000 chars
            for key in list(audio.tags.keys()):
                if key.startswith('COMM:') and 'Description' in key:
                    del audio.tags[key]
            audio.tags['COMM:Description'] = COMM(encoding=3, lang='eng', desc='Description', text=desc)

        # Custom tags - Source URL
        for key in list(audio.tags.keys()):
            if key.startswith('WXXX:') and 'Source URL' in key:
                del audio.tags[key]
        audio.tags['WXXX:Source URL'] = WXXX(encoding=3, desc='Source URL', url=metadata['url'])

        # Additional metadata as comments
        stats = f"Uploader: {metadata.get('uploader', 'Unknown')}\n"
        stats += f"Duration: {metadata.get('duration', 0)}s\n"
        stats += f"Views: {metadata.get('view_count', 'N/A')}\n"
        stats += f"Likes: {metadata.get('like_count', 'N/A')}"
        for key in list(audio.tags.keys()):
            if key.startswith('COMM:') and 'YouTube Stats' in key:
                del audio.tags[key]
        audio.tags['COMM:YouTube Stats'] = COMM(encoding=3, lang='eng', desc='YouTube Stats', text=stats)

        # Embed thumbnail as album art
        thumbnail_url = video_info.get('thumbnail')
        if thumbnail_url:
            try:
                response = requests.get(thumbnail_url, timeout=10)
                if response.status_code == 200:
                    # Convert to JPEG and resize
                    img = Image.open(io.BytesIO(response.content))
                    img.thumbnail((500, 500), Image.Resampling.LANCZOS)

                    # Convert to JPEG
                    img_byte_arr = io.BytesIO()
                    img.convert('RGB').save(img_byte_arr, format='JPEG', quality=90)
                    img_data = img_byte_arr.getvalue()

                    # Delete existing album art
                    for key in list(audio.tags.keys()):
                        if key.startswith('APIC'):
                            del audio.tags[key]

                    # Embed as album art
                    audio.tags['APIC'] = APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,  # Cover (front)
                        desc='Album Art',
                        data=img_data
                    )
                    metadata['thumbnail_embedded'] = True
            except Exception as e:
                metadata['thumbnail_embedded'] = False

        # Save all tags
        audio.save()

    except Exception as e:
        print(f"Warning: Could not embed metadata: {e}")
        raise

def youtube_to_mp3(
    video_url: str,
    bitrate: str = "192k",
    output_dir: str = "/app/downloads",
    preserve_metadata: bool = True,
    output_filename: str = ""
) -> dict:
    """
    Download YouTube video and convert to MP3 with metadata

    Args:
        video_url: YouTube URL or video ID
        bitrate: Audio bitrate (128k, 192k, 256k, 320k)
        output_dir: Directory to save MP3 files
        preserve_metadata: Whether to embed ID3 tags
        output_filename: Custom output filename (optional)

    Returns:
        dict with file path, metadata, and status
    """

    try:
        # Extract video ID
        video_id = extract_video_id(video_url)

        # Configure output template
        if output_filename:
            # Custom filename
            base_name = output_filename.replace('.mp3', '')
            outtmpl = os.path.join(output_dir, f'{base_name}.%(ext)s')
        else:
            # Use video title
            outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')

        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': bitrate.replace('k', ''),
            }],
            'outtmpl': outtmpl,
            'writethumbnail': preserve_metadata,  # Download thumbnail if preserving metadata
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'no_color': True,
        }

        # Download and convert
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info
            info = ydl.extract_info(video_url, download=True)

            # Get output filename
            base_filename = ydl.prepare_filename(info)
            mp3_filename = base_filename.rsplit('.', 1)[0] + '.mp3'

            # Collect metadata
            metadata = {
                'title': info.get('title', 'Unknown Title'),
                'artist': info.get('uploader', 'Unknown Artist'),
                'album': info.get('album') or 'YouTube',
                'date': info.get('upload_date', ''),
                'description': info.get('description', ''),
                'url': video_url,
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', ''),
                'channel_id': info.get('channel_id', ''),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'thumbnail_embedded': False
            }

            # Embed metadata if requested
            if preserve_metadata and os.path.exists(mp3_filename):
                embed_metadata(mp3_filename, metadata, info)

            # Get file info
            file_size = os.path.getsize(mp3_filename) if os.path.exists(mp3_filename) else 0

            # Format response
            result_text = f"""✅ Download and conversion complete!

📁 File Details:
- Path: {mp3_filename}
- Size: {format_file_size(file_size)}
- Bitrate: {bitrate}
- Duration: {format_duration(metadata['duration'])}

🏷️ Metadata {'(Embedded)' if preserve_metadata else '(Not Embedded)'}:
- Title: {metadata['title']}
- Artist: {metadata['artist']}
- Album: {metadata['album']}
- Year: {metadata['date'][:4] if metadata['date'] else 'N/A'}
- Album Art: {'✅ Embedded' if metadata.get('thumbnail_embedded') else '❌ Not embedded'}

📊 Statistics:
- Views: {metadata['view_count']:,}
- Likes: {metadata['like_count']:,}
- Uploader: {metadata['uploader']}

🔗 Source: {metadata['url']}

💾 File saved to: {mp3_filename}
"""

            return {
                "content": [{
                    "type": "text",
                    "text": result_text
                }],
                "data": {
                    "success": True,
                    "file_path": mp3_filename,
                    "file_size": file_size,
                    "file_size_mb": round(file_size / (1024 * 1024), 2),
                    "bitrate": bitrate,
                    "metadata": metadata,
                    "metadata_embedded": preserve_metadata
                }
            }

    except Exception as e:
        raise ValueError(f"Error downloading/converting video: {str(e)}")
