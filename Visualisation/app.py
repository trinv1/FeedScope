import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt


API_BASE = "https://echochamber-q214.onrender.com"

st.title("Algorithmic Bias Analysis")

#Fetching studies from api
def fetch_studies():
    r = requests.get(f"{API_BASE}/studies")
    r.raise_for_status()
    return r.json()["studies"]

#Fetching subjects from api
def fetch_subjects(study_id=""):
    params = {}
    if study_id:
        params["study_id"] = study_id
    r = requests.get(f"{API_BASE}/subjects", params=params)
    r.raise_for_status()
    return r.json()["subjects"]

#Fetching from phases from api
def fetch_phases(study_id="", subject_id=""):
    params = {}
    if study_id:
        params["study_id"] = study_id
    if subject_id:
        params["subject_id"] = subject_id
    r = requests.get(f"{API_BASE}/phases", params=params)
    r.raise_for_status()
    return r.json()["phases"]

#Fetching sessions from api
def fetch_sessions(study_id="", subject_id="", phase_id=""):
    params = {}
    if study_id:
        params["study_id"] = study_id
    if subject_id:
        params["subject_id"] = subject_id
    if phase_id:
        params["phase_id"] = phase_id
    r = requests.get(f"{API_BASE}/sessions", params=params)
    r.raise_for_status()
    return r.json()["sessions"]

#Fetching tweets
def fetch_tweets(study_id="", subject_id="", phase_id="", session_id=""):
    params = {}
    if study_id:
        params["study_id"] = study_id
    if subject_id:
        params["subject_id"] = subject_id
    if phase_id:
        params["phase_id"] = phase_id
    if session_id:
        params["session_id"] = session_id

    r = requests.get(f"{API_BASE}/tweets", params=params)
    r.raise_for_status()
    return r.json()


#Fetching stats
def fetch_political_leaning(study_id="", subject_id="", phase_id="", session_id=""):
    params = {}
    if study_id:
        params["study_id"] = study_id
    if subject_id:
        params["subject_id"] = subject_id
    if phase_id:
        params["phase_id"] = phase_id
    if session_id:
        params["session_id"] = session_id

    r = requests.get(f"{API_BASE}/stats/political-leaning", params=params)
    r.raise_for_status()
    return r.json()

#Making pie chart from collected stats
def make_pie_from_stats(series):
    if not series:
            return None, None
    
    df = pd.DataFrame(series)
    if df.empty:
        return None, None

    pie_df = (
        df.groupby("political_leaning", as_index=False)["count"]
        .sum()
        .sort_values("count", ascending=False)
    )

    fig, ax = plt.subplots()
    ax.pie(
        pie_df["count"],
        labels=pie_df["political_leaning"],
        autopct="%1.1f%%",
        startangle=90
    )
    ax.axis("equal")
    return fig, df

try:
    studies = fetch_studies()
except Exception as e:
    st.error(f"Could not load studies: {e}")
    studies = []

study_id = st.selectbox("Study ID", [""] + studies)

try:
    subjects = fetch_subjects(study_id)
except Exception as e:
    st.error(f"Could not load subjects: {e}")
    subjects = []

subject_id = st.selectbox("Subject ID", [""] + subjects)

try:
    phases = fetch_phases(study_id, subject_id)
except Exception as e:
    st.error(f"Could not load phases: {e}")
    phases = []

phase_id = st.selectbox("Phase ID", [""] + phases)

try:
    sessions = fetch_sessions(study_id, subject_id, phase_id)
except Exception as e:
    st.error(f"Could not load sessions: {e}")
    sessions = []

session_id = st.selectbox("Session ID", [""] + sessions)



#Loading analysis from data
if st.button("Load analysis"):
    try:
            tweet_data = fetch_tweets(study_id, subject_id, phase_id, session_id)
            stats_data = fetch_political_leaning(study_id, subject_id, phase_id, session_id)

            st.subheader("Tweets")
            st.write("Tweet count:", tweet_data["count"])

            tweets_df = pd.DataFrame(tweet_data["tweets"])
            if tweets_df.empty:
                st.write("No tweets found for these filters.")
            else:
                st.dataframe(tweets_df)

            st.subheader("Political leaning breakdown")
            fig, stats_df = make_pie_from_stats(stats_data["series"])

            if fig is None:
                st.write("No political-leaning data found for these filters.")
            else:
                st.pyplot(fig)
                st.dataframe(stats_df)

    except requests.HTTPError as e:
        st.error(f"API error: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")