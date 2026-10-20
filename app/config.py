import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./travel_planner.db")
SECRET_KEY: str = os.getenv("SECRET_KEY", "college_advanced_python_secret_key_change_in_production_2026")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# External Experience Finder API configuration
# Reads EXPERIENCE_FINDER_API_URL with backwards compatibility to EXPERIENCE_API_URL
EXPERIENCE_FINDER_API_URL: str = (
    os.getenv("EXPERIENCE_FINDER_API_URL")
    or os.getenv("EXPERIENCE_API_URL")
    or "http://localhost:8001"
).rstrip("/")
EXPERIENCE_API_URL: str = EXPERIENCE_FINDER_API_URL

# Server-to-Server Integration Credentials for Experience Finder
# Never expose this credential in frontend code
INTEGRATION_API_KEY: str = os.getenv("INTEGRATION_API_KEY", "st_partner_secret_key_2026")

# Permitted demo trip IDs accessible via partner reverse integration
DEMO_PERMITTED_TRIP_IDS = [
    int(x.strip()) for x in os.getenv("DEMO_PERMITTED_TRIP_IDS", "101,102").split(",") if x.strip().isdigit()
]

