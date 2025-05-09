"""
Web content extraction functionality.
"""

import json
import requests
from bs4 import BeautifulSoup
from config import HEADERS, REQUEST_TIMEOUT, MAX_LEN_PER_SOURCE
from youtube_utils import extract_youtube_video_id, fetch_youtube_transcript, get_youtube_metadata


def fetch_and_extract_text(url: str) -> str | None:
    """
    Fetches content from a URL and extracts text using BeautifulSoup.
    Returns extracted text or None if fetching/parsing fails.
    """
    # Check if this is a YouTube URL and try to extract transcript
    video_id = extract_youtube_video_id(url)
    if video_id:
        print(f"[INFO] Detected YouTube video: {url} (ID: {video_id})")
        transcript = fetch_youtube_transcript(video_id)
        if transcript:
            print(f"[INFO] Successfully extracted transcript from YouTube video")
            
            # Also fetch the webpage to get metadata
            try:
                title_text, description = get_youtube_metadata(url)
                
                # Combine metadata with transcript
                full_text = f"YOUTUBE VIDEO: {title_text}\n\n"
                if description:
                    full_text += f"{description}\n\n"
                full_text += transcript
                return full_text[:MAX_LEN_PER_SOURCE]
            except Exception as e:
                print(f"[WARN] Failed to fetch YouTube page metadata: {e}")
                # If webpage fetch fails, just return the transcript
                return transcript[:MAX_LEN_PER_SOURCE]
    
    # Continue with regular webpage processing
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Check if content type is HTML
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            print(f"[WARN] Non-HTML content detected at {url} ({content_type})")
            # Try to extract text from non-HTML content when possible
            if 'application/json' in content_type:
                try:
                    return json.dumps(response.json(), indent=2)[:MAX_LEN_PER_SOURCE]
                except:
                    pass
            elif 'text/' in content_type:  # Handle other text formats
                return response.text[:MAX_LEN_PER_SOURCE]
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract metadata
        metadata = []
        title = soup.find('title')
        if title and title.text.strip():
            metadata.append(f"Title: {title.text.strip()}")
            
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description and meta_description.get('content', '').strip():
            metadata.append(f"Description: {meta_description.get('content', '').strip()}")
            
        # Extract structured data if available
        structured_data = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                structured_data.append(f"Structured Data: {json.dumps(data, indent=2)[:500]}...")
            except:
                pass
                
        # Enhanced content extraction strategy
        extracted_text = []
        
        # 1. Try to find main content containers
        main_content = soup.find('article') or soup.find('main') or soup.find('div', class_=['content', 'main-content', 'post', 'article'])
        if main_content:
            extracted_text.append(main_content.get_text(separator=' ', strip=True))
        
        # 2. Extract headers for structure
        headers = []
        for h in soup.find_all(['h1', 'h2', 'h3']):
            header_text = h.get_text(strip=True)
            if header_text:
                headers.append(f"{h.name}: {header_text}")
        if headers:
            extracted_text.append("Document Structure: " + " | ".join(headers))
        
        # 3. Extract paragraphs if we don't have enough content yet
        if not extracted_text or len(' '.join(extracted_text)) < 100:
            paragraphs = soup.find_all('p')
            if paragraphs:
                extracted_text.append(' '.join(p.get_text(strip=True) for p in paragraphs))
        
        # 4. Extract list items for additional structured content
        lists = soup.find_all(['ul', 'ol'])
        list_text = []
        for lst in lists:
            items = lst.find_all('li')
            if items:
                list_text.append(' '.join(f"• {item.get_text(strip=True)}" for item in items))
        if list_text:
            extracted_text.append(' '.join(list_text))
        
        # 5. Look for tables and convert to text
        tables = soup.find_all('table')
        table_text = []
        for table in tables[:2]:  # Limit to first 2 tables to avoid excessive content
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells:
                    table_text.append(' | '.join(cell.get_text(strip=True) for cell in cells))
        if table_text:
            extracted_text.append("Table Content: " + " / ".join(table_text))

        # Combine all extracted content
        all_text = []
        if metadata:
            all_text.append("METADATA: " + " | ".join(metadata))
        if structured_data:
            all_text.append("STRUCTURED DATA: " + structured_data[0])  # Include first structured data block
        all_text.extend(extracted_text)
        
        # Final text assembly
        text = ' '.join(all_text)
        
        # Basic cleaning
        text = ' '.join(text.split())  # Remove extra whitespace
        
        if not text:
            print(f"[WARN] No significant text extracted from {url}")
            return None
            
        # Limit text length per source to avoid excessive context
        return text[:MAX_LEN_PER_SOURCE]

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to parse {url}: {e}")
        return None