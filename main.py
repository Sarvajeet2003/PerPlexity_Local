import sys
import requests
import json # Import json library
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import re  # Add regex for YouTube URL detection

# Add the YouTube transcript API
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    print("[WARN] youtube-transcript-api not installed. YouTube transcript extraction will be disabled.")
    print("[INFO] Install with: pip install youtube-transcript-api")
    YOUTUBE_API_AVAILABLE = False

# Define how many search results we want to process
MAX_RESULTS = 5
# Define a timeout for web requests
REQUEST_TIMEOUT = 4 # seconds
# Define a user agent to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
MAX_LEN_PER_SOURCE = 20000

# --- Ollama Configuration ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
# *** IMPORTANT: Change this to the model you pulled and want to use ***
OLLAMA_MODEL = "phi3:instruct" # Corrected model name based on previous recommendation
OLLAMA_REQUEST_TIMEOUT = 120 # Increased timeout slightly for potentially longer streaming

# --- Context Preservation Configuration ---
MAX_HISTORY_TURNS = 3  # Number of previous turns to keep in context
HISTORY_ENABLED = True  # Toggle for enabling/disabling history


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
                response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.find('title')
                title_text = title.text.strip() if title else "Unknown YouTube Video"
                
                # Try to get video description
                description = ""
                meta_desc = soup.find('meta', {'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    description = f"Video Description: {meta_desc.get('content')}\n\n"
                
                # Combine metadata with transcript
                full_text = f"YOUTUBE VIDEO: {title_text}\n\n{description}{transcript}"
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

def synthesize_with_ollama_stream(query: str, context: str, history=None):
    """
    Sends the query and context to the Ollama API and yields response chunks as they arrive.
    Handles potential errors during streaming.
    Yields:
        str: Chunks of the generated response.
    Raises:
        requests.exceptions.RequestException: If connection or request fails.
        Exception: For other unexpected errors during processing.
    """
    # Build history context if available
    history_text = ""
    if history and HISTORY_ENABLED:
        history_text = "CONVERSATION HISTORY:\n"
        for i, (q, a) in enumerate(history):
            history_text += f"User: {q}\nAssistant: {a}\n\n"
        history_text += "---\n\n"
    
    # Check if this is a YouTube transcript and format the prompt accordingly
    if "YOUTUBE TRANSCRIPT" in context:
        prompt = f"""
Based on the following YouTube video transcript and any metadata provided, please provide a detailed summary of the video.
If the transcript is in a language other than English, it has been automatically translated.

Your summary should:
1. Be comprehensive and detailed (at least 5-10 paragraphs)
2. Include key points, main arguments, and important details
3. Maintain the logical flow of the original content
4. Mention any significant examples or evidence presented
5. Conclude with the main takeaways from the video

{history_text}VIDEO CONTENT:
---
{context}
---

TASK: {query}

DETAILED SUMMARY:
"""
    else:
        # Regular prompt remains the same
        prompt = f"""
Based *only* on the following context and conversation history (if provided), please provide a comprehensive answer to the user's query.
Do not use any prior knowledge. If the context does not contain enough information to answer the query, state that clearly.

{history_text}CONTEXT:
---
{context}
---

USER QUERY: {query}

ANSWER:
"""
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True, # Enable streaming
        "temperature": 0.7,  # Add some creativity for better summaries
        "num_predict": 2048  # Encourage longer responses
    }
    headers = {'Content-Type': 'application/json'}

    try:
        print(f"[INFO] Sending streaming request to Ollama (model: {OLLAMA_MODEL})...")
        # Use stream=True in requests.post to handle the response incrementally
        with requests.post(
            OLLAMA_API_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=OLLAMA_REQUEST_TIMEOUT,
            stream=True # Enable streaming in the requests library
        ) as response:
            response.raise_for_status() # Check for HTTP errors immediately

            print("[INFO] Receiving stream from Ollama...")
            # Process the stream line by line
            for line in response.iter_lines():
                if line:
                    try:
                        # Each line is a JSON object, decode it
                        chunk = json.loads(line.decode('utf-8'))
                        # Check if the chunk contains the 'response' part
                        if 'response' in chunk:
                            yield chunk['response'] # Yield the actual text chunk
                        # Check if the generation is done (Ollama sends a final status object)
                        if chunk.get('done', False):
                            print("\n[INFO] Ollama stream finished.")
                            break # Exit the loop once generation is complete
                    except json.JSONDecodeError:
                        print(f"[WARN] Skipping invalid JSON line from stream: {line}")
                    except Exception as e:
                        print(f"[ERROR] Error processing stream chunk: {e}")
                        # Decide if you want to stop or continue on chunk errors
                        break # Stop on chunk processing error

    # Re-raise specific exceptions for the caller to handle
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] Could not connect to Ollama API at {OLLAMA_API_URL}. Is Ollama running?")
        raise e
    except requests.exceptions.Timeout as e:
        print(f"[ERROR] Request to Ollama timed out after {OLLAMA_REQUEST_TIMEOUT} seconds.")
        raise e
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed during Ollama request: {e}")
        # Attempt to print error body if available
        try:
            print(f"[DEBUG] Ollama Error Response Body: {response.text}")
        except:
            pass
        raise e
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during Ollama streaming setup: {e}")
        raise e # Re-raise unexpected errors


def perform_search_and_synthesis(query: str, conversation_history=None):
    """
    Handles the core logic: Search, Extract, Synthesize (streaming), Print.
    """
    print(f"\n[INFO] Received query: {query}")
    
    # Check if the query itself is a YouTube URL
    video_id = extract_youtube_video_id(query.split()[0])
    if video_id:
        print(f"[INFO] Direct YouTube URL detected in query: {query.split()[0]}")
        youtube_url = query.split()[0]
        search_results = [youtube_url]  # Use the YouTube URL as the only search result
        
        # Extract any additional query text after the URL
        remaining_query = ' '.join(query.split()[1:])
        if remaining_query:
            print(f"[INFO] Additional query text: {remaining_query}")
            query = remaining_query  # Update query to only include the text part
        else:
            # Provide a more detailed default query for YouTube videos
            query = "Provide a detailed summary of this video, covering all main points and key information in a comprehensive way"
    else:
        # Regular web search
        print("[INFO] Searching web using DuckDuckGo...")
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
                    return
        except Exception as e:
            print(f"[ERROR] Failed during web search: {e}")
            return

    # Rest of the function remains the same
    print("\n[INFO] Fetching and extracting content...")
    extracted_texts = []
    sources = []
    for url in search_results:
        print(f"[INFO] Processing {url}...")
        text = fetch_and_extract_text(url)
        if text:
            extracted_texts.append(text)
            sources.append(url)
            print(f"[INFO] Successfully extracted text from {url} (length: {len(text)})")
        else:
            print(f"[INFO] Failed to extract text from {url}")

    if not extracted_texts:
        print("[ERROR] No text could be extracted from any search result.")
        return

    full_context = "\n\n---\n\n".join(extracted_texts)
    print(f"\n[INFO] Total extracted context length: {len(full_context)}")
    
    if conversation_history and HISTORY_ENABLED:
        print(f"[INFO] Including {len(conversation_history)} previous conversation turns")

    # --- Call Ollama for Synthesis (Streaming) ---
    print("\n[INFO] Synthesizing answer with Ollama (streaming)...")
    print("\n" + "="*40 + " RESULTS " + "="*40)
    print("\nSynthesized Answer:\n")

    full_response = ""
    try:
        # Iterate through the generator returned by the streaming function
        for chunk in synthesize_with_ollama_stream(query, full_context, conversation_history):
            print(chunk, end='', flush=True) # Print chunk immediately without newline
            full_response += chunk # Accumulate the full response if needed later

        # Add a newline after the streaming is complete
        print()

        # Check if any response was actually generated
        if not full_response:
             print("\n[WARN] No response content received from Ollama stream.")

        print("\nSources Used:")
        for i, url in enumerate(sources):
             print(f"  [{i+1}] {url}")

    except Exception as e:
        # Handle errors raised from the streaming function
        print(f"\n[ERROR] Failed to generate or stream the synthesized answer: {e}")
        print("\nSources Checked:") # Still show sources even if synthesis failed
        for i, url in enumerate(sources):
             print(f"  [{i+1}] {url}")

    print("\n" + "="*90 + "\n")


def main():
    """
    Main function to run the query loop.
    """
    print("Local Perplexity-like Search Tool")
    print("Enter your query below, or type 'exit' to quit.")
    # print(f"Context preservation is {'ENABLED' if HISTORY_ENABLED else 'DISABLED'}")
    
    # Initialize conversation history
    conversation_history = []

    while True:
        try:
            query = input("Query: ")
            if query.lower() == 'exit':
                print("Exiting...")
                break
            if query.lower() == 'clear history':
                conversation_history = []
                print("[INFO] Conversation history cleared.")
                continue
            if query.lower() == 'toggle history':
                # global HISTORY_ENABLED
                HISTORY_ENABLED = not HISTORY_ENABLED
                print(f"[INFO] Context preservation {'enabled' if HISTORY_ENABLED else 'disabled'}")
                continue
            if not query:
                continue

            # Call the search and synthesis function with history
            response = perform_search_and_synthesis(query, conversation_history)
            
            # Add this interaction to history if we got a valid response
            if response:
                conversation_history.append((query, response))
                # Trim history to keep only recent conversations
                if len(conversation_history) > MAX_HISTORY_TURNS:
                    conversation_history = conversation_history[-MAX_HISTORY_TURNS:]

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {e}")
            # Optionally add more robust error handling or logging

if __name__ == "__main__":
    main()