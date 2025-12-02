"""
Shared logic for YouTube transcript retrieval
"""

import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If no pattern matches, assume it's already a video ID
    return url.strip()

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"
    else:
        return f"[{minutes:02d}:{secs:02d}]"

def get_transcript(video_url: str, language: str = "en", include_timestamps: bool = False) -> dict:
    """
    Get transcript for a YouTube video

    Args:
        video_url: YouTube URL or video ID
        language: Language code (e.g., 'en', 'es')
        include_timestamps: Whether to include timestamps

    Returns:
        dict with 'content' (list with text) and optional 'data'
    """
    try:
        # Extract video ID
        video_id = extract_video_id(video_url)

        if not video_id:
            raise ValueError("Invalid YouTube URL or video ID")

        # Create API instance and get transcript
        api = YouTubeTranscriptApi()
        try:
            transcript_list = api.fetch(video_id, languages=(language,))
        except NoTranscriptFound:
            # Try to get any available transcript
            transcript_list = api.fetch(video_id)

        # Format output
        if include_timestamps:
            lines = [
                f"{format_timestamp(entry.start)} {entry.text}"
                for entry in transcript_list
            ]
            text = "\n".join(lines)
        else:
            text = " ".join(entry.text for entry in transcript_list)

        return {
            "content": [{
                "type": "text",
                "text": f"Transcript for video {video_id}:\n\n{text}"
            }],
            "data": {
                "video_id": video_id,
                "language": language,
                "entry_count": len(transcript_list),
                "duration_seconds": transcript_list[-1].start + transcript_list[-1].duration if transcript_list else 0
            }
        }

    except TranscriptsDisabled:
        raise ValueError(f"Transcripts are disabled for video: {video_id}")
    except VideoUnavailable:
        raise ValueError(f"Video unavailable or does not exist: {video_id}")
    except Exception as e:
        raise ValueError(f"Error retrieving transcript: {str(e)}")

def list_available_languages(video_url: str) -> dict:
    """
    List available transcript languages for a video

    Args:
        video_url: YouTube URL or video ID

    Returns:
        dict with available languages
    """
    try:
        video_id = extract_video_id(video_url)

        if not video_id:
            raise ValueError("Invalid YouTube URL or video ID")

        # Create API instance and get available transcripts
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        # Format available languages
        languages = []
        for transcript in transcript_list:
            lang_info = f"- {transcript.language_code} ({transcript.language})"
            if transcript.is_generated:
                lang_info += " [auto-generated]"
            languages.append(lang_info)

        text = f"Available transcript languages for video {video_id}:\n\n" + "\n".join(languages)

        return {
            "content": [{
                "type": "text",
                "text": text
            }],
            "data": {
                "video_id": video_id,
                "languages": [t.language_code for t in transcript_list]
            }
        }

    except VideoUnavailable:
        raise ValueError(f"Video unavailable or does not exist: {video_id}")
    except Exception as e:
        raise ValueError(f"Error listing languages: {str(e)}")
