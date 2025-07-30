from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

uri = os.getenv("MONGODB_URI")
print("Connecting to MongoDB...")

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)  # 5s timeout
    # Force a connection check
    client.admin.command("ping")
    print("✅ Successfully connected to MongoDB Atlas!")
    print("Available databases:", client.list_database_names())
except Exception as e:
    print("❌ Connection failed:", e)
