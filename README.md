# PerPlexity Local

A local implementation of a Perplexity-like search and answer tool that uses DuckDuckGo for web searches and Ollama for local LLM-powered answer synthesis.

## Features

- **Web Search**: Uses DuckDuckGo to search the web for relevant information
- **Content Extraction**: Intelligently extracts and processes content from web pages
- **YouTube Support**: Extracts and processes transcripts from YouTube videos
- **Local LLM Integration**: Uses Ollama for local, private answer generation
- **Conversation History**: Maintains context across multiple queries
- **Streaming Responses**: Displays AI responses in real-time as they're generated

## Requirements

- Python 3.6+
- Ollama installed and running locally
- Internet connection for web searches

## Dependencies

```
requests
beautifulsoup4
duckduckgo_search
youtube-transcript-api (optional, for YouTube transcript extraction)
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/PerPlexity_Local.git
cd PerPlexity_Local
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install requests beautifulsoup4 duckduckgo_search
```

4. For YouTube transcript support (optional):
```bash
pip install youtube-transcript-api
```

5. Install and start Ollama:
   - Follow the instructions at [Ollama's official website](https://ollama.ai/) to install
   - Pull the model you want to use: `ollama pull dolphin-phi`

## Configuration

The main configuration options are at the top of `main.py`:

- `MAX_RESULTS`: Number of search results to process (default: 5)
- `REQUEST_TIMEOUT`: Timeout for web requests in seconds (default: 4)
- `MAX_LEN_PER_SOURCE`: Maximum text length to extract from each source (default: 20000)
- `OLLAMA_API_URL`: URL for the Ollama API (default: "http://localhost:11434/api/generate")
- `OLLAMA_MODEL`: The Ollama model to use (default: "dolphin-phi:latest")
- `OLLAMA_REQUEST_TIMEOUT`: Timeout for Ollama requests in seconds (default: 120)
- `MAX_HISTORY_TURNS`: Number of conversation turns to remember (default: 3)
- `HISTORY_ENABLED`: Whether to use conversation history (default: True)

## Usage

Run the program:

```bash
python main.py
```

### Commands

- Enter your query at the prompt
- Type `exit` to quit the program
- Type `clear history` to clear conversation history
- Type `toggle history` to enable/disable conversation history

### YouTube Support

You can include a YouTube URL in your query to get a summary of the video:

```
Query: Summarize this video https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## How It Works

1. **Search**: The program searches the web using DuckDuckGo or processes a YouTube URL
2. **Extract**: It extracts and processes content from the search results
3. **Synthesize**: The extracted content is sent to Ollama for answer generation
4. **Display**: The answer is displayed in real-time as it's generated

## Limitations

- Depends on DuckDuckGo's search API which may change
- YouTube transcript extraction requires the video to have captions
- Limited by the capabilities of the local LLM model used with Ollama
- Web content extraction may not work perfectly on all websites

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

        