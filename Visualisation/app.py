import streamlit as st
from state import init_session_state
from auth_page import render_auth_page, render_logged_in_sidebar
from analysis_page import render_analysis_page
from study_pages import render_create_study_page, render_edit_delete_study_page

st.title("EchoChamber")

#Initialize session state variables (user_id, email, auth_token etc)
init_session_state()

#Get query parameters from URL for reset/verify links
query_params = st.query_params

#Extract password reset token and email from URL
reset_token_from_url = query_params.get("reset_token", "")
reset_email_from_url = query_params.get("email", "")

#Extract email verification token and email from URL 
verify_token_from_url = query_params.get("verify_token", "")
verify_email_from_url = query_params.get("email", "")

#If user is not logged in, show authentication tabs only
if not st.session_state["user_id"]:
    render_auth_page(
        reset_token_from_url=reset_token_from_url,
        reset_email_from_url=reset_email_from_url,
        verify_token_from_url=verify_token_from_url,
        verify_email_from_url=verify_email_from_url,
    )
    st.stop()

#Rendering sidebar
render_logged_in_sidebar()

tab_analysis, tab_create, tab_edit = st.tabs(["Analysis", "Create Study", "Edit/Delete Study"])

#Rendering pages
with tab_analysis:
    render_analysis_page()

with tab_create:
    render_create_study_page()

with tab_edit:
    render_edit_delete_study_page()