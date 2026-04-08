from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["SocialMediaDB"]
tweets = db["tweets"]

result = tweets.delete_many({
    "phase_id": "5"
})

print(f"Deleted {result.deleted_count} documents.")