from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from bson import Binary
import json
import base64
import asyncio
import re
import hashlib
from rapidfuzz import fuzz

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

tweets.create_index("tweet_hash", unique=True, sparse=True)
studies.create_index("study_id", unique=True, sparse=True)
subjects.create_index([("study_id", 1), ("subject_id", 1)], unique=True)
phases.create_index([("study_id", 1), ("phase_id", 1)], unique=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Tweets endpoint
@app.get("/tweets")
def get_tweets(
    study_id: str = "",
    subject_id: str = "",
    phase_id: str = "",
    session_id: str = "",
):
    query = {}

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
    description: str = Form("")
):
    doc = {
        "study_id": study_id,
        "name": name,
        "description": description,
        "created_at": datetime.now(timezone.utc),
    }
    result = studies.insert_one(doc)
    return {"ok": True, "id": str(result.inserted_id), "study_id": study_id}

#Endpoint to post subjects to mongo
@app.post("/subjects")
def create_subject(
    study_id: str = Form(...),
    subject_id: str = Form(...),
    label: str = Form("")
):
    doc = {
        "study_id": study_id,
        "subject_id": subject_id,
        "label": label,
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
    end_date: str = Form("")
):
    doc = {
        "study_id": study_id,
        "phase_id": phase_id,
        "label": label,
        "start_date": start_date,
        "end_date": end_date,
        "created_at": datetime.now(timezone.utc),
    }
    result = phases.insert_one(doc)
    return {"ok": True, "id": str(result.inserted_id), "study_id": study_id, "phase_id": phase_id}

#Endpoint to get studies 
@app.get("/studies")
def get_studies():
    data = list(
        studies.find({}, {"_id": 0}).sort("study_id", 1)
    )
    return {"studies": data}

#Endpoint to get subjects of certain study
@app.get("/subjects")
def get_subjects(study_id: str = ""):
    query = {}
    if study_id:
        query["study_id"] = study_id

    data = list(
        subjects.find(query, {"_id": 0}).sort("subject_id", 1)
    )
    return {"subjects": data}

#Endpoint to get phases of certain study 
@app.get("/phases")
def get_phases(study_id: str = ""):
    query = {}
    if study_id:
        query["study_id"] = study_id

    data = list(
        phases.find(query, {"_id": 0}).sort("phase_id", 1)
    )
    return {"phases": data}

#Endpoint to get sessions 
@app.get("/sessions")
def get_sessions(study_id: str = "", subject_id: str = "", phase_id: str = ""):
    query = {"session_id": {"$ne": ""}}
    if study_id:
        query["study_id"] = study_id
    if subject_id:
        query["subject_id"] = subject_id
    if phase_id:
        query["phase_id"] = phase_id
    sessions = tweets.distinct("session_id", query)
    return {"sessions": sorted(sessions)}

#Aggregating date a political leaning
def counts_by_date_and_leaning(study_id="", subject_id="", phase_id="", session_id=""):
    match_stage = {}

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

#Political leaning stats endpoint
@app.get("/stats/political-leaning")
def political_leaning_stats(
    study_id: str = "",
    subject_id: str = "",
    phase_id: str = "",
    session_id: str = "",
):
    result = counts_by_date_and_leaning(study_id, subject_id, phase_id, session_id)
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
):
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image")

    doc = {
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
                "Your job is to extract ALL clearly visible main-feed tweets from the screenshot. "
                "Return ONLY valid JSON. No markdown, no backticks, no explanations.\n"
                "Rules:\n"
                "- Return ONLY valid JSON.\n"
                "- Ignore ads, promoted posts, sponsored content, and anything labelled 'Promoted'.\n"
                "- Ignore sidebars, trends, menus, buttons, search bars, notifications, and any non-feed UI text.\n"
                "- Ignore partial tweets if too little is visible to identify the tweet reliably.\n"
                "- If multiple feed tweets are visible, include all of them in top-to-bottom order.\n"
                "- Do not invent missing values. Use empty strings if a field is not visible.\n"
                "Return JSON in exactly this format:\n"
                "{\n"
                "  \"tweets\": [\n"
                "    {\n"
                "      \"username\": \"\",\n"
                "      \"display_name\": \"\",\n"
                "      \"tweet\": \"\",\n"
                "      \"likes\": \"\",\n"
                "      \"retweets\": \"\",\n"
                "    }\n"
                "  ]\n"
                "}\n"
            )
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Extract all visible main-feed tweets from this screenshot. "
                        "Include only real tweets visible in the central feed. "
                        "Do not include promoted posts, ads, sponsored content, or anything marked 'Promoted'. "
                        "Do not include sidebar content or interface text. "
                        "For each visible tweet, extract:\n"
                        "- username (@handle)\n"
                        "- display_name\n"
                        "- tweet text\n"
                        "- likes count\n"
                        "- retweets count\n"
                        "Return all tweets in top-to-bottom order. "
                        "Return ONLY valid JSON in the required format."
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

    #If tweet doesnt exist dont save
    if item in  parsed_tweets:
        captures.update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": "done", "note": "No tweets extracted"}}
        )
        return []

    #Checking if tweets are duplicates and saving to mongo
    for item in tweets:
        tweet_text = item.get("tweet", "")
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
            "study_id": doc.get("study_id", ""),
            "subject_id": doc.get("subject_id", ""),
            "phase_id": doc.get("phase_id", ""),
            "session_id": doc.get("session_id", ""),
            "capture_id": str(doc["_id"]),
            "image_name": datetime.now().strftime("%d-%m-%Y"),
            "username": item.get("username", ""),
            "display_name": item.get("display_name", ""),
            "tweet": item.get("tweet", ""),
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
    tweet_text = doc["tweet"]

    #Calling API and creating chat completion request
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a sentiment and political-alignment classifier. "
                    "Classify content based ONLY on language, framing, and expressed positions. "
                    "Do not apply moral judgment or assume correctness of any viewpoint. "

                    "LEFT-LEANING: "
                    "- emphasizes collective responsibility, systemic or structural explanations; "
                    "- focuses on equality, redistribution, or group-level outcomes; "
                    "- supports expanded government, regulation, or institutional intervention; "
                    "- uses framing aligned with progressive, socialist, or egalitarian traditions. "

                    "RIGHT-LEANING: "
                    "- emphasizes individual responsibility, national identity, or cultural continuity; "
                    "- focuses on sovereignty, borders, security, tradition, or market outcomes; "
                    "- supports limited government, enforcement, or established institutions; "
                    "- uses framing aligned with conservative, nationalist, or free-market traditions. "

                    "CENTRIST / MODERATE: "
                    "- balances or mixes left and right framing; "
                    "- focuses on pragmatism, trade-offs, or incremental change; "
                    "- avoids strong ideological or absolutist language. "

                    "APOLITICAL: "
                    "- contains no political claims, advocacy, or ideological framing; "
                    "- topics such as sports, entertainment, personal anecdotes, or non-political news. "

                    "UNCLEAR: "
                    "- insufficient or ambiguous information to infer political alignment. "

                    "Rules: "
                    "- Political alignment is inferred from the text itself, including both explicit ideological statements and implicit political signaling."
                    "- Implicit political signaling includes framing, narratives, or language commonly associated with contemporary political factions, even if no policy or ideology is explicitly stated."
                    "- Criticism of governments, religions, cultures, or ideologies is NOT inherently hateful."
                    "- Emotional tone and toxicity are independent of political alignment. "
                    "- Do not infer intent beyond the provided text. "

                    "Output JSON format:\n"
                    "{\n"
                    "  \"emotional_valence\": \"positive | neutral | negative | serious\",\n"
                    "  \"emotion_intensity\": 0.0 to 1.0,\n"
                    "  \"moral_stance\": \"supportive | condemning | informative | neutral | sarcastic\",\n"
                    "  \"political_leaning\": \"left | right | centre | apolitical | unclear\",\n"
                    "  \"is_toxic\": true | false,\n"
                    "  \"topic\": \"short neutral topic\"\n"
                    "}\n"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Tweet: {tweet_text}\n\nAnalyse the sentiment and return JSON only."
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
