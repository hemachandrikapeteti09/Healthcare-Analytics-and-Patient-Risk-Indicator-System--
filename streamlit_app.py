
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Healthcare Analytics",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Healthcare Analytics & Patient Risk Indicator System")
st.caption("Educational demo using synthetic data — not for medical diagnosis.")

st.info(
    "This dashboard uses sample data for demonstration. "
    "It is not connected to your MySQL database yet."
)

visits = pd.DataFrame({
    "Department": [
        "General Medicine",
        "General Medicine",
        "General Medicine",
        "Cardiology",
        "Cardiology",
        "Orthopedics"
    ],
    "Visit Type": [
        "Outpatient",
        "Inpatient",
        "Outpatient",
        "Outpatient",
        "Inpatient",
        "Outpatient"
    ]
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

st.subheader("Sample Visit Records")
st.dataframe(visits, use_container_width=True)

st.subheader("About This Project")
st.write(
    "This project demonstrates healthcare visit analytics, "
    "department trends, and educational patient-risk indicators. "
    "All displayed records are synthetic sample data."
)
