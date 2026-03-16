import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

API_URL_B = "https://echochamber-q214.onrender.com/stats/boy/political-leaning"
API_URL_G = "https://echochamber-q214.onrender.com/stats/girl/political-leaning"

phases = [
    {
        "name": "Phase 1 – Baseline (no gender)",
        "start": "23-11-2025",
        "end": "06-12-2025"
    },
    {
        "name": "Phase 2 – Gender assigned",
        "start": "07-12-2025",
        "end": "13-01-2026"
    },
    {
        "name": "Phase 3 – Gender + username",
        "start": "14-01-2026",
        "end": "07-03-2026"
    },
    {
        "name": "Phase 4 – Post tweet",
        "start": "08-03-2026",
        "end": "30-03-2026"
    },
    {
        "name": "Phase 5 – Unknown",
        "start": "01-04-2026",
        "end": "28-04-2026"
    },
    {
        "name": "Phase 6 – Unknown",
        "start": "21-03-2026",
        "end": "11-04-2026"
    },
] 

#Fetching aggregated data for tables
def fetch_data(url):
    r = requests.get(url)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["series"])
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    return df.sort_values("date")

#Making pie chart for each phase
def make_phase_pie(df, start, end):
    phase_df = df[(df["date"] >= start) & (df["date"] <= end)].copy()

    if phase_df.empty:
        return None, None

    pie_df = (
        phase_df.groupby("political_leaning", as_index=False)["count"]
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

    return fig, phase_df

boy_df = fetch_data(API_URL_B)
girl_df = fetch_data(API_URL_G)

st.title("Algorithmic Bias Analysis by Phase")

#Displaying data for each phase side by side
for p in phases:
    start = pd.to_datetime(p["start"], format="%d-%m-%Y")
    end = pd.to_datetime(p["end"], format="%d-%m-%Y")

    st.header(p["name"])
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Boy")
        boy_fig, boy_phase_df = make_phase_pie(boy_df, start, end)

        if boy_fig is None:
            st.write("No data collected yet for this phase.")
        else:
            st.pyplot(boy_fig)

    with col2:
        st.subheader("Girl")
        girl_fig, girl_phase_df = make_phase_pie(girl_df, start, end)

        if girl_fig is None:
            st.write("No data collected yet for this phase.")
        else:
            st.pyplot(girl_fig)

    st.divider()