"""
Ollama API client for generating responses.
"""

import json
import requests
from config import OLLAMA_API_URL, OLLAMA_MODEL, OLLAMA_REQUEST_TIMEOUT, HISTORY_ENABLED


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
You are a factual assistant tasked with summarizing YouTube content. Based STRICTLY on the following YouTube video transcript and metadata, provide a detailed summary of the video.
If the transcript is in a language other than English, it has been automatically translated.

IMPORTANT INSTRUCTIONS:
1. ONLY use information explicitly stated in the provided transcript and metadata
2. DO NOT make up or hallucinate any information not present in the transcript
3. If the transcript is unclear or incomplete, acknowledge these limitations
4. Organize your summary to follow the logical structure of the video
5. Include specific details, quotes, and examples from the transcript to support your summary

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

FACTUAL SUMMARY:
"""
    else:
        # Improved regular prompt with stronger factuality constraints
        prompt = f"""
You are a factual assistant. Based STRICTLY on the following context and conversation history (if provided), provide a comprehensive answer to the user's query.

IMPORTANT INSTRUCTIONS:
1. ONLY use information explicitly stated in the context below
2. DO NOT use any prior knowledge or information not present in the context
3. If the context doesn't contain enough information to answer the query, state "Based on the provided information, I don't have enough details to answer this question fully" and explain what specific information is missing
4. DO NOT make up or hallucinate any information not present in the context
5. When citing facts, refer to specific parts of the context
6. If different sources in the context provide conflicting information, acknowledge this and present both perspectives
7. Maintain a neutral, factual tone throughout your response

{history_text}CONTEXT:
---
{context}
---

USER QUERY: {query}

FACTUAL ANSWER:
"""
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True, # Enable streaming
        "temperature": 0.3,  # Reduced temperature for more factual responses
        "num_predict": 2048  # Encourage longer responses
    }
    headers = {'Content-Type': 'application/json'}

    response = None  # Initialize response variable outside the try block
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
            if response:  # Check if response exists before accessing it
                print(f"[DEBUG] Ollama Error Response Body: {response.text}")
        except:
            pass
        raise e
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during Ollama streaming setup: {e}")
        raise e