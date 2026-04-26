import streamlit as st

def init_session_state():
    #Storing user_id, email and auth token in session state
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = ""

    if "user_email" not in st.session_state:
        st.session_state["user_email"] = ""

    if "auth_token" not in st.session_state:
        st.session_state["auth_token"] = ""
