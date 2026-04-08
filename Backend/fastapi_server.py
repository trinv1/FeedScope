from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime, timezone, timedelta
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from bson import Binary
import json
import base64
import asyncio
import re
import hashlib
from rapidfuzz import fuzz
from passlib.context import CryptContext
import secrets


load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
PROCESSOR_ENABLED = os.getenv("PROCESSOR_ENABLED", "0") == "1"

MONGO_URI = os.getenv("MONGO_URI")

BATCH_SIZE = 10
BATCH_SLEEP_SEC = 60
IDLE_SLEEP_SEC = 3

client = MongoClient(MONGO_URI)
db = client["SocialMediaDB"]
tweets = db["tweets"]
studies = db["studies"]
subjects = db["subjects"]
phases = db["phases"]
captures = db["captures"]
users = db["users"]
sessions = db["sessions"]

#Creating indexes
users.create_index("email", unique=True, sparse=True)
tweets.create_index("tweet_hash", unique=True, sparse=True)
studies.create_index("study_id", unique=True, sparse=True)
subjects.create_index([("study_id", 1), ("subject_id", 1)], unique=True)
phases.create_index([("study_id", 1), ("phase_id", 1)], unique=True)
sessions.create_index([("owner_id", 1), ("study_id", 1), ("session_id", 1)], unique=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Defining passlib hashing algo
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#Posting email and password details to mongo for signup
@app.post("/signup")
def signup(
    email: str = Form(...),
    password: str = Form(...)
):
    hashed_password = pwd_context.hash(password)
    token = secrets.token_hex(32)

    doc = {
        "email": email,
        "password_hash": hashed_password,
        "auth_token": token,
        "created_at": datetime.now(timezone.utc),
    }

    result = users.insert_one(doc)
    return {"ok": True, "user_id": str(result.inserted_id), "email": email, "token": token}

#Posting login to mongo to verify user
@app.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...)
):
    user = users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not pwd_context.verify(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = secrets.token_hex(32)

    users.update_one(
        {"_id": user["_id"]},
        {"$set": {"auth_token": token}}
    )

    return {
        "ok": True,
        "user_id": str(user["_id"]),
        "email": user["email"],
        "token": token
    }

#Endpoint to change password for logged in user
@app.post("/change-password")
def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    authorization: str = Header("")
):
    user = get_current_user(authorization)

    #Check current password is correct
    if not pwd_context.verify(current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    #Check new passwords match
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")

    #Basic password validation
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")

    #Prevent reusing same password
    if pwd_context.verify(new_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    #Hash and store new password
    new_password_hash = pwd_context.hash(new_password)

    users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": new_password_hash}}
    )

    return {"ok": True, "message": "Password changed successfully"}

#Endpoint to request password reset
@app.post("/forgot-password")
def forgot_password(email: str = Form(...)):
    user = users.find_one({"email": email})

    #Always return same response so emails cannot be enumerated
    if not user:
        return {"ok": True, "message": "If that email exists, a reset token has been generated."}

    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "reset_token": reset_token,
                "reset_token_expires_at": expires_at
            }
        }
    )

    #just returning token directly right now
    return {
        "ok": True,
        "message": "Reset token generated",
        "reset_token": reset_token
    }

#Endpoint to reset password using reset token
@app.post("/reset-password")
def reset_password(
    email: str = Form(...),
    reset_token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    user = users.find_one({"email": email})

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or reset token")

    stored_token = user.get("reset_token")
    expires_at = user.get("reset_token_expires_at")

    if not stored_token or stored_token != reset_token:
        raise HTTPException(status_code=400, detail="Invalid email or reset token")

    if not expires_at:
        raise HTTPException(status_code=400, detail="Reset token has expired")

    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)

    if expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    new_password_hash = pwd_context.hash(new_password)
    new_auth_token = secrets.token_hex(32)

    users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_hash": new_password_hash,
                "auth_token": new_auth_token
            },
            "$unset": {
                "reset_token": "",
                "reset_token_expires_at": ""
            }
        }
    )

    return {"ok": True, "message": "Password reset successfully"}

#Get current user from token
def get_current_user(authorization: str = Header("")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "").strip()
    user = users.find_one({"auth_token": token})

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user

#Get current user
@app.get("/me")
def get_me(authorization: str = Header("")):
    user = get_current_user(authorization)
    return {
        "user_id": str(user["_id"]),
        "email": user["email"]
    }

#Get tweets of certain owner, study, subject and phase
@app.get("/tweets")
def get_tweets(
    study_id: str = "",
    subject_id: str = "",
    phase_id: str = "",
    session_id: str = "",
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])
    query = {"owner_id": owner_id}

    if study_id:
        query["study_id"] = study_id
    if subject_id:
        query["subject_id"] = subject_id
    if phase_id:
        query["phase_id"] = phase_id
    if session_id:
        query["session_id"] = session_id

    data = list(tweets.find(query, {"_id": 0}).sort("image_name", 1))
    return {"count": len(data), "tweets": data}

#Endpoint to post studies to mongo
@app.post("/studies")
def create_study(
    study_id: str = Form(...),
    name: str = Form(""),
    description: str = Form(""),
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    doc = {
        "owner_id": owner_id,
        "study_id": study_id,
        "name": name,
        "description": description,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    }
    result = studies.insert_one(doc)
    return {"ok": True, "id": str(result.inserted_id), "study_id": study_id}

#Endpoint to post subjects to mongo
@app.post("/subjects")
def create_subject(
    study_id: str = Form(...),
    subject_id: str = Form(...),
    label: str = Form(""),
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    doc = {
        "owner_id": owner_id,
        "study_id": study_id,
        "subject_id": subject_id,
        "label": label,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    }
    result = subjects.insert_one(doc)
    return {"ok": True, "id": str(result.inserted_id), "study_id": study_id, "subject_id": subject_id}

#Endpoint to post phases to mongo
@app.post("/phases")
def create_phase(
    study_id: str = Form(...),
    phase_id: str = Form(...),
    label: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    doc = {
        "owner_id": owner_id,
        "study_id": study_id,
        "phase_id": phase_id,
        "label": label,
        "start_date": start_date,
        "end_date": end_date,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    }
    result = phases.insert_one(doc)
    return {"ok": True, "id": str(result.inserted_id), "study_id": study_id, "phase_id": phase_id}

#Endpoint to post start of session to mongo
@app.post("/sessions/start")
def start_session(
    study_id: str = Form(...),
    subject_id: str = Form(""),
    phase_id: str = Form(""),
    session_id: str = Form(...),
    label: str = Form(""),
    authorization: str = Header("")
):    
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    doc = {
        "owner_id": owner_id,
        "study_id": study_id,
        "subject_id": subject_id,
        "phase_id": phase_id,
        "session_id": session_id,
        "label": label,
        "status": "active",
        "started_at": datetime.now(timezone.utc),
        "ended_at": None,
    }

    result = sessions.insert_one(doc)

    return {"ok": True, "id": str(result.inserted_id), "session_id": session_id, "status": "active",}

#Endpoint to post end of session to mongo
@app.post("/sessions/stop")
def stop_session(
    study_id: str = Form(...),
    session_id: str = Form(...),
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    result = sessions.update_one(
        {
            "owner_id": owner_id,
            "study_id": study_id,
            "session_id": session_id,
            "status": "active",
        },
        {
            "$set": {
                "status": "stopped",
                "ended_at": datetime.now(timezone.utc),
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Active session not found")

    return {"ok": True, "session_id": session_id, "status": "stopped"}

#Endpoint to get studies of certain owner
@app.get("/studies")
def get_studies(authorization: str = Header("")):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    data = list(studies.find({"owner_id": owner_id, "is_deleted": {"$ne": True}}, {"_id": 0}).sort("study_id", 1))
    return {"studies": data}

#Endpoint to get subjects of certain study and owner
@app.get("/subjects")
def get_subjects(study_id: str = "", authorization: str = Header("")):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    query = {"owner_id": owner_id, "is_deleted": {"$ne": True}}
    if study_id:
        query["study_id"] = study_id

    data = list(
        subjects.find(query, {"_id": 0}).sort("subject_id", 1)
    )
    return {"subjects": data}

#Endpoint to get phases of certain study and owner
@app.get("/phases")
def get_phases(study_id: str = "", authorization: str = Header(""), subject_id: str = ""):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])
    
    query = {"owner_id": owner_id, "is_deleted": {"$ne": True}}
    if study_id:
        query["study_id"] = study_id
    if subject_id:
        query["subject_id"] = subject_id

    data = list(
        phases.find(query, {"_id": 0}).sort("phase_id", 1)
    )
    return {"phases": data}

#Endpoint to get sessions 
@app.get("/sessions")
def get_sessions(
    study_id: str = "",
    subject_id: str = "",
    phase_id: str = "",
    status: str = "",
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])
    query = {"owner_id": owner_id, "is_deleted": {"$ne": True}}

    if study_id:
        query["study_id"] = study_id
    if subject_id:
        query["subject_id"] = subject_id
    if phase_id:
        query["phase_id"] = phase_id
    if status:
        query["status"] = status

    data = list(
        sessions.find(query, {"_id": 0}).sort("started_at", -1)
    )

    return {"sessions": data}

#Route to update studies
@app.put("/studies/{study_id}")
def update_study(
    study_id: str,
    name: str = Form(""),
    description: str = Form(""),
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    update_fields = {
        "name": name,
        "description": description,
        "updated_at": datetime.now(timezone.utc),
    }

    result = studies.update_one(
        {
            "owner_id": owner_id,
            "study_id": study_id,
            "is_deleted": {"$ne": True}
        },
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Study not found")

    return {"ok": True, "study_id": study_id}

#Route to update subjects
@app.put("/subjects/{subject_id}")
def update_subject(
    subject_id: str,
    study_id: str = Form(...),
    label: str = Form(""),
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    update_fields = {
        "label": label,
        "updated_at": datetime.now(timezone.utc),
    }

    result = subjects.update_one(
        {
            "owner_id": owner_id,
            "study_id": study_id,
            "subject_id": subject_id,
            "is_deleted": {"$ne": True}
        },
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Subject not found")

    return {"ok": True, "subject_id": subject_id}

#Route to update phases
@app.put("/phases/{phase_id}")
def update_phase(
    phase_id: str,
    study_id: str = Form(...),
    label: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    update_fields = {
        "label": label,
        "start_date": start_date,
        "end_date": end_date,
        "updated_at": datetime.now(timezone.utc),
    }

    result = phases.update_one(
        {
            "owner_id": owner_id,
            "study_id": study_id,
            "phase_id": phase_id,
            "is_deleted": {"$ne": True}
        },
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Phase not found")

    return {"ok": True, "phase_id": phase_id}

#Route to soft delete study
@app.delete("/studies/{study_id}")
def delete_study(
    study_id: str,
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    result = studies.update_one(
        {
            "owner_id": owner_id,
            "study_id": study_id,
            "is_deleted": {"$ne": True}
        },
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc)
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Study not found")

    return {"ok": True, "study_id": study_id, "deleted": True}

#Route to soft delete subject
@app.delete("/subjects/{subject_id}")
def delete_subject(
    subject_id: str,
    study_id: str,
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    result = subjects.update_one(
        {
            "owner_id": owner_id,
            "study_id": study_id,
            "subject_id": subject_id,
            "is_deleted": {"$ne": True}
        },
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc)
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Subject not found")

    return {"ok": True, "subject_id": subject_id, "deleted": True}

#Route to soft delete phases
@app.delete("/phases/{phase_id}")
def delete_phase(
    phase_id: str,
    study_id: str,
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    result = phases.update_one(
        {
            "owner_id": owner_id,
            "study_id": study_id,
            "phase_id": phase_id,
            "is_deleted": {"$ne": True}
        },
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc)
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Phase not found")

    return {"ok": True, "phase_id": phase_id, "deleted": True}

#Most common words found in a session
def top_words(owner_id="", study_id="", subject_id="", phase_id="", session_id="", limit=20):
    match_stage = {}

    if owner_id:
        match_stage["owner_id"] = owner_id
    if study_id:
        match_stage["study_id"] = study_id
    if subject_id:
        match_stage["subject_id"] = subject_id
    if phase_id:
        match_stage["phase_id"] = phase_id
    if session_id:
        match_stage["session_id"] = session_id

    pipeline = []

    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.extend([
        {
            "$project": {
                "words": {
                    "$split": [
                        {"$toLower": "$tweet"},
                        " "
                    ]
                }
            }
        },
        {"$unwind": "$words"},
        {
            "$match": {
                "words": {
                    "$nin": [
                        "", "there", "once", "one", "the", "and", "to", "of", "a", "in", "is", "for", "on", "movie", "-"
                        "that", "with", "as", "it", "this", "at", "by", "from", "be", "are", "more", "out", "all"
                        "was", "were", "will", "would", "should", "could", "an", "like", "not", "new", "am", "been",
                        "i", "you", "he", "she", "we", "they", "them", "his", "her", "people", "who", "real", "into",
                        "my", "your", "our", "their", "some", "can", "just", "every", "now", "she's", "time", "get",
                        "just", "have", "has", "had", "do", "does", "did", "when", "no", "after", "me", "what", "first",
                        "but", "if", "or", "so", "because", "about", "well", "years", "never" "life", "he's", "see"
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": "$words",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ])

    return list(tweets.aggregate(pipeline))

#Endpoint getting top words of that session
@app.get("/stats/top-words")
def get_top_words(
    study_id: str = "",
    subject_id: str = "",
    phase_id: str = "",
    session_id: str = "",
    limit: int = 20,
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    result = top_words(
        owner_id=owner_id,
        study_id=study_id,
        subject_id=subject_id,
        phase_id=phase_id,
        session_id=session_id,
        limit=limit
    )

    return {"words": result}

#Top topics of session
def top_topics(owner_id="", study_id="", subject_id="", phase_id="", session_id="", limit=10):
    match_stage = {}

    if owner_id:
        match_stage["owner_id"] = owner_id
    if study_id:
        match_stage["study_id"] = study_id
    if subject_id:
        match_stage["subject_id"] = subject_id
    if phase_id:
        match_stage["phase_id"] = phase_id
    if session_id:
        match_stage["session_id"] = session_id

    pipeline = []

    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.extend([
        {
            "$group": {
                "_id": "$sentiment.topic",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ])

    return list(tweets.aggregate(pipeline))

#Getting top topics of session
@app.get("/stats/top-topics")
def get_top_topics(
    study_id: str = "",
    subject_id: str = "",
    phase_id: str = "",
    session_id: str = "",
    limit: int = 10,
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    limit = min(max(limit, 1), 100)

    result = top_topics(
        owner_id=owner_id,
        study_id=study_id,
        subject_id=subject_id,
        phase_id=phase_id,
        session_id=session_id,
        limit=limit
    )

    return {"topics": result}

#Aggregating date a political leaning
def counts_by_date_and_leaning(owner_id ="", study_id="", subject_id="", phase_id="", session_id=""):
    match_stage = {}

    if owner_id:
        match_stage["owner_id"] = owner_id
    if study_id:
        match_stage["study_id"] = study_id
    if subject_id:
        match_stage["subject_id"] = subject_id
    if phase_id:
        match_stage["phase_id"] = phase_id
    if session_id:
        match_stage["session_id"] = session_id

    pipeline = []

    if match_stage:
        pipeline.append({"$match": match_stage})
    
    pipeline.extend([
        #Grouping by image name AND sentiment.political_leaning
        {
            "$group": {
                "_id": {
                    "date": "$image_name",
                    "leaning": "$sentiment.political_leaning"
                    },
                "count": {"$sum": 1}
            }
        },
        #Shaping output
        {
            "$project": {
                "_id": 0,
                "date": "$_id.date",
                "political_leaning": "$_id.leaning",
                "count": 1
            }
        },
        #Sorting by date 
        {"$sort": {"date": 1}}
    ])
    return list(tweets.aggregate(pipeline))

#Finding leaning of certain topics for accounts
def topic_by_leaning(owner_id="", study_id="", subject_id="", phase_id="", session_id="", limit=20):
    match_stage = {}

    if owner_id:
        match_stage["owner_id"] = owner_id
    if study_id:
        match_stage["study_id"] = study_id
    if subject_id:
        match_stage["subject_id"] = subject_id
    if phase_id:
        match_stage["phase_id"] = phase_id
    if session_id:
        match_stage["session_id"] = session_id

    pipeline = []

    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.extend([
        {
            "$match": {
                "sentiment": {"$exists": True},
                "sentiment.topic": {"$exists": True, "$ne": ""},
                "sentiment.political_leaning": {"$exists": True, "$ne": ""}
            }
        },
        {
            "$group": {
                "_id": {
                    "topic": "$sentiment.topic",
                    "leaning": "$sentiment.political_leaning"
                },
                "count": {"$sum": 1}
            }
        },
        {
            "$group": {
                "_id": "$_id.topic",
                "leanings": {
                    "$push": {
                        "political_leaning": "$_id.leaning",
                        "count": "$count"
                    }
                },
                "total": {"$sum": "$count"}
            }
        },
        {
            "$project": {
                "_id": 0,
                "topic": "$_id",
                "total": 1,
                "leanings": 1
            }
        },
        {"$sort": {"total": -1}},
        {"$limit": limit}
    ])

    return list(tweets.aggregate(pipeline))

#Getting topic by leaning stats
@app.get("/stats/topic-by-leaning")
def get_topic_by_leaning(
    study_id: str = "",
    subject_id: str = "",
    phase_id: str = "",
    session_id: str = "",
    limit: int = 20,
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    limit = min(max(limit, 1), 200)

    result = topic_by_leaning(
        owner_id=owner_id,
        study_id=study_id,
        subject_id=subject_id,
        phase_id=phase_id,
        session_id=session_id,
        limit=limit
    )

    return {"series": result}

#Political leaning stats endpoint
@app.get("/stats/political-leaning")
def political_leaning_stats(
    study_id: str = "",
    subject_id: str = "",
    phase_id: str = "",
    session_id: str = "",
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    result = counts_by_date_and_leaning(owner_id, study_id, subject_id, phase_id, session_id)
    return {"series": result}

os.makedirs("uploads", exist_ok=True)

#Endpoint to upload image
@app.post("/upload")
async def upload(
    image: UploadFile = File(...),
    tabId: str = Form(""),
    pageUrl: str = Form(""),
    ts: str = Form(""),
    studyId: str = Form(""),
    subjectId: str = Form(""),
    phaseId: str = Form(""),
    sessionId: str = Form(""),
    authorization: str = Header("")
):
    user = get_current_user(authorization)
    owner_id = str(user["_id"])

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image")

    doc = {
        "owner_id": owner_id,
        "filename": image.filename,
        "content_type": image.content_type,
        "image_bytes": Binary(data),
        "tab_id": tabId,
        "page_url": pageUrl,
        "ts": ts,
        "study_id": studyId,
        "subject_id": subjectId,
        "phase_id": phaseId,
        "session_id": sessionId,
        "created_at": datetime.now(timezone.utc),
        "status": "queued",
        "processed": False,
    }

    result = captures.insert_one(doc)
    return {
        "ok": True,
        "capture_id": str(result.inserted_id),
        "study_id": studyId,
        "subject_id": subjectId,
        "phase_id": phaseId,
        "session_id": sessionId,
        "status": "queued",
    }

#Endpoint to check server can see queued docs
@app.get("/debug/queue")
def debug_queue():
    q = list(captures.find({"status": "queued"}, {"image_bytes": 0, "_id": 0}).sort("created_at", 1).limit(5))
    return {"queued_sample": q, "queued_count": captures.count_documents({"status": "queued"})}

#Normalising tweets
def normalize_tweet_text(text):
    if not text:
        return ""

    text = text.lower().strip()
    text = text.replace("\n", " ")
    text = re.sub(r"http\S+", "", text)      #remove links
    text = re.sub(r"[^a-z0-9\s]", "", text)  #remove punctuation
    text = re.sub(r"\s+", " ", text).strip() #collapse repeated spaces
    return text

#Creating hash for tweet
def make_tweet_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

#Near duplicate checking for api mistakes
def similarity_score(a, b):
    return max(
        fuzz.ratio(a, b),
        fuzz.partial_ratio(a, b),
        fuzz.token_sort_ratio(a, b),
        fuzz.token_set_ratio(a, b),
    )

#Helper function to process one captured image
def process_one_capture(doc):
    #Get image bytes from mongo document
    image_bytes = doc["image_bytes"]
    content_type = doc.get("content_type", "image/jpeg")

    #Convert image bytes to base64 for OpenAI input
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    #Calling API and creating chat completion request
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a Twitter/X screenshot parser. "
                    "Extract ALL clearly visible main-feed posts from the central feed only. "
                    "Return ONLY valid JSON. No markdown, no backticks, no explanations.\n\n"

                    "Important context rules:\n"
                    "- Detect whether each visible post is an original tweet, repost/retweet, quote tweet, reply, or unclear.\n"
                    "- If the screenshot shows that a user reposted someone else's content, capture BOTH the reposting user's context and the original visible content.\n"
                    "- If the screenshot shows a quote tweet, capture BOTH the quoting text and the quoted/original tweet text.\n"
                    "- If the screenshot shows a reply and the parent tweet is visible, capture the reply text and the parent tweet text.\n"
                    "- If referenced content is not visible, leave it as an empty string.\n"
                    "- Do not invent hidden or cropped text.\n"
                    "- Ignore ads, promoted posts, sidebars, trends, menus, and interface text.\n"
                    "- Ignore partial posts if too little is visible to identify them reliably.\n"
                    "- Preserve top-to-bottom order.\n\n"

                    "For each visible post return:\n"
                    "- username\n"
                    "- display_name\n"
                    "- post_type\n"
                    "- actor_commentary\n"
                    "- referenced_username\n"
                    "- referenced_display_name\n"
                    "- referenced_post_text\n"
                    "- relationship_to_referenced_post\n"
                    "- full_visible_meaning\n"
                    "- likes\n"
                    "- retweets\n\n"

                    "Definitions:\n"
                    "- original: a standalone post by the visible account\n"
                    "- retweet: repost of another post without substantial added text\n"
                    "- quote_tweet: repost with added commentary\n"
                    "- reply: response to another post\n"
                    "- thread_post: post that is part of a visible thread\n"
                    "- unclear: cannot determine reliably\n\n"

                    "relationship_to_referenced_post meanings:\n"
                    "- endorses: visible user appears to agree with or support referenced content\n"
                    "- criticises: visible user appears to disagree with or attack referenced content\n"
                    "- shares_without_clear_stance: referenced content is shared but endorsement is not clear\n"
                    "- unclear: cannot determine\n\n"

                    "Return JSON in exactly this format:\n"
                    "{\n"
                    "  \"tweets\": [\n"
                    "    {\n"
                    "      \"username\": \"\",\n"
                    "      \"display_name\": \"\",\n"
                    "      \"post_type\": \"original | retweet | quote_tweet | reply | thread_post | unclear\",\n"
                    "      \"actor_commentary\": \"\",\n"
                    "      \"referenced_username\": \"\",\n"
                    "      \"referenced_display_name\": \"\",\n"
                    "      \"referenced_post_text\": \"\",\n"
                    "      \"relationship_to_referenced_post\": \"endorses | criticises | shares_without_clear_stance | unclear\",\n"
                    "      \"full_visible_meaning\": \"\",\n"
                    "      \"likes\": \"\",\n"
                    "      \"retweets\": \"\"\n"
                    "    }\n"
                    "  ]\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract all visible main-feed posts from this screenshot. "
                            "For each item, determine whether it is an original post, retweet/repost, "
                            "quote tweet, reply, thread post, or unclear. "
                            "Where visible, include both the user's own commentary and any referenced/original post text. "
                            "If a user appears to be agreeing with, criticising, or neutrally sharing referenced content, record that. "

                            "CRITICAL RULE: "
                            "Do NOT summarise, interpret, or describe the content. "
                            "Do NOT write sentences like 'The user retweeted...' or 'This post is about...'. "
                            "ONLY extract text that is directly visible in the screenshot. "
                            "actor_commentary must be the exact visible text written by the user. "
                            "referenced_post_text must be the exact visible text of the original or quoted tweet. "
                            "full_visible_meaning must be a direct concatenation of actor_commentary and referenced_post_text, not a summary. "
                            "If there is no visible text for a field, return an empty string. "
                            "If you are unsure, return an empty string instead of guessing. "

                            "Return ONLY valid JSON."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{content_type};base64,{image_b64}"
                        }
                    }
                ]
            }
        ]
    )

    #Extracting model output (JSON string)
    json_output = response.choices[0].message.content

    #Parsing JSON returned by model
    parsed = json.loads(json_output)
    parsed_tweets = parsed.get("tweets", [])

    #Choosing destination collection
    collection = db["tweets"]

    if not parsed_tweets:
        captures.update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": "done", "note": "No tweets extracted"}}
        )
        return []

    #Checking if tweets are duplicates and saving to mongo
    for item in parsed_tweets:
        tweet_text = (
            (item.get("actor_commentary") or "") + " " +
            (item.get("referenced_post_text") or "")
        ).strip()
        tweet_normalized = normalize_tweet_text(tweet_text)
        tweet_hash = make_tweet_hash(tweet_normalized)

        existing = collection.find_one({"tweet_hash": tweet_hash})
        if existing:
            continue

        candidates = collection.find({
            "username": item.get("username", ""),
            "tweet_normalized": {"$exists": True}
        }).limit(20)

        is_duplicate = False
        for candidate in candidates:
            score = similarity_score(tweet_normalized, candidate.get("tweet_normalized", ""))
            if score >= 94:
                is_duplicate = True
                break

        if is_duplicate:
            continue

        collection.insert_one({
            "owner_id": doc.get("owner_id", ""),
            "study_id": doc.get("study_id", ""),
            "subject_id": doc.get("subject_id", ""),
            "phase_id": doc.get("phase_id", ""),
            "session_id": doc.get("session_id", ""),
            "capture_id": str(doc["_id"]),
            "image_name": datetime.now().strftime("%d-%m-%Y"),

            "username": item.get("username", ""),
            "display_name": item.get("display_name", ""),

            #Main text field
            "tweet": tweet_text,

            #Context fields
            "post_type": item.get("post_type", "unclear"),
            "actor_commentary": item.get("actor_commentary", ""),
            "referenced_username": item.get("referenced_username", ""),
            "referenced_display_name": item.get("referenced_display_name", ""),
            "referenced_post_text": item.get("referenced_post_text", ""),
            "relationship_to_referenced_post": item.get("relationship_to_referenced_post", "unclear"),
            "full_visible_meaning": tweet_text,
            
            #Normalisation
            "tweet_normalized": tweet_normalized,
            "tweet_hash": tweet_hash,

            "likes": item.get("likes", ""),
            "retweets": item.get("retweets", ""),
    })

    #Mark original capture as processed
    captures.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "done", "processed_at": datetime.now(timezone.utc)}}
    )

    return parsed

def process_one_sentiment(collection, doc):

    #Getting tweet from document
    context_text = f"""
    username: {doc.get('username', '')}
    display_name: {doc.get('display_name', '')}
    post_type: {doc.get('post_type', '')}
    actor_commentary: {doc.get('actor_commentary', '')}
    referenced_username: {doc.get('referenced_username', '')}
    referenced_display_name: {doc.get('referenced_display_name', '')}
    referenced_post_text: {doc.get('referenced_post_text', '')}
    relationship_to_referenced_post: {doc.get('relationship_to_referenced_post', '')}
    full_visible_meaning: {doc.get('full_visible_meaning') or doc.get('actor_commentary', '')}
    """

    #Calling API and creating chat completion request
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                    "content": (
                        "You are a sentiment and political-alignment classifier for Twitter/X posts. "
                        "Classify the OVERALL expressed stance of the visible post using all provided context. "
                        "This includes whether the post is an original post, retweet, quote tweet, or reply, "
                        "and whether the visible user appears to endorse, criticise, or neutrally share referenced content.\n\n"

                        "Core rule:\n"
                        "- Do NOT classify based only on the referenced post text.\n"
                        "- Do NOT classify based only on the user's short commentary.\n"
                        "- Classify the combined visible meaning from all available context.\n"
                        "- If a user reposts or quote-tweets content approvingly, the referenced content should influence classification strongly.\n"
                        "- If a user reposts or quote-tweets content critically, classify according to the user's overall stance, not the referenced author's stance.\n"
                        "- If stance toward referenced content is unclear, use 'unclear' unless the user's own commentary is sufficient.\n\n"

                        "Political alignment categories:\n"
                        "- left: progressive, redistributive, egalitarian, structural/systemic framing\n"
                        "- right: conservative, nationalist, sovereignty/border/tradition/free-market framing\n"
                        "- centre: mixed, moderate, pragmatic, cross-ideological\n"
                        "- apolitical: no meaningful political content\n"
                        "- unclear: not enough evidence or conflicting signals\n\n"

                        "Output JSON format:\n"
                        "{\n"
                        "  \"emotional_valence\": \"positive | neutral | negative | serious\",\n"
                        "  \"emotion_intensity\": 0.0,\n"
                        "  \"moral_stance\": \"supportive | condemning | informative | neutral | sarcastic\",\n"
                        "  \"political_leaning\": \"left | right | centre | apolitical | unclear\",\n"
                        "  \"is_toxic\": true,\n"
                        "  \"topic\": \"short neutral topic\",\n"
                        "  \"stance_reason\": \"short explanation of how the overall stance was inferred\"\n"
                        "}"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Classify this Twitter/X post using all context below.\n\n"
                            f"{context_text}\n\n"
                            "Return JSON only."
                        )
                    }
                ]
            }
        ]
    )

    #Extracting model output (JSON string)
    sentiment = json.loads(response.choices[0].message.content)

    #Updating docs in mongo with sentiment
    collection.update_one(
    {"_id": doc["_id"]},
    {"$set": {"sentiment": sentiment}}
)
    return sentiment

#Background worker that keeps processing docs
async def processing_worker():
    while True:
        capture_batch = list(captures.find({"status": "queued"}).sort("created_at", 1).limit(BATCH_SIZE))
        batch = list(tweets.find({"sentiment": {"$exists": False}}).limit(BATCH_SIZE))

        #Captures first
        if capture_batch:
            processed = 0
            failed = 0

            for doc in capture_batch:
                try:
                    await asyncio.to_thread(process_one_capture, doc)
                    processed += 1
                except Exception as e:
                    failed += 1
                    captures.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"status": "error", "error": str(e)}}
                    )

            await asyncio.sleep(BATCH_SLEEP_SEC)
            continue
                
        #Performs sentiment analysis when captures is empty
        if batch:
            processed = 0
            failed = 0

            for doc in batch:
                    await asyncio.to_thread(process_one_sentiment, tweets, doc)
                    processed += 1

            await asyncio.sleep(BATCH_SLEEP_SEC)
            continue

        #Nothing to do
        await asyncio.sleep(IDLE_SLEEP_SEC)

#Launching when app starts
@app.on_event("startup")
async def start_background_worker():
    asyncio.create_task(processing_worker())

