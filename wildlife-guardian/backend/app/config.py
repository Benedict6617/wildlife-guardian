import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "Wildlife Guardian"
API_VERSION = "1.0.0"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
