import pandas as pd
from api_client import fetch_political_leaning

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
