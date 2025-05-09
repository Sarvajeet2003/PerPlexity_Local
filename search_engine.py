"""
Search engine functionality using DuckDuckGo.
"""

from duckduckgo_search import DDGS
from config import MAX_RESULTS
from youtube_utils import extract_youtube_video_id


def perform_web_search(query):
    """
    Performs a web search using DuckDuckGo.
    Returns a list of URLs from search results.
    """
    search_results = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=MAX_RESULTS))
            if results:
                search_results = [r['href'] for r in results]
                print(f"[INFO] Found {len(search_results)} potential URLs:")
                for url in search_results:
                    print(f"  - {url}")
            else:
                print("[INFO] No search results found.")
    except Exception as e:
        print(f"[ERROR] Failed during web search: {e}")
    
    return search_results


def extract_youtube_url(query):
    """
    Extracts a YouTube URL from the query if present.
    Returns the URL and an updated query.
    """
    youtube_url = None
    updated_query = query
    
    query_words = query.split()
    for word in query_words:
        video_id = extract_youtube_video_id(word)
        if video_id:
            youtube_url = word
            # Remove the YouTube URL from the query
            updated_query = query.replace(youtube_url, "").strip()
            if not updated_query or updated_query.lower() in ["summarize", "summarise", "summary"]:
                # Provide a more detailed default query for YouTube videos
                updated_query = "Provide a detailed summary of this video, covering all main points and key information in a comprehensive way"
            break
    
    return youtube_url, updated_query