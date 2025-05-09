"""
PerPlexity Local - A local web search and AI response generation tool.
"""

import sys
from config import MAX_HISTORY_TURNS, HISTORY_ENABLED
from youtube_utils import extract_youtube_video_id
from web_extractor import fetch_and_extract_text
from ollama_client import synthesize_with_ollama_stream
from search_engine import perform_web_search, extract_youtube_url


def perform_search_and_synthesis(query: str, conversation_history=None):
    """
    Handles the core logic: Search, Extract, Synthesize (streaming), Print.
    """
    print(f"\n[INFO] Received query: {query}")
    
    # Extract YouTube URL from anywhere in the query
    youtube_url, query = extract_youtube_url(query)
    
    if youtube_url:
        print(f"[INFO] YouTube URL detected in query: {youtube_url}")
        search_results = [youtube_url]  # Use the YouTube URL as the only search result
        print(f"[INFO] Updated query for YouTube video: {query}")
    else:
        # Regular web search
        print("[INFO] Searching web using DuckDuckGo...")
        search_results = perform_web_search(query)
        if not search_results:
            return None

    # Fetch and extract content from search results
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
        return None

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
    return full_response


def main():
    global HISTORY_ENABLED
    """
    Main function to run the query loop.
    """
    print("Local Perplexity-like Search Tool")
    print("Enter your query below, or type 'exit' to quit.")
    print(f"Context preservation is {'ENABLED' if HISTORY_ENABLED else 'DISABLED'}")
    
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


if __name__ == "__main__":
    main()