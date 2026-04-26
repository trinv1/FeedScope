import streamlit as st
import requests
from api_client import (
    signup_user,
    login_user,
    forgot_password,
    reset_password,
    verify_email,
    change_password,
)

#Render login, sign-up, email verification, and password reset forms.
def render_auth_page(reset_token_from_url, reset_email_from_url, verify_token_from_url, verify_email_from_url):
    if verify_token_from_url and not st.session_state.get("email_verified_message_shown", False):
        try:
            verify_email(verify_email_from_url, verify_token_from_url)
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

#Render side bar controls
def render_logged_in_sidebar():
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