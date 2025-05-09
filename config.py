"""
Configuration settings for the PerPlexity Local application.
"""

# Web request settings
MAX_RESULTS = 5
REQUEST_TIMEOUT = 4  # seconds
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
MAX_LEN_PER_SOURCE = 20000

# Ollama configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "deepseek-r1:1.5b"
OLLAMA_REQUEST_TIMEOUT = 120  # seconds

# Context preservation configuration
MAX_HISTORY_TURNS = 3  # Number of previous turns to keep in context
HISTORY_ENABLED = True  # Toggle for enabling/disabling history