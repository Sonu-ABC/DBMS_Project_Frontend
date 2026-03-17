# backend/db.py – MongoDB connection utility
import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

# Load .env from the backend folder
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)

_client = None


def get_client():
    """Return a cached MongoClient instance."""
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI not set – check backend/.env")
        _client = MongoClient(uri)
    return _client


def get_db():
    """Return the pymongo Database for Module A6."""
    db_name = os.getenv("MONGODB_DB_NAME", "a6_clinical_alerts")
    return get_client()[db_name]
