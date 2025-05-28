import os

# --- Načtení klíčů z env vars ---
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT", "us-east-1")
PINECONE_ENV = PINECONE_ENVIRONMENT
INDEX_NAME = os.environ.get("INDEX_NAME", "winston-memory")
INDEX_DIMENSION = int(os.environ.get("INDEX_DIMENSION", 1536))
INDEX_METRIC = os.environ.get("INDEX_METRIC", "cosine")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")