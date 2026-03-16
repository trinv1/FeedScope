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
girltwitter = db["girltwitter"]
boytwitter = db["boytwitter"]
captures = db["captures"]

boytwitter.create_index("tweet_hash", unique=True, sparse=True)
girltwitter.create_index("tweet_hash", unique=True, sparse=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Getting all tweets from boy account
@app.get("/tweets/boy")
def get_boy_tweets():
    data = list(boytwitter.find({}, {"_id": 0}))
    return {"count": len(data), "tweets": data}

#Getting all tweets from girl account
@app.get("/tweets/girl")
def get_girl_tweets():
    data = list(girltwitter.find({}, {"_id": 0}))
    return {"count": len(data), "tweets": data}

#Aggregating dates and political leaning
def counts_by_date_and_leaning(collection):
    pipeline = [
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
    ]
    return list(collection.aggregate(pipeline))

@app.get("/stats/boy/political-leaning")
def boy_stats():
    result = counts_by_date_and_leaning(boytwitter)
    print("Boy stats:")
    for r in result:
        print(r)
    return {"series": result}

@app.get("/stats/girl/political-leaning")
def girl_stats():
    result = counts_by_date_and_leaning(girltwitter)
    print("Girl stats:")
    for r in result:
        print(r)
    return {"series": result}

os.makedirs("uploads", exist_ok=True)

#Endpoint to upload image
@app.post("/upload")
async def upload(
    image: UploadFile = File(...),
    tabId: str = Form(""),
    pageUrl: str = Form(""),
    ts: str = Form(""),
    account: str = Form(""),  
):
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image")

    image_name = image.filename or f"{ts or int(datetime.now().timestamp())}.jpg"

    doc = {
        "created_at": datetime.now(timezone.utc),
        "image_name": image_name,
        "tabId": tabId,
        "pageUrl": pageUrl,
        "ts": ts,
        "account": account,
        "content_type": image.content_type or "image/jpeg",
        "image_bytes": Binary(data),
        "status": "queued",
        "tries": 0
    }

    ins = captures.insert_one(doc)
    return {"ok": True, "id": str(ins.inserted_id)}

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
    tweets = parsed.get("tweets", [])

    #Choosing destination collection
    account = (doc.get("account") or "").lower()
    if account == "boy":
        collection = boytwitter
    elif account == "girl":
        collection = girltwitter
    else:
        collection = db["parsedtweets"]

    #If tweet doesnt exist dont save
    if not tweets:
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
        girl_batch = list(girltwitter.find({"sentiment": {"$exists": False}}).limit(BATCH_SIZE))
        boy_batch = list(boytwitter.find({"sentiment": {"$exists": False}}).limit(BATCH_SIZE))

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
        if girl_batch:
            processed = 0
            failed = 0

            for doc in girl_batch:
                    await asyncio.to_thread(process_one_sentiment, girltwitter, doc)
                    processed += 1

            await asyncio.sleep(BATCH_SLEEP_SEC)
            continue

        #Performs boy sentiment analysis when girl is empty
        if boy_batch:
            processed = 0
            failed = 0

            for doc in boy_batch:
                    await asyncio.to_thread(process_one_sentiment, boytwitter, doc)
                    processed += 1

            await asyncio.sleep(BATCH_SLEEP_SEC)
            continue

        #Nothing to do
        await asyncio.sleep(IDLE_SLEEP_SEC)

#Launching when app starts
@app.on_event("startup")
async def start_background_worker():
    asyncio.create_task(processing_worker())
