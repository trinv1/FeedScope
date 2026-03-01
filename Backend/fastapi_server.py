from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os, traceback, time
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from bson import Binary
import json
import base64
import asyncio

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
PROCESSOR_ENABLED = os.getenv("PROCESSOR_ENABLED", "0") == "1"

MONGO_URI = os.getenv("MONGO_URI")

BATCH_SIZE = 5
BATCH_SLEEP_SEC = 60
IDLE_SLEEP_SEC = 3

client = MongoClient(MONGO_URI)
db = client["SocialMediaDB"]
girltwitter = db["girltwitter"]
boytwitter = db["boytwitter"]
captures = db["captures"]

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
        #Creating "date_str" field from image_name and removing .png
        {
            "$addFields": {
                "date_str": {
                    "$replaceAll": {
                        "input": "$image_name",
                        "find": ".png",
                        "replacement": ""
                    }
                }
            }
        },
        #Grouping by date_str AND sentiment.political_leaning
        {
            "$group": {
                "_id": {
                    "date": "$date_str",
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
                    "You are a Twitter screenshot parser. "
                    "Extract ONLY the FIRST main tweet visible in the screenshot. "
                    "Return ONLY valid JSON. No markdown, no backticks, no explanations.\n"
                    "{\n"
                    "  \"username\": \"\",\n"
                    "  \"display_name\": \"\",\n"
                    "  \"tweet\": \"\",\n"
                    "  \"likes\": \"\",\n"
                    "  \"retweets\": \"\",\n"
                    "  \"replies\": \"\"\n"
                    "}\n"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract all visible information for ONLY the first main tweet. "
                            "Do NOT include replies unless they are part of the first tweet. "
                            "Required fields:\n"
                            "- username (@handle)\n"
                            "- display_name\n"
                            "- tweet text\n"
                            "- likes count\n"
                            "- retweets count\n"
                            "Return ONLY valid JSON. No extra text."
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

    #Choosing destination collection
    account = (doc.get("account") or "").lower()
    if account == "boy":
        collection = boytwitter
    elif account == "girl":
        collection = girltwitter
    else:
        collection = db["parsedtweets"]

     #Saving parsed tweet to Mongo
    collection.insert_one({
    "image_name": datetime.now().strftime("%d-%m-%Y"),
    "username": parsed.get("username", ""),
    "display_name": parsed.get("display_name", ""),
    "tweet": parsed.get("tweet", ""),
    "likes": parsed.get("likes", ""),
    "retweets": parsed.get("retweets", ""),
    })

    #Mark original capture as processed
    captures.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "done", "processed_at": datetime.now(timezone.utc)}}
    )

    return parsed

#Endpoint to process 1 doc in capture
@app.post("/process/one")
def process_one():
    doc = captures.find_one({"status": "queued"})
    if not doc:
        return {"ok": True, "msg": "nothing queued"}
    
    parsed = process_one_capture(doc)
    return {"ok": True, "id": str(doc["_id"])}

#Endopoint to process documents in batches 
@app.post("/process/batch")
def process_batch():
    batch = list(captures.find({"status": "queued"}).sort("created_at", 1).limit(5))

    if not batch:
        return {"ok": True, "message": "No queued captures found", "processed": 0}

    processed = 0
    failed = 0

    for doc in batch:
        try:
            process_one_capture(doc)
            processed += 1
        except Exception as e:
            failed += 1
            captures.update_one(
                {"_id": doc["_id"]},
                {"$set": {"status": "error", "error": str(e)}}
            )

    return {
        "ok": True,
        "processed": processed,
        "failed": failed
    }

#Endpoint that processes documents in batches until empty
@app.post("/process/run")
def process_run():
    total_processed = 0
    total_failed = 0
    batch_num = 0

    while True:
        batch = list(captures.find({"status": "queued"}).sort("created_at", 1).limit(10))

        if not batch:
            break

        batch_num += 1
        processed = 0
        failed = 0

        for doc in batch:
            try:
                process_one_capture(doc)
                processed += 1
                total_processed += 1
            except Exception as e:
                failed += 1
                total_failed += 1
                captures.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"status": "error", "error": str(e)}}
                )

        print(f"Batch {batch_num}: processed={processed}, failed={failed}")

        # only sleep if there is still more work left
        remaining = captures.count_documents({"status": "queued"})
        if remaining > 0:
            print("Sleeping 60 seconds before next batch")
            time.sleep(60)

    return {
        "ok": True,
        "batches": batch_num,
        "processed": total_processed,
        "failed": total_failed
    }

#Background worker that keeps processing docs
async def processing_worker():
    total_processed = 0
    total_failed = 0
    batch_num = 0

    while True:
        batch = list(captures.find({"status": "queued"}).sort("created_at", 1).limit(10))

        if not batch:
            await asyncio.sleep(5)
            continue

        batch_num += 1
        processed = 0
        failed = 0

        for doc in batch:
            try:
                process_one_capture(doc)
                processed += 1
                total_processed += 1
            except Exception as e:
                failed += 1
                total_failed += 1
                captures.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"status": "error", "error": str(e)}}
                )

        print(f"Batch {batch_num}: processed={processed}, failed={failed}")

        # only sleep if there is still more work left
        remaining = captures.count_documents({"status": "queued"})
        if remaining > 0:
            print("Sleeping 60 seconds before next batch")
            await asyncio.sleep(60)

#Launching when app starts
@app.on_event("startup")
async def start_background_worker():
    asyncio.create_task(processing_worker())
