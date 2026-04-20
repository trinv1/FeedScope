# EchoChamber

EchoChamber is a research platform designed to analyse how personalised social media recommendation feeds evolve over time. The system captures content from the X (Twitter) “For You” feed, extracts text from screenshots, classifies sentiment and political leaning using large language models, and visualises trends through an interactive dashboard.

The project was developed to investigate whether gender-related account signals influence the political composition of recommended content.

# Overview

EchoChamber implements a fully automated, end-to-end data pipeline for studying algorithmic personalisation and potential bias in recommendation systems.

The system enables:

* Longitudinal analysis of recommendation feeds
* Controlled multi-account experimentation
* Automated capture and processing of feed data
* Visual exploration of political and emotional trends

# System Architecture

The platform is composed of several interconnected components:

## Data Capture

A Chrome extension automatically scrolls through the X “For You” feed and captures screenshots at regular intervals.

## Text Extraction

Captured images are processed using the OpenAI API to extract tweet content from the feed.

## Storage

Extracted data and metadata are stored in a MongoDB Atlas database.

## Processing & Classification

Tweets are analysed using large language models to determine:

- Political leaning
- Emotional tone
- Topic classification
- Backend (FastAPI)

### A RESTful API handles:

- Authentication
- Data ingestion
- Background processing
- Retrieval of processed results
- Frontend (Streamlit)

### An interactive dashboard allows users to:

- Manage studies and phases
- View sentiment and political distributions
- Analyse trends over time
- Automation

# Tech Stack
* Python
* FastAPI
* Streamlit
* MongoDB Atlas
* OpenAI API
* Chrome Extension (JavaScript, Manifest V3)

# How to run
**Clone repository:**

* git clone https://github.com/trinv1/EchoChamber
* cd echochamber

**Install Dependencies:**
* pip install -r Backend/requirements.txt
* pip install -r requirements.txt

**Configure environmental variables:**
* OPENAI_API_KEY=your_openai_key
* BREVO_API_KEY=your_brevo_key
* SECRET_KEY=your_secret_key
* MONGO_URI=your_mongodb_connection_string

**Create account:**
1. Navigate to: https://feedscopeinc.streamlit.app/
2. Signup with email and password

**Load the Chrome Extension**
1. Open Chrome and navigate to:
- chrome://extensions/
2. Enable Developer Mode
3. Click “Load unpacked”
4. Select the extension/ folder from this project
5. The extension will appear in your toolbar

**Using the Extension**
1. Open the extension popup
2. Log in
3. Select:
- Study
- Subject
- Phase
4. Click Start Capture

The extension will:
* Scroll the feed
* Capture screenshots
* Upload data to the backend

# Experimental Design

The system supports a multi-phase experimental framework where controlled accounts are modified incrementally.

Phases include:

* Baseline (no gender signals)
* Gender assignment
* Gendered usernames
* Controlled posting
* Controlled engagement (likes)
* Balanced political following
* Strong ideological signals

This enables structured analysis of how recommendation outputs change over time.

# Key Features
* Automated feed capture from X
* Image-based tweet extraction
* Sentiment and political classification
* Duplicate detection and filtering
* Multi-account experimental tracking
* Interactive visual analytics
* Scalable backend processing


