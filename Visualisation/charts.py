import pandas as pd
import matplotlib.pyplot as plt
from config import LEANING_COLOURS, LEANING_ORDER

#----------------------- PIE CHARTS ----------------------- #

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
    pie_df["political_leaning"] = pd.Categorical(
        pie_df["political_leaning"],
        categories=LEANING_ORDER,
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

#----------------------- BAR CHART ----------------------- #

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

#----------------------- TOPIC BY LEANING ----------------------- #

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