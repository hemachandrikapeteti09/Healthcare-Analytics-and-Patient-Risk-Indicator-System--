
import streamlit as st
import pandas as pd
import numpy as np
import mysql.connector
from pathlib import Path
from analytics import (
    validate_measurements,
    build_illustrative_indicators,
    build_measurement_summary,
)

st.set_page_config(
    page_title="Healthcare Analytics",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 Healthcare Analytics & Patient Risk Indicator System")
st.warning(
    "Educational synthetic-data demo only. "
    "Indicators are not medical diagnoses and must not guide patient care."
)


@st.cache_data(ttl=60)
def load_data():
    config = st.secrets["mysql"]
    connection = mysql.connector.connect(
        host=config["host"],
        port=int(config["port"]),
        user=config["user"],
        password=config["password"],
        database=config["database"],
        ssl_ca=str(Path(__file__).parent / "ca.pem"),
        ssl_verify_cert=True,
        ssl_verify_identity=True,
        connection_timeout=15,
    )
    try:
        visits = pd.read_sql(
            """
            SELECT patient_code, department, visit_date,
                   age_band, visit_type
            FROM visits
            ORDER BY visit_date
            """,
            connection,
        )

        measurements = pd.read_sql(
            """
            SELECT patient_code, measurement_name,
                   measurement_value, measurement_unit, measured_at
            FROM measurements
            ORDER BY measured_at
            """,
            connection,
        )
        return visits, measurements
    finally:
        connection.close()


try:
    visits, measurements = load_data()
except Exception as error:
    st.error("Could not load database records.")
    st.caption(
        "Check Streamlit Secrets, ca.pem, database table names, "
        "and analytics.py."
    )
    st.code(str(error))
    st.stop()


# ---------------- VISIT ANALYTICS ----------------
st.header("1. Operational Analytics")

c1, c2, c3 = st.columns(3)
c1.metric("Total Visits", len(visits))
c2.metric(
    "Departments",
    visits["department"].nunique() if not visits.empty else 0,
)
c3.metric(
    "Visit Types",
    visits["visit_type"].nunique() if not visits.empty else 0,
)

if not visits.empty:
    department_counts = (
        visits["department"].fillna("Unknown")
        .value_counts()
        .rename_axis("Department")
        .reset_index(name="Visits")
    )
    st.subheader("Department-wise Visits")
    st.bar_chart(department_counts, x="Department", y="Visits")

    monthly = visits.copy()
    monthly["visit_date"] = pd.to_datetime(
        monthly["visit_date"], errors="coerce"
    )
    monthly = monthly.dropna(subset=["visit_date"])
    if not monthly.empty:
        monthly["Month"] = monthly["visit_date"].dt.to_period("M").astype(str)
        trend = monthly.groupby("Month").size().reset_index(name="Visits")
        st.subheader("Monthly Visit Trend")
        st.line_chart(trend, x="Month", y="Visits")

    st.subheader("Live Visit Records")
    st.dataframe(visits, use_container_width=True)
else:
    st.info("No visit records found.")


# ---------------- MEASUREMENTS ----------------
st.header("2. Measurement Analytics")

st.metric("Total Measurement Records", len(measurements))

if measurements.empty:
    st.info(
        "No measurement records exist in the database yet. "
        "Add synthetic demonstration records to see validation and trends."
    )
else:
    measurement_records = measurements.rename(
        columns={
            "patient_code": "patient_code",
            "measurement_name": "measurement_name",
            "measurement_value": "measurement_value",
            "measured_at": "measured_at",
        }
    ).to_dict(orient="records")

    validation = validate_measurements(measurement_records)
    validation_df = pd.DataFrame(validation)

    st.subheader("Measurement Validation")
    st.caption(
        "Demo plausibility bounds are assumptions for this project, "
        "not clinical reference ranges."
    )

    if "validation_status" in validation_df.columns:
        st.dataframe(
            validation_df,
            use_container_width=True,
            hide_index=True,
        )
        st.bar_chart(
            validation_df["validation_status"].value_counts()
            .rename_axis("Status")
            .reset_index(name="Records"),
            x="Status",
            y="Records",
        )

    summary = build_measurement_summary(measurement_records)
    st.subheader("Measurement Summary")

    summary_df = pd.DataFrame(summary["numeric_summary"])
    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True)
        chart_df = summary_df.dropna(subset=["mean"])
        if not chart_df.empty:
            st.subheader("Average Measurement Values")
            st.bar_chart(chart_df, x="measure_type", y="mean")

    trend_df = pd.DataFrame(summary["monthly_trends"])
    if not trend_df.empty:
        st.subheader("Measurement Trends by Month")
        for measure_type in trend_df["measure_type"].unique():
            one_type = trend_df[
                trend_df["measure_type"] == measure_type
            ].dropna(subset=["mean_value"])
            if not one_type.empty:
                st.caption(str(measure_type))
                st.line_chart(
                    one_type,
                    x="month",
                    y="mean_value",
                )

    st.subheader("Illustrative Data-Review Indicators")
    indicator_report = build_illustrative_indicators(
        measurement_records
    )
    st.metric(
        "Patients Flagged for Data Review",
        indicator_report["indicator_count"],
    )

    distribution = indicator_report["indicator_distribution"]
    if distribution:
        distribution_df = pd.DataFrame(
            list(distribution.items()),
            columns=["Indicator Category", "Count"],
        )
        st.bar_chart(
            distribution_df,
            x="Indicator Category",
            y="Count",
        )
    else:
        st.info("No measurement records were flagged by the demo rules.")

    st.dataframe(
        pd.DataFrame(indicator_report["indicators"]),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(indicator_report["limitations"])


# ---------------- LIMITATIONS ----------------
st.header("3. Limitations and Data Privacy")
st.write(
    """
    - Use synthetic or properly de-identified records only.
    - Demo measurement bounds are not clinical reference ranges.
    - The illustrative indicator counts data records for review; it is
      not a validated medical risk score.
    - No diagnosis or treatment recommendation is provided.
    - Restrict access to the app and database; do not expose credentials.
    """
)

if st.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()
