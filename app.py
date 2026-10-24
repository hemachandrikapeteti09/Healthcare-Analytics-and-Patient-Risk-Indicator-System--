
import os
import math
from datetime import date, datetime

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

from analytics import build_summary, create_department_chart

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY", "local-development-only-change-me"
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv(
        "DB_NAME",
        "healthcare_analytics_and_patient_risk_indicator_system"
    ),
}

# Synthetic educational data validation bounds only.
# These are NOT medical reference ranges or diagnostic criteria.
MEASUREMENT_BOUNDS = {
    "heart_rate": (1, 300, "bpm"),
    "temperature": (25, 45, "C"),
    "spo2": (1, 100, "%"),
    "systolic_bp": (1, 300, "mmHg"),
    "diastolic_bp": (1, 200, "mmHg"),
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def row_to_dict(row):
    result = dict(row)
    for key, value in result.items():
        if hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        elif isinstance(value, (int, float)):
            result[key] = value
    return result


def error_response(message, status=400):
    return jsonify(error=message), status


def parse_json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


def patient_exists(cursor, patient_code):
    cursor.execute(
        "SELECT patient_code FROM patients WHERE patient_code = %s",
        (patient_code,)
    )
    return cursor.fetchone() is not None


@app.get("/")
def index():
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT visit_id, patient_code, department, visit_date,
                       age_band, visit_type
                FROM visits
                ORDER BY visit_date DESC, visit_id DESC
                LIMIT 10
            """)
            visits = [row_to_dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT COUNT(*) AS total FROM visits")
            total_visits = cursor.fetchone()["total"]

            cursor.execute("""
                SELECT department, COUNT(*) AS visits
                FROM visits
                GROUP BY department
                ORDER BY visits DESC
            """)
            by_department = cursor.fetchall()
            departments = [row["department"] for row in by_department]

            cursor.execute("SELECT COUNT(*) AS total FROM patients")
            total_patients = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM measurements")
            total_measurements = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM risk_indicators")
            total_indicators = cursor.fetchone()["total"]

            cursor.close()

        summary = {
            "total_visits": total_visits,
            "departments": departments,
            "by_department": by_department,
            "total_patients": total_patients,
            "total_measurements": total_measurements,
            "total_indicators": total_indicators,
        }

        return render_template(
            "index.html", visits=visits, summary=summary, db_ok=True
        )

    except Error:
        app.logger.exception("Dashboard database query failed")
        return render_template(
            "index.html",
            visits=[],
            summary={
                "total_visits": 0,
                "departments": [],
                "by_department": [],
                "total_patients": 0,
                "total_measurements": 0,
                "total_indicators": 0,
            },
            db_ok=False,
            error="Check MySQL connection and database tables."
        ), 503


@app.get("/api/health")
def health():
    try:
        with get_connection() as conn:
            conn.ping(reconnect=True, attempts=1, delay=0)
        return jsonify(status="ok", database="connected")
    except Error:
        app.logger.exception("Database health check failed")
        return jsonify(status="error", database="unavailable"), 503


# ---------------- PATIENT RECORDS ----------------

@app.get("/api/patients")
def get_patients():
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)

        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT patient_id, patient_code, age_band, created_at
                FROM patients
                ORDER BY patient_id DESC
                LIMIT %s
            """, (limit,))
            records = [row_to_dict(row) for row in cursor.fetchall()]
            cursor.close()

        return jsonify(records=records, count=len(records))

    except ValueError:
        return error_response("limit must be a number", 400)
    except Error:
        app.logger.exception("Could not fetch patients")
        return error_response("Could not fetch patients", 503)


@app.post("/api/patients")
def create_patient():
    data = parse_json_object()
    if data is None:
        return error_response("Send a JSON object", 400)

    patient_code = str(data.get("patient_code", "")).strip()
    age_band = str(data.get("age_band", "")).strip() or None

    if not patient_code:
        return error_response("patient_code is required", 400)
    if len(patient_code) > 40:
        return error_response("patient_code must be at most 40 characters", 400)
    if age_band and age_band not in {
        "Under 18", "18-29", "30-44", "45-59", "60+"
    }:
        return error_response("Unsupported age_band", 400)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO patients (patient_code, age_band)
                VALUES (%s, %s)
            """, (patient_code, age_band))
            new_id = cursor.lastrowid
            conn.commit()
            cursor.close()

        return jsonify(
            message="Synthetic patient created",
            patient_id=new_id,
            patient_code=patient_code
        ), 201

    except Error as exc:
        if getattr(exc, "errno", None) == 1062:
            return error_response("patient_code already exists", 409)
        app.logger.exception("Could not create patient")
        return error_response("Could not create patient; check database settings", 503)


# ---------------- VISIT RECORDS ----------------

@app.get("/api/records")
def get_records():
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)

        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT visit_id, patient_code, department, visit_date,
                       age_band, visit_type
                FROM visits
                ORDER BY visit_date DESC, visit_id DESC
                LIMIT %s
            """, (limit,))
            records = [row_to_dict(row) for row in cursor.fetchall()]
            cursor.close()

        return jsonify(records=records, count=len(records))

    except ValueError:
        return error_response("limit must be a number", 400)
    except Error:
        app.logger.exception("Could not fetch visits")
        return error_response("Could not fetch visits", 503)


@app.post("/api/records")
def create_record():
    data = parse_json_object()
    if data is None:
        return error_response("Send a JSON object", 400)

    required = ["patient_code", "department", "visit_date"]
    missing = [
        key for key in required
        if data.get(key) is None or not str(data[key]).strip()
    ]
    if missing:
        return jsonify(error="Missing required fields", fields=missing), 400

    patient_code = str(data["patient_code"]).strip()
    department = str(data["department"]).strip()
    age_band = str(data.get("age_band", "")).strip() or None
    visit_type = str(data.get("visit_type", "")).strip() or None

    if len(patient_code) > 40 or len(department) > 100:
        return error_response("patient_code or department is too long", 400)

    try:
        visit_date = date.fromisoformat(str(data["visit_date"]))
    except ValueError:
        return error_response("visit_date must use YYYY-MM-DD format", 400)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            if not patient_exists(cursor, patient_code):
                cursor.close()
                return error_response(
                    "Patient code does not exist. Create a synthetic patient first.",
                    400
                )

            cursor.execute("""
                INSERT INTO visits
                    (patient_code, department, visit_date, age_band, visit_type)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                patient_code, department, visit_date, age_band, visit_type
            ))
            new_id = cursor.lastrowid
            conn.commit()
            cursor.close()

        return jsonify(message="Visit created", visit_id=new_id), 201

    except Error:
        app.logger.exception("Could not create visit")
        return error_response("Could not create visit; check database settings", 503)


# ---------------- MEASUREMENT RECORDS ----------------

@app.get("/api/measurements")
def get_measurements():
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)

        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT measurement_id, patient_code, measurement_name,
                       measurement_value, measurement_unit, measured_at
                FROM measurements
                ORDER BY measured_at DESC, measurement_id DESC
                LIMIT %s
            """, (limit,))
            records = [row_to_dict(row) for row in cursor.fetchall()]
            cursor.close()

        return jsonify(records=records, count=len(records))

    except ValueError:
        return error_response("limit must be a number", 400)
    except Error:
        app.logger.exception("Could not fetch measurements")
        return error_response("Could not fetch measurements", 503)


@app.post("/api/measurements")
def create_measurement():
    data = parse_json_object()
    if data is None:
        return error_response("Send a JSON object", 400)

    required = [
        "patient_code", "measurement_name",
        "measurement_value", "measured_at"
    ]
    missing = [
        key for key in required
        if data.get(key) is None or str(data[key]).strip() == ""
    ]
    if missing:
        return jsonify(error="Missing required fields", fields=missing), 400

    patient_code = str(data["patient_code"]).strip()
    name = str(data["measurement_name"]).strip().lower()
    unit = str(data.get("measurement_unit", "")).strip() or None

    if len(patient_code) > 40 or len(name) > 100:
        return error_response("Patient code or measurement name is too long", 400)

    if name not in MEASUREMENT_BOUNDS:
        return jsonify(
            error="Unsupported measurement name",
            allowed_names=list(MEASUREMENT_BOUNDS.keys())
        ), 400

    try:
        value = float(data["measurement_value"])
        if not math.isfinite(value):
            raise ValueError
    except (ValueError, TypeError):
        return error_response("measurement_value must be a finite number", 400)

    low, high, default_unit = MEASUREMENT_BOUNDS[name]
    if not low <= value <= high:
        return jsonify(
            error="Value is outside the documented sample validation bounds",
            allowed_range=[low, high],
            note="These are educational data bounds, not medical reference ranges."
        ), 400

    try:
        measured_at = datetime.fromisoformat(
            str(data["measured_at"]).replace("Z", "+00:00")
        ).replace(tzinfo=None)
    except ValueError:
        return error_response(
            "measured_at must be an ISO date/time, e.g. 2026-03-05T10:30:00",
            400
        )

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            if not patient_exists(cursor, patient_code):
                cursor.close()
                return error_response(
                    "Patient code does not exist. Create a synthetic patient first.",
                    400
                )

            cursor.execute("""
                INSERT INTO measurements
                    (patient_code, measurement_name, measurement_value,
                     measurement_unit, measured_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                patient_code, name, value, unit or default_unit, measured_at
            ))
            new_id = cursor.lastrowid
            conn.commit()
            cursor.close()

        return jsonify(
            message="Synthetic measurement created",
            measurement_id=new_id,
            note="Educational validation only; not a clinical assessment."
        ), 201

    except Error:
        app.logger.exception("Could not create measurement")
        return error_response("Could not save measurement", 503)


# ---------------- RULE-BASED INDICATORS ----------------

@app.get("/api/indicators")
def get_indicators():
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)

        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT indicator_id, patient_code, indicator_name,
                       indicator_value, indicator_level, rationale, assessed_at
                FROM risk_indicators
                ORDER BY assessed_at DESC, indicator_id DESC
                LIMIT %s
            """, (limit,))
            records = [row_to_dict(row) for row in cursor.fetchall()]
            cursor.close()

        return jsonify(
            records=records,
            count=len(records),
            note="Illustrative indicators only; not diagnoses or clinical advice."
        )

    except ValueError:
        return error_response("limit must be a number", 400)
    except Error:
        app.logger.exception("Could not fetch indicators")
        return error_response("Could not fetch indicators", 503)


@app.post("/api/indicators/evaluate")
def evaluate_indicators():
    data = parse_json_object()
    if data is None:
        return error_response("Send a JSON object", 400)

    patient_code = str(data.get("patient_code", "")).strip()
    if not patient_code:
        return error_response("patient_code is required", 400)

    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            if not patient_exists(cursor, patient_code):
                cursor.close()
                return error_response("Patient code does not exist", 404)

            cursor.execute("""
                SELECT measurement_name, measurement_value, measured_at
                FROM measurements
                WHERE patient_code = %s
                ORDER BY measured_at DESC, measurement_id DESC
            """, (patient_code,))
            measurements = cursor.fetchall()

            # Use the latest recorded value for each measurement type.
            latest = {}
            for record in measurements:
                latest.setdefault(
                    record["measurement_name"],
                    float(record["measurement_value"])
                )

            indicators = []

            # Illustrative thresholds for demonstrating transparent rules.
            # They are NOT clinically validated and must not guide care.
            if "spo2" in latest:
                value = latest["spo2"]
                if value < 90:
                    level, rationale = "high", "Demo rule: SpO2 sample value below 90"
                elif value < 95:
                    level, rationale = "moderate", "Demo rule: SpO2 sample value below 95"
                else:
                    level, rationale = "low", "Demo rule: SpO2 sample value at least 95"

                indicators.append((
                    "spo2_demo_rule", value, level, rationale
                ))

            if "heart_rate" in latest:
                value = latest["heart_rate"]
                if value < 50 or value > 120:
                    level, rationale = "high", "Demo rule: heart rate outside illustrative 50-120 band"
                elif value < 60 or value > 100:
                    level, rationale = "moderate", "Demo rule: heart rate outside illustrative 60-100 band"
                else:
                    level, rationale = "low", "Demo rule: heart rate within illustrative 60-100 band"

                indicators.append((
                    "heart_rate_demo_rule", value, level, rationale
                ))

            if not indicators:
                cursor.close()
                return jsonify(
                    patient_code=patient_code,
                    indicators=[],
                    message="No supported measurements found for these demo rules.",
                    note="No clinical conclusion can be drawn."
                )

            created = []
            for name, value, level, rationale in indicators:
                cursor.execute("""
                    INSERT INTO risk_indicators
                        (patient_code, indicator_name, indicator_value,
                         indicator_level, rationale)
                    VALUES (%s, %s, %s, %s, %s)
                """, (patient_code, name, value, level, rationale))
                created.append({
                    "indicator_id": cursor.lastrowid,
                    "indicator_name": name,
                    "indicator_value": value,
                    "indicator_level": level,
                    "rationale": rationale,
                })

            conn.commit()
            cursor.close()

        return jsonify(
            patient_code=patient_code,
            indicators=created,
            note="Illustrative educational rules only. Not diagnoses or clinical advice."
        ), 201

    except Error:
        app.logger.exception("Could not evaluate indicators")
        return error_response("Could not evaluate indicators", 503)


# ---------------- ANALYTICS AND CHARTS ----------------

@app.get("/api/analytics")
def analytics():
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT department, visit_date, age_band, visit_type
                FROM visits
                ORDER BY visit_date
            """)
            records = [row_to_dict(row) for row in cursor.fetchall()]
            cursor.close()

        return jsonify(build_summary(records))

    except Error:
        app.logger.exception("Could not calculate analytics")
        return error_response("Could not calculate analytics", 503)


@app.get("/api/analytics/measurements")
def measurement_analytics():
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT measurement_name, measured_at,
                       measurement_value, measurement_unit
                FROM measurements
                ORDER BY measured_at
            """)
            rows = cursor.fetchall()
            cursor.close()

        groups = {}
        for row in rows:
            name = row["measurement_name"]
            groups.setdefault(name, []).append({
                "measured_at": row["measured_at"].isoformat(),
                "value": float(row["measurement_value"]),
                "unit": row["measurement_unit"],
            })

        return jsonify(
            measurement_trends=groups,
            count=len(rows),
            note="Descriptive synthetic-data summaries only."
        )

    except Error:
        app.logger.exception("Could not calculate measurement trends")
        return error_response("Could not calculate measurement trends", 503)


@app.get("/api/analytics/indicators")
def indicator_analytics():
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT indicator_name, indicator_level, COUNT(*) AS count
                FROM risk_indicators
                GROUP BY indicator_name, indicator_level
                ORDER BY indicator_name, indicator_level
            """)
            rows = cursor.fetchall()
            cursor.close()

        return jsonify(
            indicator_distribution=rows,
            note="Counts of illustrative rules only; not clinical validity claims."
        )

    except Error:
        app.logger.exception("Could not summarize indicators")
        return error_response("Could not summarize indicators", 503)


@app.post("/api/chart")
def chart():
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT department FROM visits")
            records = cursor.fetchall()
            cursor.close()

        path = create_department_chart(
            records, os.path.join(app.root_path, "static", "charts")
        )

        return jsonify(
            message="Department chart created",
            url="/static/charts/summary.png",
            records=len(records)
        )

    except Error:
        app.logger.exception("Could not create chart")
        return error_response("Could not create chart", 503)


if __name__ == "__main__":
    # Local development only. Do not expose this server publicly.
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=os.getenv("FLASK_DEBUG", "0") == "1"
    )
