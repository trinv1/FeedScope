import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

tab1, tab2 = st.tabs(["Analysis", "Manage Setup"])

API_BASE = "https://echochamber-q214.onrender.com"

#Helper functions to create study, subject and phase
def create_study(study_id, name, description):
    data = {
        "study_id": study_id,
        "name": name,
        "description": description,
    }
    r = requests.post(f"{API_BASE}/studies", data=data)
    r.raise_for_status()
    return r.json()

def create_subject(study_id, subject_id, label):
    data = {
        "study_id": study_id,
        "subject_id": subject_id,
        "label": label,
    }
    r = requests.post(f"{API_BASE}/subjects", data=data)
    r.raise_for_status()
    return r.json()

def create_phase(study_id, phase_id, label, start_date, end_date):
    data = {
        "study_id": study_id,
        "phase_id": phase_id,
        "label": label,
        "start_date": str(start_date),
        "end_date": str(end_date),
    }
    r = requests.post(f"{API_BASE}/phases", data=data)
    r.raise_for_status()
    return r.json()

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

with tab1:

    st.title("Algorithmic Bias Analysis")

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

    #Dropdowns to fetch studies
    try:
        study_docs = fetch_studies()
        study_options = [doc["study_id"] for doc in study_docs]
    except Exception as e:
        st.error(f"Could not load studies: {e}")
        studies = []

    study_id = st.selectbox("Study ID", [""] + study_options)

    #Dropdown to fetch subjects in study
    try:
        subject_docs = fetch_subjects(study_id)
        subject_options = [doc["subject_id"] for doc in subject_docs]
    except Exception as e:
        st.error(f"Could not load subjects: {e}")
        all_subjects = []

    #Choosing multiple subjects
    subject_ids = st.multiselect("Subject IDs", subject_options)

    #Showing phases that exist for this subject
    if subject_ids:
        phase_subject_for_filter = subject_ids[0]
    else:
        phase_subject_for_filter = ""

    #Fetching phase in study
    try:
        phase_docs = fetch_phases(study_id)
        phase_options = [doc["phase_id"] for doc in phase_docs]
    except Exception as e:
        st.error(f"Could not load phases: {e}")
        phases = []

    phase_id = st.selectbox("Phase ID", [""] + phase_options)

    #Fetching sessions 
    try:
        sessions = fetch_sessions(study_id, phase_subject_for_filter, phase_id)
    except Exception as e:
        st.error(f"Could not load sessions: {e}")
        sessions = []

    session_id = st.selectbox("Session ID", [""] + sessions)


    #Loading analysis from data
    if st.button("Load analysis"):
        if not subject_ids:
            st.warning("Please select at least one subject.")   
        else:
            cols = st.columns(min(len(subject_ids), 3))

            #Looping through subject, getting position and placing in available column
            for i, subject_id in enumerate(subject_ids):
                col = cols[i % len(cols)]

                with col:
                    st.subheader(subject_id)
                    
                    #Displaying pie chart of stats
                    try:
                        tweet_data = fetch_tweets(study_id, subject_id, phase_id, session_id)
                        stats_data = fetch_political_leaning(study_id, subject_id, phase_id, session_id)

                        st.write("Tweet count:", tweet_data["count"])

                        fig, stats_df = make_pie_from_stats(stats_data["series"])
                        if fig is None:
                            st.write("No political-leaning data found.")
                        else:
                            st.pyplot(fig)

                    except requests.HTTPError as e:
                        st.error(f"API error: {e}")
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")

with tab2: 
    st.header("Create Study")

    #Form to create study
    with st.form("create_study_form"):
        new_study_id = st.text_input("Study ID")
        new_study_name = st.text_input("Study Name")
        new_study_description = st.text_area("Description")
        submit_study = st.form_submit_button("Create Study")

        if submit_study:
            try:
                result = create_study(new_study_id, new_study_name, new_study_description)
                st.success(f"Study created: {new_study_id}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create study: {e}")

    st.header("Create Subject")

    #Form to create subject
    study_docs = fetch_studies()
    study_options = [doc["study_id"] if isinstance(doc, dict) else doc for doc in study_docs]

    with st.form("create_subject_form"):
        subject_study_id = st.selectbox("Study", study_options)
        new_subject_id = st.text_input("Subject ID")
        new_subject_label = st.text_input("Subject Label")
        submit_subject = st.form_submit_button("Create Subject")

        if submit_subject:
            try:
                result = create_subject(subject_study_id, new_subject_id, new_subject_label)
                st.success(f"Subject created: {new_subject_id}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create subject: {e}")


    st.header("Create Phase")

    #Form to create phase
    with st.form("create_phase_form"):
        phase_study_id = st.selectbox("Study for Phase", study_options)
        new_phase_id = st.text_input("Phase ID")
        new_phase_label = st.text_input("Phase Label")
        new_phase_start = st.date_input("Start Date")
        new_phase_end = st.date_input("End Date")
        submit_phase = st.form_submit_button("Create Phase")

        if submit_phase:
            try:
                result = create_phase(
                    phase_study_id,
                    new_phase_id,
                    new_phase_label,
                    new_phase_start,
                    new_phase_end
                )
                st.success(f"Phase created: {new_phase_id}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create phase: {e}")