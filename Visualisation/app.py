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

boy_df = fetch_data(API_URL_B)
girl_df = fetch_data(API_URL_G)


st.title("Algorithmic Bias Analysis")

#Showing statistics
def show_by_phase(df, title):
    st.header(title)

    for p in phases:
        start = pd.to_datetime(p["start"], format="%d-%m-%Y")
        end = pd.to_datetime(p["end"], format="%d-%m-%Y")

        phase_df = df[(df["date"] >= start) & (df["date"] <= end)].copy()

        st.subheader(p["name"])

        if phase_df.empty:
            st.write("No data collected yet for this phase.")
        #else:
         #   phase_df["date"] = phase_df["date"].dt.date#removing time
          #  st.dataframe(phase_df[["date", "political_leaning", "count"]], use_container_width=True)

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

        st.pyplot(fig)

        phase_df["date"] = phase_df["date"].dt.date
        st.dataframe(phase_df[["date", "political_leaning", "count"]], use_container_width=True)

show_by_phase(boy_df, "Male account")
show_by_phase(girl_df, "Female account")