import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
HEADLESS = os.getenv("HEADLESS", "False") == "True"
