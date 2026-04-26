import streamlit as st
import requests
import pandas as pd

from api_client import (
    fetch_studies,
    fetch_subjects,
    fetch_phases,
    fetch_sessions,
    fetch_tweets,
    fetch_political_leaning,
    fetch_top_words,
    fetch_top_topics,
    fetch_topic_by_leaning,
)
from analysis_logic import compare_leaning_between_phases
from charts import make_pie_from_stats, make_bar_chart, make_topic_by_leaning_chart
from config import LEANING_ORDER

#----------------------- ANALYSIS PAGE  ----------------------- #

def render_analysis_page():
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

    render_phase_difference_sidebar(
            study_id=study_id,
            subject_options=subject_options,
            subject_label_map=subject_label_map,
            phase_options=phase_options,
            session_options=session_options,
        )

#----------------------- LOAD ANALYSIS BUTTON  ----------------------- #
    if st.button("Load analysis"):
        if not subject_ids:
            st.warning("Please select at least one subject.")   
        else:
            cols = st.columns(min(len(subject_ids), 3))

            #Looping through subject, getting position and placing in available column
            for i, selected_subject_id in enumerate(subject_ids):
                col = cols[i % len(cols)]

                with col:
                    st.subheader(subject_label_map.get(selected_subject_id, selected_subject_id))
                    render_subject_analysis(study_id, selected_subject_id, phase_id, session_id)

#----------------------- PHASE DIFFERENCE   ----------------------- #

def render_phase_difference_sidebar(study_id, subject_options, subject_label_map, phase_options, session_options):
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

#----------------------- SUBJECT ANALYSIS   ----------------------- #

def render_subject_analysis(study_id, subject_id, phase_id, session_id):
    
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

        render_top_words(top_words_data)
        render_top_topics(top_topics_data)
        render_topic_by_leaning(topic_by_leaning_data)

    except requests.HTTPError as e:
        st.error(f"API error: {e}")
    except Exception:
        st.error("Data is currently being analysed. Try again later")

#-----------------------  TOP WORDS ----------------------- #

def render_top_words(top_words_data):
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

#-----------------------  TOP TOPICS ----------------------- #

def render_top_topics(top_topics_data):
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

#-----------------------  TOP BY LEANING ----------------------- #

def render_topic_by_leaning(topic_by_leaning_data):
    #Display stacked chart showing topic distribution by political leaning
    st.markdown("### Topic by leaning")
    series = topic_by_leaning_data.get("series", [])
    if series:
        fig_topic_leaning = make_topic_by_leaning_chart(series)
        if fig_topic_leaning:
            st.pyplot(fig_topic_leaning)
    else:
        st.write("No topic-by-leaning data found.")

