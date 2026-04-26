import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

API_BASE = "https://echochamber-production-573f.up.railway.app"

#Fixed colours for political leaning across all charts
LEANING_COLOURS = {
    "left": "#1f77b4",       
    "right": "#d62728",       
    "centre": "#9467bd",      
    "centrist": "#8c564b",  
    "apolitical": "#7f7f7f",  
    "unclear": "#ff7f0e",  
}

#Storing user_id and email in session state
if "user_id" not in st.session_state:
    st.session_state["user_id"] = ""

if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""

if "auth_token" not in st.session_state:
    st.session_state["auth_token"] = ""

query_params = st.query_params
reset_token_from_url = query_params.get("reset_token", "")
reset_email_from_url = query_params.get("email", "")

verify_token_from_url = query_params.get("verify_token", "")
verify_email_from_url = query_params.get("email", "")

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

st.title("EchoChamber")

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

#If user id isnt in session state, show tabs
if not st.session_state["user_id"]:
    if verify_token_from_url and not st.session_state.get("email_verified_message_shown", False):
            try:
                data = {
                    "email": verify_email_from_url,
                    "verify_token": verify_token_from_url
                }

                r = requests.post(f"{API_BASE}/verify-email", data=data)
                r.raise_for_status()

                st.session_state["email_verified_message_shown"] = True
                st.success("Email verified successfully. You can now log in.")
            except Exception:
                st.error("Verification failed or expired.")

    tab1, tab2, tab3 = st.tabs(["Login", "Sign up", "Forgot password"])

    with tab1:
        st.markdown("### Login")

        #Login form checking user info
        with st.form("login_form"):
            login_email = st.text_input("Email")
            login_password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Login")

            if login_submit:
                try:
                    result = login_user(login_email, login_password)
                    st.session_state["user_id"] = result["user_id"]
                    st.session_state["user_email"] = result["email"]
                    st.session_state["auth_token"] = result["token"]
                    st.success("Logged in successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"Invalid email or password. Please try again")

    with tab2:
        st.markdown("### Sign up")

        #Signup form storing user info
        with st.form("signup_form"):
            signup_email = st.text_input("Email", key="signup_email") 
            signup_password = st.text_input("Password", type="password", key="signup_password")
            signup_submit = st.form_submit_button("Sign up")

            if signup_submit:
                try:
                    result = signup_user(signup_email, signup_password)
                    st.success(result.get("message", "Account created. Please verify your email."))
                except requests.HTTPError as e:
                    try:
                        error_message = e.response.json().get("detail", "Signup failed")
                    except Exception:
                        error_message = "Signup failed"
                    st.error(error_message)
                except Exception as e:
                    st.error(f"Unexpected signup error: {e}")
    
    with tab3:
        st.markdown("### Forgot Password")

        with st.form("forgot_password_form"):
            forgot_email = st.text_input("Enter your email", key="forgot_email")
            forgot_submit = st.form_submit_button("Send Reset Email")

            if forgot_submit:
                try:
                    forgot_password(forgot_email)
                    st.success("If that email exists, a reset link has been sent.")
                except requests.HTTPError as e:
                    try:
                        error_message = e.response.json().get("detail", "Could not send reset email")
                    except Exception:
                        error_message = f"Could not send reset email: {e}"
                    st.error(error_message)
                except Exception as e:
                    st.error(f"Could not send reset email: {e}")

        with st.form("reset_password_form"):
            reset_email = st.text_input("Email", value=reset_email_from_url, key="reset_email")

            #Using token directly from email link 
            reset_token = reset_token_from_url

            if reset_token:
                st.caption("Reset link detected.")

            reset_new_password = st.text_input("New Password", type="password")
            reset_confirm_password = st.text_input("Confirm New Password", type="password")
            reset_submit = st.form_submit_button("Reset Password")

            if reset_submit:
                try:
                    reset_password(
                        reset_email,
                        reset_token,
                        reset_new_password,
                        reset_confirm_password
                    )
                    st.success("Password reset successfully. You can now log in.")
                except requests.HTTPError as e:
                    try:
                        error_message = e.response.json().get("detail", "Reset failed")
                    except Exception:
                        error_message = f"Reset failed: {e}"
                    st.error(error_message)
                except Exception as e:
                    st.error(f"Unexpected error while resetting password: {e}")

    st.stop()

#Whos logged in
st.sidebar.write(f"Logged in as: {st.session_state['user_email']}")

#Logout button
if st.sidebar.button("Logout"):
    st.session_state["user_id"] = ""
    st.session_state["user_email"] = ""
    st.session_state["auth_token"] = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Change Password")

#Form for user to change password
with st.sidebar.form("change_password_form"):
    current_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    change_password_submit = st.form_submit_button("Update Password")

    if change_password_submit:
        try:
            result = change_password(current_password, new_password, confirm_password)
            st.sidebar.success("Password updated successfully")
        except requests.HTTPError as e:
            try:
                error_message = e.response.json().get("detail", "Failed to update password")
            except Exception:
                error_message = "Failed to update password"
            st.sidebar.error(error_message)
        except Exception as e:
            st.sidebar.error("Unexpected error while updating password")


tab4, tab5, tab6 = st.tabs(["Analysis", "Create Study", "Edit/Delete Study"])

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

#Cached GET helper for stopping Streamlit from calling the same backend endpoint again on every rerun.
@st.cache_data(ttl=60)
def cached_get(url, params, token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    return r.json()

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

#Summarise one phase into counts + percentages by political leaning
def summarise_phase_leaning(study_id="", subject_id="", phase_id="", session_id=""):
    stats_data = fetch_political_leaning(study_id, subject_id, phase_id, session_id)
    series = stats_data.get("series", [])

    if not series:
        return pd.DataFrame(columns=["political_leaning", "count", "percentage"])

    df = pd.DataFrame(series)

    if df.empty or "political_leaning" not in df.columns or "count" not in df.columns:
        return pd.DataFrame(columns=["political_leaning", "count", "percentage"])

    summary = (
        df.groupby("political_leaning", as_index=False)["count"]
        .sum()
    )

    total = summary["count"].sum()
    if total > 0:
        summary["percentage"] = (summary["count"] / total) * 100
    else:
        summary["percentage"] = 0.0

    return summary


#Compare one political leaning across two phases for one chosen subject
def compare_leaning_between_phases(study_id, subject_id, phase_a, phase_b, leaning, session_id=""):
    phase_a_df = summarise_phase_leaning(
        study_id=study_id,
        subject_id=subject_id,
        phase_id=phase_a,
        session_id=session_id
    )

    phase_b_df = summarise_phase_leaning(
        study_id=study_id,
        subject_id=subject_id,
        phase_id=phase_b,
        session_id=session_id
    )

    def get_values(summary_df, chosen_leaning):
        if summary_df.empty:
            return 0, 0.0

        row = summary_df[summary_df["political_leaning"] == chosen_leaning]
        if row.empty:
            return 0, 0.0

        count = int(row["count"].iloc[0])
        percentage = float(row["percentage"].iloc[0])
        return count, percentage

    phase_a_count, phase_a_pct = get_values(phase_a_df, leaning)
    phase_b_count, phase_b_pct = get_values(phase_b_df, leaning)

    return {
        "phase_a": phase_a,
        "phase_b": phase_b,
        "leaning": leaning,
        "phase_a_count": phase_a_count,
        "phase_b_count": phase_b_count,
        "phase_a_pct": phase_a_pct,
        "phase_b_pct": phase_b_pct,
        "count_diff": phase_b_count - phase_a_count,
        "pct_diff": phase_b_pct - phase_a_pct
    }

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

with tab4:
    st.title("Algorithmic Bias Analysis")

    #Making pie chart from collected stats
    def make_pie_from_stats(series):
        if not series:
                return None, None
        
        #Convert list of items into dataframe
        df = pd.DataFrame(series)
        if df.empty:
            return None, None

        pie_df = (
            df.groupby("political_leaning", as_index=False)["count"]
            .sum()
        )

        #Making colours stay consistent for leanings
        leaning_order = ["left", "right", "centre", "centrist", "apolitical", "unclear"]
        pie_df["political_leaning"] = pd.Categorical(
            pie_df["political_leaning"],
            categories=leaning_order,
            ordered=True
        )
        pie_df = pie_df.sort_values("political_leaning")

        #Map each leaning to a fixed colour
        colours = [LEANING_COLOURS.get(label, "#cccccc") for label in pie_df["political_leaning"]]

        fig, ax = plt.subplots(figsize=(6, 4))
        
        wedges, texts, autotexts = ax.pie(
            pie_df["count"],
            labels=None, 
            colors=colours,
            #autopct="%1.1f%%",
            autopct=lambda pct: f"{pct:.1f}%" if pct >= 4 else "",   #Hide tiny labels
            startangle=90,
            pctdistance=1.12
        )

        #Style percentage text
        for autotext in autotexts:
            autotext.set_fontsize(12)

        #Legend instead of wedge labels
        ax.legend(
            wedges,
            pie_df["political_leaning"],
            title="Political leaning",
            loc="center left",
            bbox_to_anchor=(1, 0.5)
        )

        ax.axis("equal")
        return fig, df
    
    #Create reusable bar chart from API items
    def make_bar_chart(items, label_key, value_key, title, horizontal=True):
        #Returning nothing if no data exists
        if not items:
            return None

        #Convert list of items into dataframe
        df = pd.DataFrame(items)
        if df.empty or label_key not in df.columns or value_key not in df.columns:
            return None

        #Sort values so chart displays in sensible order
        df = df.sort_values(value_key, ascending=True if horizontal else False)

        #Make chart height depend on number of rows
        chart_height = max(4, len(df) * 0.45)

        #Create chart figure
        fig, ax = plt.subplots(figsize=(7, chart_height))

        #Draw horizontal bar chart
        if horizontal:
            ax.barh(df[label_key], df[value_key])
            ax.set_xlabel(value_key.replace("_", " ").title())
            ax.set_ylabel(label_key.replace("_", " ").title())
        else:
            ax.bar(df[label_key], df[value_key])
            ax.set_ylabel(value_key.replace("_", " ").title())
            ax.set_xlabel(label_key.replace("_", " ").title())
            plt.xticks(rotation=45, ha="right")

        #Set chart title and tidy layout
        ax.set_title(title)
        plt.tight_layout()
        return fig

    #Create stacked bar chart showing how each topic is split by political leaning
    def make_topic_by_leaning_chart(series):
        #Return nothing if no data exists
        if not series:
            return None

        rows = []

        #Flatten nested topic/leaning structure into simple rows
        for item in series:
            topic = item.get("topic", "")
            for leaning in item.get("leanings", []):
                rows.append({
                    "topic": topic,
                    "political_leaning": leaning.get("political_leaning", "unknown"),
                    "count": leaning.get("count", 0)
                })

        if not rows:
            return None

        #Convert rows into dataframe
        df = pd.DataFrame(rows)
        if df.empty:
            return None
        
        
        #Pivot data so each leaning becomes a stacked segment
        pivot_df = df.pivot_table(
            index="topic",
            columns="political_leaning",
            values="count",
            aggfunc="sum",
            fill_value=0,
        )

        #Sort topics by total volume
        pivot_df["total"] = pivot_df.sum(axis=1)
        pivot_df = pivot_df.sort_values("total", ascending=True).drop(columns=["total"])

        #Plot stacked horizontal bar chart by colour
        fig, ax = plt.subplots(figsize=(8, 5))
        leaning_columns = list(pivot_df.columns)
        bar_colors = [LEANING_COLOURS.get(col, "#cccccc") for col in leaning_columns]

        pivot_df.plot(
            kind="barh",
            stacked=True,
            ax=ax,
            color=bar_colors
        )

        ax.set_title("Topic by Political Leaning")
        ax.set_xlabel("Count")
        ax.set_ylabel("Topic")
        ax.legend(title="Political leaning", bbox_to_anchor=(1.02, 1), loc="upper left")
        plt.tight_layout()
        return fig

    #Dropdowns to fetch studies
    try:
        study_docs = fetch_studies()
        study_options = [doc["study_id"] for doc in study_docs]
    except Exception as e:
        st.error(f"Could not load studies: {e}")
        study_options = []

    study_id = st.selectbox("Study ID", [""] + study_options)

    #Dropdown to fetch subjects in study
    try:
        subject_docs = fetch_subjects(study_id)
        subject_options = [doc["subject_id"] for doc in subject_docs]
        #Map subject id to display label
        subject_label_map = {
            doc["subject_id"]: f"{doc['subject_id']} - {doc.get('label', '')}"
            for doc in subject_docs
        }
    except Exception as e:
        st.error(f"Could not load subjects: {e}")
        subject_options = []
        format_func=lambda sid: subject_label_map.get(sid, sid)

    #Choosing multiple subjects
    subject_ids = st.multiselect("Subject IDs", subject_options)

    #Fetching phase in study
    try:
        phase_docs = fetch_phases(study_id)
        phase_options = [doc["phase_id"] for doc in phase_docs]
    except Exception as e:
        st.error(f"Could not load phases: {e}")
        phase_options = []

    phase_id = st.selectbox("Phase ID", [""] + phase_options)

    #Fetching sessions in study
    try:
        session_docs = fetch_sessions(study_id, "", phase_id)
        session_options = [
            doc["session_id"] if isinstance(doc, dict) else doc
            for doc in session_docs
    ]
    except Exception as e:
        st.error(f"Could not load sessions: {e}")
        session_options = []

    session_id = st.selectbox("Session ID", [""] + session_options)

   #---------------- Sidebar: Phase Difference Calculator ----------------#

    st.sidebar.markdown("---")
    #Section title
    st.sidebar.subheader("Phase Difference Calculator")

    #Dropdown to select subject to analyse
    compare_subject_id = st.sidebar.selectbox(
        "Subject for comparison",
        [""] + subject_options,
        #Show label if available, otherwise show raw subject_id
        format_func=lambda sid: "Select subject" if sid == "" else subject_label_map.get(sid, sid),
        key="compare_subject_id"
    )

    #Dropdown to select which political leaning to compare
    compare_leaning = st.sidebar.selectbox(
        "Political leaning",
        ["left", "right", "centre", "centrist", "apolitical", "unclear"],
        key="compare_leaning"
    )

    #Dropdown to select first phase (baseline)
    compare_phase_a = st.sidebar.selectbox(
        "From phase",
        [""] + phase_options,
        key="compare_phase_a"
    )

    #Dropdown to select second phase (comparison phase)
    compare_phase_b = st.sidebar.selectbox(
        "To phase",
        [""] + phase_options,
        key="compare_phase_b"
    )

    #Optional filter to narrow analysis to a specific session
    compare_session_id = st.sidebar.selectbox(
        "Session filter (optional)",
        [""] + session_options,
        key="compare_session_id"
    )

    #Button to trigger calculation
    if st.sidebar.button("Calculate phase difference"):

        #Validation: ensure required inputs are selected
        if not study_id:
            st.sidebar.warning("Please select a study first.")
        elif not compare_subject_id:
            st.sidebar.warning("Please select a subject.")
        elif not compare_phase_a or not compare_phase_b:
            st.sidebar.warning("Please select both phases.")

        else:
            try:
                #Call helper function to compute difference between phases
                result = compare_leaning_between_phases(
                    study_id=study_id,
                    subject_id=compare_subject_id,
                    phase_a=compare_phase_a,
                    phase_b=compare_phase_b,
                    leaning=compare_leaning,
                    session_id=compare_session_id
                )

                #Display selected subject (label if available)
                st.sidebar.markdown(
                    f"**Subject:** {subject_label_map.get(compare_subject_id, compare_subject_id)}"
                )

                #Display percentage values for both phases
                st.sidebar.markdown(f"**Phase {result['phase_a']} %:** {result['phase_a_pct']:.2f}%")
                st.sidebar.markdown(f"**Phase {result['phase_b']} %:** {result['phase_b_pct']:.2f}%")

                #Display percentage point difference (+ / -)
                st.sidebar.markdown(f"**Percentage difference:** {result['pct_diff']:+.2f}")

                #Interpretation of result (increase / decrease / no change)
                if result["pct_diff"] > 0:
                    st.sidebar.success(
                        f"{compare_leaning.title()} leaning increased from phase {compare_phase_a} to phase {compare_phase_b}."
                    )
                elif result["pct_diff"] < 0:
                    st.sidebar.info(
                        f"{compare_leaning.title()} leaning decreased from phase {compare_phase_a} to phase {compare_phase_b}."
                    )
                else:
                    st.sidebar.info(
                        f"{compare_leaning.title()} leaning stayed the same between phase {compare_phase_a} and phase {compare_phase_b}."
                    )
            except requests.HTTPError as e:
                st.sidebar.error(f"API error: {e}")

            except Exception as e:
                st.sidebar.error("Could not calculate phase difference.")

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
                    st.subheader(subject_label_map.get(subject_id, subject_id))

                    try:
                        #Fetch all analysis datasets for selected subject
                        tweet_data = fetch_tweets(study_id, subject_id, phase_id, session_id)
                        stats_data = fetch_political_leaning(study_id, subject_id, phase_id, session_id)
                        top_words_data = fetch_top_words(study_id, subject_id, phase_id, session_id, limit=10)
                        top_topics_data = fetch_top_topics(study_id, subject_id, phase_id, session_id, limit=10)
                        topic_by_leaning_data = fetch_topic_by_leaning(study_id, subject_id, phase_id, session_id, limit=10)

                        #Show total number of tweets collected
                        #st.write("Tweet count:", tweet_data["count"])

                        #Display pie chart for political leaning distribution
                        fig, stats_df = make_pie_from_stats(stats_data["series"])
                        if fig is None:
                            st.write("No political-leaning data found.")
                        else:
                            st.pyplot(fig)

                        #Display top words as bar chart
                        st.markdown("### Top words")
                        words = top_words_data.get("words", [])
                        if words:
                            words_df = pd.DataFrame(words)

                            #Rename Mongo _id field if backend has not yet projected 'word'
                            if "_id" in words_df.columns and "word" not in words_df.columns:
                                words_df = words_df.rename(columns={"_id": "word"})

                            fig_words = make_bar_chart(
                                words_df.to_dict(orient="records"),
                                "word",
                                "count",
                                "Top Words"
                            )
                            if fig_words:
                                st.pyplot(fig_words)
                        else:
                            st.write("No top words found.")

                        #Display top topics as bar chart
                        st.markdown("### Top topics")
                        topics = top_topics_data.get("topics", [])
                        if topics:
                            topics_df = pd.DataFrame(topics)

                            #Rename Mongo _id field if backend has not yet projected 'topic'
                            if "_id" in topics_df.columns and "topic" not in topics_df.columns:
                                topics_df = topics_df.rename(columns={"_id": "topic"})

                            fig_topics = make_bar_chart(
                                topics_df.to_dict(orient="records"),
                                "topic",
                                "count",
                                "Top Topics"
                            )
                            if fig_topics:
                                st.pyplot(fig_topics)
                        else:
                            st.write("No top topics found.")

                        #Display stacked chart showing topic distribution by political leaning
                        st.markdown("### Topic by leaning")
                        series = topic_by_leaning_data.get("series", [])
                        if series:
                            fig_topic_leaning = make_topic_by_leaning_chart(series)
                            if fig_topic_leaning:
                                st.pyplot(fig_topic_leaning)
                        else:
                            st.write("No topic-by-leaning data found.")

                    except requests.HTTPError as e:
                        st.error(f"API error: {e}")
                    except Exception as e:
                        st.error(f"Data is currently being analysed. Try again later")

with tab5: 
    
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
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Study ID already exists")

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
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Subject ID already exists")


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
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Phase ID already exists")
    
with tab6:
    #DELETE / EDIT STUDY
    st.header("Edit / Delete Study")

    #fetching study
    try:
        study_docs = fetch_studies()
        study_options = [doc["study_id"] for doc in study_docs]
    except Exception as e:
        st.error(f"Could not load studies for editing: {e}")
        study_docs = []
        study_options = []

    #selecting study
    selected_study_to_edit = st.selectbox(
        "Select Study to Edit",
        [""] + study_options,
        key="edit_study_select"
    )
    #looking for matching study id
    if selected_study_to_edit:
        selected_study_doc = next(
            (doc for doc in study_docs if doc["study_id"] == selected_study_to_edit),
            None
        )

        if selected_study_doc:
            with st.form("edit_study_form"):
                edit_study_name = st.text_input(
                    "Study Name",
                    value=selected_study_doc.get("name", "")
                )
                edit_study_description = st.text_area(
                    "Description",
                    value=selected_study_doc.get("description", "")
                )

                col1, col2 = st.columns(2)
                save_study = col1.form_submit_button("Save Study Changes")
                delete_study_btn = col2.form_submit_button("Delete Study")

                #updating study
                if save_study:
                    try:
                        update_study(
                            selected_study_to_edit,
                            edit_study_name,
                            edit_study_description
                        )
                        st.success("Study updated")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update study: {e}")

                #deleting study
                if delete_study_btn:
                    try:
                        delete_study(selected_study_to_edit)
                        st.success("Study deleted")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete study: {e}")

    #DELETE / EDIT SUBJECT

    st.header("Edit / Delete Subject")

    selected_study_for_subject_edit = st.selectbox(
        "Study for Subject Edit",
        [""] + study_options,
        key="subject_edit_study"
    )

    #fetching subject
    if selected_study_for_subject_edit:
        try:
            subject_docs_for_edit = fetch_subjects(selected_study_for_subject_edit)
            subject_edit_options = [doc["subject_id"] for doc in subject_docs_for_edit]
        except Exception as e:
            st.error(f"Could not load subjects for editing: {e}")
            subject_docs_for_edit = []
            subject_edit_options = []

        selected_subject_to_edit = st.selectbox(
            "Select Subject to Edit",
            [""] + subject_edit_options,
            key="edit_subject_select"
        )

        #looking for matching subject id
        if selected_subject_to_edit:
            selected_subject_doc = next(
                (doc for doc in subject_docs_for_edit if doc["subject_id"] == selected_subject_to_edit),
                None
            )

            if selected_subject_doc:
                with st.form("edit_subject_form"):
                    edit_subject_label = st.text_input(
                        "Subject Label",
                        value=selected_subject_doc.get("label", "")
                    )

                    col1, col2 = st.columns(2)
                    save_subject = col1.form_submit_button("Save Subject Changes")
                    delete_subject_btn = col2.form_submit_button("Delete Subject")

                    if save_subject:
                        try: #updating subject
                            update_subject(
                                selected_study_for_subject_edit,
                                selected_subject_to_edit,
                                edit_subject_label
                            )
                            st.success("Subject updated")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update subject: {e}")

                    #deleting subject
                    if delete_subject_btn:
                        try:
                            delete_subject(
                                selected_study_for_subject_edit,
                                selected_subject_to_edit
                            )
                            st.success("Subject deleted")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete subject: {e}")
            
    #DELETE / EDIT PHASE
    st.header("Edit / Delete Phase")

    selected_study_for_phase_edit = st.selectbox(
        "Study for Phase Edit",
        [""] + study_options,
        key="phase_edit_study"
    )

    #fetching phases
    if selected_study_for_phase_edit:
        try:
            phase_docs_for_edit = fetch_phases(selected_study_for_phase_edit)
            phase_edit_options = [doc["phase_id"] for doc in phase_docs_for_edit]
        except Exception as e:
            st.error(f"Could not load phases for editing: {e}")
            phase_docs_for_edit = []
            phase_edit_options = []

        selected_phase_to_edit = st.selectbox(
            "Select Phase to Edit",
            [""] + phase_edit_options,
            key="edit_phase_select"
        )

        #looking for matching phase id
        if selected_phase_to_edit:
            selected_phase_doc = next(
                (doc for doc in phase_docs_for_edit if doc["phase_id"] == selected_phase_to_edit),
                None
            )

            #editing specific parts of phase
            if selected_phase_doc:
                with st.form("edit_phase_form"):
                    edit_phase_label = st.text_input(
                        "Phase Label",
                        value=selected_phase_doc.get("label", "")
                    )

                    current_start = selected_phase_doc.get("start_date", "")
                    current_end = selected_phase_doc.get("end_date", "")

                    edit_phase_start = st.date_input("Start Date", value = current_start)
                    edit_phase_end = st.date_input("End Date", value = current_end)

                    col1, col2 = st.columns(2)
                    save_phase = col1.form_submit_button("Save Phase Changes")
                    delete_phase_btn = col2.form_submit_button("Delete Phase")

                    #updating phase
                    if save_phase:
                        try:
                            update_phase(
                                selected_study_for_phase_edit,
                                selected_phase_to_edit,
                                edit_phase_label,
                                edit_phase_start,
                                edit_phase_end
                            )
                            st.success("Phase updated")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update phase: {e}")

                    #deleting phase
                    if delete_phase_btn:
                        try:
                            delete_phase(
                                selected_study_for_phase_edit,
                                selected_phase_to_edit
                            )
                            st.success("Phase deleted")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete phase: {e}")