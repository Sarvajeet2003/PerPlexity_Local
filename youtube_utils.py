"""
YouTube-related functionality for extracting video IDs and transcripts.
"""

import re
from config import HEADERS, REQUEST_TIMEOUT, MAX_LEN_PER_SOURCE

# Add the YouTube transcript API
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    print("[WARN] youtube-transcript-api not installed. YouTube transcript extraction will be disabled.")
    print("[INFO] Install with: pip install youtube-transcript-api")
    YOUTUBE_API_AVAILABLE = False

import requests
from bs4 import BeautifulSoup


def extract_youtube_video_id(url):
    """
    Extract YouTube video ID from various YouTube URL formats.
    Returns None if the URL is not a YouTube URL or ID extraction fails.
    """
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    match = re.match(youtube_regex, url)
    if match:
        return match.group(6)
    return None


def fetch_youtube_transcript(video_id):
    """
    Fetch and format transcript for a YouTube video.
    Returns formatted transcript text or None if unavailable.
    """
    if not YOUTUBE_API_AVAILABLE:
        print(f"[WARN] Cannot extract YouTube transcript: youtube-transcript-api not installed")
        return None
        
    try:
        # First try to get English transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            print(f"[INFO] Found English transcript")
        except Exception as e:
            print(f"[INFO] No English transcript available, trying to find any available transcript")
            # If English transcript is not available, get list of available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get a generated transcript first (usually more accurate)
            generated_transcript = None
            for transcript in transcript_list:
                if transcript.is_generated:
                    generated_transcript = transcript
                    break
            
            # If no generated transcript, get the first available one
            if generated_transcript:
                print(f"[INFO] Using generated transcript in language: {generated_transcript.language_code}")
                # Try to translate to English if not already in English
                if generated_transcript.language_code != 'en':
                    try:
                        print(f"[INFO] Attempting to translate transcript to English")
                        english_transcript = generated_transcript.translate('en')
                        transcript_list = english_transcript.fetch()
                    except Exception as translation_error:
                        print(f"[WARN] Could not translate transcript: {translation_error}")
                        transcript_list = generated_transcript.fetch()
                else:
                    transcript_list = generated_transcript.fetch()
            else:
                # Get the first available transcript
                first_transcript = next(iter(transcript_list))
                print(f"[INFO] Using transcript in language: {first_transcript.language_code}")
                # Try to translate to English if not already in English
                if first_transcript.language_code != 'en':
                    try:
                        print(f"[INFO] Attempting to translate transcript to English")
                        english_transcript = first_transcript.translate('en')
                        transcript_list = english_transcript.fetch()
                    except Exception as translation_error:
                        print(f"[WARN] Could not translate transcript: {translation_error}")
                        transcript_list = first_transcript.fetch()
                else:
                    transcript_list = first_transcript.fetch()
        
        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_list)
        
        # Clean up the transcript text
        # Remove excessive newlines and ensure proper spacing
        transcript_text = re.sub(r'\n{3,}', '\n\n', transcript_text)
        
        # Add some metadata about the source
        return f"YOUTUBE TRANSCRIPT [video_id: {video_id}]:\n\n{transcript_text}"
    except Exception as e:
        print(f"[WARN] Failed to get transcript for YouTube video {video_id}: {e}")
        return None


def get_youtube_metadata(url):
    """
    Fetch metadata for a YouTube video.
    Returns title and description if available.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('title')
        title_text = title.text.strip() if title else "Unknown YouTube Video"
        
        # Try to get video description
        description = ""
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = f"Video Description: {meta_desc.get('content')}"
        
        return title_text, description
    except Exception as e:
        print(f"[WARN] Failed to fetch YouTube page metadata: {e}")
        return "Unknown YouTube Video", ""