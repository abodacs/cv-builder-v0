import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    # Redis Configuration
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_TTL = int(os.getenv("REDIS_TTL", "3600"))  # 1 hour default

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-mini")

    # PDF Configuration
    STATIC_DIR = "static"
    PDF_ARABIC_FONT = "Amiri-Regular.ttf"

    # Static files configuration
    STATIC_DIR = "static"
    FONTS_DIR = os.path.join(STATIC_DIR, "fonts")
    ARABIC_FONT_PATH = os.path.join(FONTS_DIR, "Amiri-Regular.ttf")
