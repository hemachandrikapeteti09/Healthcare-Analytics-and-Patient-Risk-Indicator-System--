from collections import Counter
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def build_summary(records):
    columns = ["department", "visit_date", "age_band", "visit_type"]
    df = pd.DataFrame(records)
    for col in columns:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    total = int(len(df))
    if total == 0:
        return {
            "total_visits": 0,
            "department_counts": [],
            "visit_type_counts": [],
            "monthly_counts": [],
            "average_visits_per_department": 0,
        }
    department_counts = (
        df["department"].fillna("Unknown").value_counts().rename_axis("department")
        .reset_index(name="visits").to_dict(orient="records")
    )
    visit_type_counts = (
        df["visit_type"].fillna("Unknown").value_counts().rename_axis("visit_type")
        .reset_index(name="visits").to_dict(orient="records")
    )
    dates = pd.to_datetime(df["visit_date"], errors="coerce")
    monthly = dates.dropna().dt.to_period("M").value_counts().sort_index()
    monthly_counts = [{"month": str(month), "visits": int(count)} for month, count in monthly.items()]
    return {
        "total_visits": total,
        "department_counts": department_counts,
        "visit_type_counts": visit_type_counts,
        "monthly_counts": monthly_counts,
        "average_visits_per_department": float(np.mean([x["visits"] for x in department_counts])) if department_counts else 0,
    }

def create_department_chart(records, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    path = out / "summary.png"
    if df.empty or "department" not in df:
        counts = pd.Series(dtype="int64")
    else:
        counts = df["department"].fillna("Unknown").value_counts().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if counts.empty:
        ax.text(0.5, 0.5, "No visit data available", ha="center", va="center")
        ax.set_axis_off()
    else:
        counts.plot(kind="bar", ax=ax)
        ax.set_title("Visits by Department")
        ax.set_xlabel("Department")
        ax.set_ylabel("Number of visits")
        ax.tick_params(axis="x", labelrotation=30)
        fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return str(path)
