
from collections import Counter
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


# =========================================================
# VISIT ANALYTICS
# =========================================================

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
        df["department"].fillna("Unknown")
        .value_counts()
        .rename_axis("department")
        .reset_index(name="visits")
        .to_dict(orient="records")
    )

    visit_type_counts = (
        df["visit_type"].fillna("Unknown")
        .value_counts()
        .rename_axis("visit_type")
        .reset_index(name="visits")
        .to_dict(orient="records")
    )

    dates = pd.to_datetime(df["visit_date"], errors="coerce")
    monthly = dates.dropna().dt.to_period("M").value_counts().sort_index()

    monthly_counts = [
        {"month": str(month), "visits": int(count)}
        for month, count in monthly.items()
    ]

    return {
        "total_visits": total,
        "department_counts": department_counts,
        "visit_type_counts": visit_type_counts,
        "monthly_counts": monthly_counts,
        "average_visits_per_department": (
            float(np.mean([x["visits"] for x in department_counts]))
            if department_counts else 0
        ),
    }


def create_department_chart(records, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(records)
    path = out / "summary.png"

    if df.empty or "department" not in df.columns:
        counts = pd.Series(dtype="int64")
    else:
        counts = (
            df["department"].fillna("Unknown")
            .value_counts()
            .sort_values(ascending=False)
        )

    fig, ax = plt.subplots(figsize=(8, 4.5))

    if counts.empty:
        ax.text(
            0.5, 0.5, "No visit data available",
            ha="center", va="center"
        )
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


# =========================================================
# MEASUREMENT VALIDATION
# Educational demo only — NOT medical diagnosis.
# These are illustrative plausibility bounds, not clinical limits.
# =========================================================

SAMPLE_MEASUREMENT_RANGES = {
    "heart_rate": {"min": 20, "max": 250, "unit": "bpm"},
    "temperature": {"min": 30, "max": 45, "unit": "C"},
    "systolic_bp": {"min": 50, "max": 300, "unit": "mmHg"},
    "spo2": {"min": 50, "max": 100, "unit": "%"},
    "oxygen_saturation": {"min": 50, "max": 100, "unit": "%"},
}


def validate_measurements(records):
    """Flag values outside configured demo plausibility bounds."""
    results = []

    for record in records:
        item = dict(record)

        name = str(
            item.get("measurement_name", item.get("measure_type", ""))
        ).strip().lower().replace(" ", "_")

        try:
            value = float(
                item.get("measurement_value", item.get("value"))
            )
        except (TypeError, ValueError):
            item["validation_status"] = "invalid_value"
            item["validation_note"] = "Value is missing or not numeric."
            results.append(item)
            continue

        if not np.isfinite(value):
            item["numeric_value"] = value
            item["validation_status"] = "invalid_value"
            item["validation_note"] = "Value must be finite."
            results.append(item)
            continue

        item["numeric_value"] = value
        bounds = SAMPLE_MEASUREMENT_RANGES.get(name)

        if bounds is None:
            item["validation_status"] = "unconfigured_measurement"
            item["validation_note"] = (
                "No demo range configured; value was not range-checked."
            )
        elif not bounds["min"] <= value <= bounds["max"]:
            item["validation_status"] = "outside_demo_range"
            item["validation_note"] = (
                f"Outside demo range "
                f"({bounds['min']}–{bounds['max']} {bounds['unit']})."
            )
        else:
            item["validation_status"] = "within_demo_range"
            item["validation_note"] = (
                "Within demo range; this does not imply health."
            )

        results.append(item)

    return results


# =========================================================
# ILLUSTRATIVE DATA-REVIEW INDICATORS
# NOT a clinical risk score or medical diagnosis.
# =========================================================

def build_illustrative_indicators(measurement_records):
    validated = validate_measurements(measurement_records)
    counts = Counter()

    for item in validated:
        patient = item.get("patient_code", item.get("patient_id"))

        if patient is None:
            continue

        if item["validation_status"] in (
            "outside_demo_range",
            "invalid_value",
        ):
            counts[str(patient)] += 1

    indicators = []

    for patient, count in sorted(counts.items()):
        indicators.append({
            "patient_id": patient,
            "rule_code": "DEMO_DATA_REVIEW_COUNT",
            "indicator_value": int(count),
            "indicator_level": (
                "review_multiple" if count >= 2 else "review_one"
            ),
            "rationale": (
                f"{count} measurement record(s) need data review. "
                "This is not a medical risk assessment."
            ),
        })

    return {
        "indicator_count": len(indicators),
        "indicator_distribution": dict(
            Counter(item["indicator_level"] for item in indicators)
        ),
        "indicators": indicators,
        "limitations": (
            "Educational demo only. These rules are not clinically "
            "validated and must not guide patient care."
        ),
    }


# =========================================================
# MEASUREMENT SUMMARY AND MONTHLY TRENDS
# =========================================================

def build_measurement_summary(records):
    """Summarize numeric measurements by type using Pandas and NumPy."""
    df = pd.DataFrame(records)

    if df.empty:
        return {
            "total_measurements": 0,
            "measurement_type_counts": [],
            "numeric_summary": [],
            "monthly_trends": [],
        }

    type_col = (
        "measurement_name"
        if "measurement_name" in df.columns
        else "measure_type"
    )
    value_col = (
        "measurement_value"
        if "measurement_value" in df.columns
        else "value"
    )
    date_col = (
        "measured_at"
        if "measured_at" in df.columns
        else "measurement_date"
    )

    if type_col not in df.columns:
        df[type_col] = "Unknown"

    if value_col not in df.columns:
        df[value_col] = np.nan

    df[type_col] = df[type_col].fillna("Unknown")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

    numeric_summary = []

    for name, group in df.groupby(type_col):
        values = group[value_col].dropna().to_numpy(dtype=float)

        numeric_summary.append({
            "measure_type": str(name),
            "valid_numeric_values": int(len(values)),
            "mean": float(np.mean(values)) if len(values) else None,
            "minimum": float(np.min(values)) if len(values) else None,
            "maximum": float(np.max(values)) if len(values) else None,
        })

    monthly_trends = []

    if date_col in df.columns:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        df["_month"] = dates.dt.to_period("M").astype("string")

        monthly = (
            df.dropna(subset=["_month"])
            .groupby(["_month", type_col])[value_col]
            .mean()
            .reset_index()
        )

        for _, row in monthly.iterrows():
            monthly_trends.append({
                "month": str(row["_month"]),
                "measure_type": str(row[type_col]),
                "mean_value": (
                    float(row[value_col])
                    if pd.notna(row[value_col]) else None
                ),
            })

    type_counts = (
        df[type_col]
        .value_counts()
        .rename_axis("measure_type")
        .reset_index(name="measurements")
        .to_dict(orient="records")
    )

    return {
        "total_measurements": int(len(df)),
        "measurement_type_counts": type_counts,
        "numeric_summary": numeric_summary,
        "monthly_trends": monthly_trends,
    }
