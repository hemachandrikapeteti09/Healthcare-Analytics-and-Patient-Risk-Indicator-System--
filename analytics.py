
import numpy as np

# ---------------------------------------------------------
# Measurement validation and illustrative indicators
# Educational analytics only — NOT medical diagnosis.
# These are demo plausibility bounds, not clinical limits.
# ---------------------------------------------------------

SAMPLE_MEASUREMENT_RANGES = {
    "heart_rate": {"min": 20, "max": 250, "unit": "bpm"},
    "temperature": {"min": 30, "max": 45, "unit": "C"},
    "systolic_bp": {"min": 50, "max": 300, "unit": "mmHg"},
    "oxygen_saturation": {"min": 50, "max": 100, "unit": "%"},
}


def validate_measurements(records):
    """Flag values outside documented demo plausibility bounds."""
    results = []

    for record in records:
        item = dict(record)
        measure_type = str(
            item.get("measure_type", item.get("measurement_name", ""))
        ).strip().lower().replace(" ", "_")

        try:
            value = float(
                item.get("value", item.get("measurement_value"))
            )
        except (TypeError, ValueError):
            item["validation_status"] = "invalid_value"
            item["validation_note"] = "Value is missing or not numeric."
            results.append(item)
            continue

        item["numeric_value"] = value
        bounds = SAMPLE_MEASUREMENT_RANGES.get(measure_type)

        if bounds is None:
            item["validation_status"] = "unconfigured_measurement"
            item["validation_note"] = (
                "No demo range configured; value was not range-checked."
            )
        elif not np.isfinite(value):
            item["validation_status"] = "invalid_value"
            item["validation_note"] = "Value must be finite."
        elif not bounds["min"] <= value <= bounds["max"]:
            item["validation_status"] = "outside_demo_range"
            item["validation_note"] = (
                f"Outside demo plausibility bounds "
                f"({bounds['min']}–{bounds['max']} {bounds['unit']})."
            )
        else:
            item["validation_status"] = "within_demo_range"
            item["validation_note"] = (
                "Within demo plausibility bounds; this does not imply health."
            )

        results.append(item)

    return results


def build_illustrative_indicators(measurement_records):
    """
    Count measurements outside configured demo bounds per patient.
    This is a data-quality review indicator, NOT a clinical risk score.
    """
    validated = validate_measurements(measurement_records)
    counts = Counter()

    for item in validated:
        patient = item.get("patient_id", item.get("patient_code"))
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
                f"{count} measurement record(s) were outside demo "
                "plausibility bounds or had invalid values. "
                "This is not a medical risk assessment."
            ),
        })

    return {
        "indicator_count": len(indicators),
        "indicator_distribution": dict(
            Counter(x["indicator_level"] for x in indicators)
        ),
        "indicators": indicators,
        "limitations": (
            "Educational synthetic-data demo only. These rules are "
            "not clinically validated and must not guide patient care."
        ),
    }


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
        "measure_type"
        if "measure_type" in df.columns
        else "measurement_name"
    )
    value_col = (
        "value"
        if "value" in df.columns
        else "measurement_value"
    )
    date_col = (
        "measurement_date"
        if "measurement_date" in df.columns
        else "measured_at"
    )

    if type_col not in df.columns:
        df[type_col] = "Unknown"
    if value_col not in df.columns:
        df[value_col] = np.nan

    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df[type_col] = df[type_col].fillna("Unknown")

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
        monthly_trends = [
            {
                "month": str(row["_month"]),
                "measure_type": str(row[type_col]),
                "mean_value": (
                    float(row[value_col])
                    if pd.notna(row[value_col])
                    else None
                ),
            }
            for _, row in monthly.iterrows()
        ]

    type_counts = (
        df[type_col].value_counts()
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
