
import streamlit as st
import pandas as pd
import mysql.connector
from pathlib import Path

st.set_page_config(
    page_title="Healthcare Analytics",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Healthcare Analytics & Patient Risk Indicator System")
st.caption("Educational demo using synthetic data — not for medical diagnosis.")


@st.cache_data(ttl=60)
def load_visits():
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
        connection_timeout=15
    )

    try:
        query = """
            SELECT patient_code, department, visit_date,
                   age_band, visit_type
            FROM visits
            ORDER BY visit_date
        """
        return pd.read_sql(query, connection)
    finally:
        connection.close()


try:
    visits = load_visits()
except Exception as error:
    st.error(
        "Database connection failed. Check Streamlit Secrets, "
        "the ca.pem certificate file, and the database connection."
    )
    st.caption(f"Technical details: {error}")
    st.stop()

visits = visits.rename(columns={
    "patient_code": "Patient Code",
    "department": "Department",
    "visit_date": "Visit Date",
    "age_band": "Age Band",
    "visit_type": "Visit Type"
})

col1, col2, col3 = st.columns(3)

col1.metric("Total Visits", len(visits))
col2.metric("Departments", visits["Department"].nunique())
col3.metric("Visit Types", visits["Visit Type"].nunique())

st.subheader("Department-wise Visits")

department_counts = (
    visits["Department"]
    .value_counts()
    .rename_axis("Department")
    .reset_index(name="Visits")
)

st.bar_chart(
    department_counts,
    x="Department",
    y="Visits"
)

st.subheader("Live Visit Records")
st.dataframe(visits, use_container_width=True)

st.subheader("About This Project")
st.write(
    "This dashboard reads synthetic demonstration records from "
    "the connected MySQL database. Patient-risk indicators are "
    "educational only and are not medical diagnoses."
)
