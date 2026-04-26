import streamlit as st
from datetime import date

from api_client import (
    create_study,
    create_subject,
    create_phase,
    fetch_studies,
    fetch_subjects,
    fetch_phases,
    update_study,
    delete_study,
    update_subject,
    delete_subject,
    update_phase,
    delete_phase,
)

#----------------------- CREATE STUDY ----------------------- #
def render_create_study_page():
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

def render_edit_delete_study_page():
    render_edit_delete_study()
    render_edit_delete_subject()
    render_edit_delete_phase()

#----------------------- EDIT / DELETE STUDY ----------------------- #

def render_edit_delete_study():
    st.header("Edit or Delete Study")

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

#----------------------- EDIT / DELETE SUBJECT ----------------------- #

def render_edit_delete_subject():
    st.header("Edit or Delete Subject")

    #Fetching studies
    try:
        study_docs = fetch_studies()
        study_options = [doc["study_id"] for doc in study_docs]
    except Exception:
        study_options = []

    selected_study_for_subject_edit = st.selectbox(
        "Study for Subject Edit",
        [""] + study_options,
        key="subject_edit_study",
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

#----------------------- EDIT / DELETE PHASE ----------------------- #

def render_edit_delete_phase():
    st.header("Edit or Delete Phase")

    #Fetching study
    try:
        study_docs = fetch_studies()
        study_options = [doc["study_id"] for doc in study_docs]
    except Exception:
        study_options = []

    selected_study_for_phase_edit = st.selectbox(
        "Study for Phase Edit",
        [""] + study_options,
        key="phase_edit_study",
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