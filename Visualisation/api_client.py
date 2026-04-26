import streamlit as st
import requests
from config import API_BASE

#Helper returning auth token in session state
def auth_headers():
    return {
        "Authorization": f"Bearer {st.session_state['auth_token']}"
    }

#Helper function to signup user
def signup_user(email, password):
    data = {
        "email": email,
        "password": password,
    }
    r = requests.post(f"{API_BASE}/signup", data=data)
    r.raise_for_status()
    return r.json()

#Helper function to login user
def login_user(email, password):
    data = {
        "email": email,
        "password": password,
    }
    r = requests.post(f"{API_BASE}/login", data=data)
    r.raise_for_status()
    return r.json()

#Helper function to change password
def change_password(current_password, new_password, confirm_password):
    data = {
        "current_password": current_password,
        "new_password": new_password,
        "confirm_password": confirm_password,
    }

    r = requests.post(
        f"{API_BASE}/change-password",
        data=data,
        headers=auth_headers()
    )
    r.raise_for_status()
    return r.json()


#Helper function to request password reset
def forgot_password(email):
    data = {
        "email": email,
    }
    r = requests.post(f"{API_BASE}/forgot-password", data=data)
    r.raise_for_status()
    return r.json()


#Helper function to reset password using token
def reset_password(email, reset_token, new_password, confirm_password):
    data = {
        "email": email,
        "reset_token": reset_token,
        "new_password": new_password,
        "confirm_password": confirm_password,
    }
    r = requests.post(f"{API_BASE}/reset-password", data=data)
    r.raise_for_status()
    return r.json()

def verify_email(email, verify_token):
    data = {
        "email": email, 
        "verify_token": verify_token
    }
    r = requests.post(f"{API_BASE}/verify-email", data=data)
    r.raise_for_status()
    return r.json()


# ---------------- Cached GET helper ---------------- #

#Cached GET helper for stopping Streamlit from calling the same backend endpoint again on every rerun
@st.cache_data(ttl=60)
def cached_get(url, params, token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    return r.json()

# ---------------- Study / subject / phase create API ---------------- #

#Helper functions to create study, subject and phase
def create_study(study_id, name, description):
    data = {
        "study_id": study_id,
        "name": name,
        "description": description,
    }
    r = requests.post(f"{API_BASE}/studies", data=data, headers=auth_headers())
    r.raise_for_status()
    return r.json()

def create_subject(study_id, subject_id, label):
    data = {
        "study_id": study_id,
        "subject_id": subject_id,
        "label": label,
    }
    r = requests.post(f"{API_BASE}/subjects", data=data, headers=auth_headers())
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
    r = requests.post(f"{API_BASE}/phases", data=data, headers=auth_headers())
    r.raise_for_status()
    return r.json()

# ---------------- Fetch API ---------------- #

#Fetching studies from api
def fetch_studies():
    return cached_get(
        f"{API_BASE}/studies",
        {},
        st.session_state["auth_token"]
    )["studies"]

#Fetching subjects from api
def fetch_subjects(study_id=""):
    params = {}
    if study_id:
        params["study_id"] = study_id

    return cached_get(
        f"{API_BASE}/subjects",
        params,
        st.session_state["auth_token"]
    )["subjects"]

#Fetching from phases from api
def fetch_phases(study_id="", subject_id=""):
    params = {}
    if study_id:
        params["study_id"] = study_id
    if subject_id:
        params["subject_id"] = subject_id

    return cached_get(
        f"{API_BASE}/phases",
        params,
        st.session_state["auth_token"]
    )["phases"]

#Fetching sessions from api
def fetch_sessions(study_id="", subject_id="", phase_id="", status=""):
    params = {}

    if study_id:
        params["study_id"] = study_id
    if subject_id:
        params["subject_id"] = subject_id
    if phase_id:
        params["phase_id"] = phase_id
    if status:
        params["status"] = status

    return cached_get(
        f"{API_BASE}/sessions",
        params,
        st.session_state["auth_token"]
    )["sessions"]

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

    return cached_get(
        f"{API_BASE}/tweets",
        params,
        st.session_state["auth_token"]
    )

#Fetching political leaning stats
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

    return cached_get(
        f"{API_BASE}/stats/political-leaning",
        params,
        st.session_state["auth_token"]
    )

#Fetch top words stats from API for selected filters
def fetch_top_words(study_id="", subject_id="", phase_id="", session_id="", limit=20):
    params = {"limit": limit}

    #Add optional filters if selected
    if study_id:
        params["study_id"] = study_id
    if subject_id:
        params["subject_id"] = subject_id
    if phase_id:
        params["phase_id"] = phase_id
    if session_id:
        params["session_id"] = session_id

    return cached_get(
        f"{API_BASE}/stats/top-words",
        params,
        st.session_state["auth_token"]
    )

#Fetch top topic stats from API for selected filters
def fetch_top_topics(study_id="", subject_id="", phase_id="", session_id="", limit=10):
    params = {"limit": limit}
    if study_id:
        params["study_id"] = study_id
    if subject_id:
        params["subject_id"] = subject_id
    if phase_id:
        params["phase_id"] = phase_id
    if session_id:
        params["session_id"] = session_id

    return cached_get(
        f"{API_BASE}/stats/top-topics",
        params,
        st.session_state["auth_token"]
    )

#Fetch topic by leaning stats from API for selected filters
def fetch_topic_by_leaning(study_id="", subject_id="", phase_id="", session_id="", limit=20):
    params = {"limit": limit}
    if study_id:
        params["study_id"] = study_id
    if subject_id:
        params["subject_id"] = subject_id
    if phase_id:
        params["phase_id"] = phase_id
    if session_id:
        params["session_id"] = session_id

    return cached_get(
        f"{API_BASE}/stats/topic-by-leaning",
        params,
        st.session_state["auth_token"]
    )

# ---------------- Update / delete API ---------------- #

#Helpers to update and delete study
def update_study(study_id, name, description):
    data = {
        "name": name,
        "description": description,
    }
    r = requests.put(
        f"{API_BASE}/studies/{study_id}",
        data=data,
        headers=auth_headers()
    )
    r.raise_for_status()
    return r.json()

def delete_study(study_id):
    r = requests.delete(
        f"{API_BASE}/studies/{study_id}",
        headers=auth_headers()
    )
    r.raise_for_status()
    return r.json()

#Helpers to update and delete subject
def update_subject(study_id, subject_id, label):
    data = {
        "study_id": study_id,
        "label": label,
    }
    r = requests.put(
        f"{API_BASE}/subjects/{subject_id}",
        data=data,
        headers=auth_headers()
    )
    r.raise_for_status()
    return r.json()

def delete_subject(study_id, subject_id):
    params = {"study_id": study_id}
    r = requests.delete(
        f"{API_BASE}/subjects/{subject_id}",
        params=params,
        headers=auth_headers()
    )
    r.raise_for_status()
    return r.json()

#Helpers to update and delete phase
def update_phase(study_id, phase_id, label, start_date, end_date):
    data = {
        "study_id": study_id,
        "label": label,
        "start_date": str(start_date),
        "end_date": str(end_date),
    }
    r = requests.put(
        f"{API_BASE}/phases/{phase_id}",
        data=data,
        headers=auth_headers()
    )
    r.raise_for_status()
    return r.json()

def delete_phase(study_id, phase_id):
    params = {"study_id": study_id}
    r = requests.delete(
        f"{API_BASE}/phases/{phase_id}",
        params=params,
        headers=auth_headers()
    )
    r.raise_for_status()
    return r.json()

