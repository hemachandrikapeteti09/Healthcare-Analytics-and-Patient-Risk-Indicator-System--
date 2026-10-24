# Healthcare Analytics and Patient Risk Indicator System

Educational Flask + MySQL project for operational visit analytics. Uses synthetic demo records only; indicators are illustrative and not medical diagnoses.

## Features
- Flask dashboard for visit summaries and recent records
- MySQL database schema for patients, visits, measurements and risk indicators
- REST-style endpoints to check health, list/create visits, view analytics and generate a chart
- Pandas/NumPy descriptive statistics and Matplotlib chart generation
- Parameterized SQL and basic input validation

## Requirements
- Python 3.11+
- MySQL Server and MySQL Workbench
- VS Code (recommended)

## Windows setup
1. Open this folder in VS Code.
2. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`.
3. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. In MySQL Workbench, open and execute `schema.sql`.
5. Copy `.env.example` to `.env`, then enter your local MySQL password in `DB_PASSWORD`. Change `FLASK_SECRET_KEY` to a long random value. Never commit `.env`.
6. Start the app:
   ```powershell
   python app.py
   ```
7. Open http://127.0.0.1:5000 in your browser.

## API
- `GET /api/health` — database connection status
- `GET /api/records?limit=100` — list up to 500 visits
- `POST /api/records` — create a visit (JSON body)
- `GET /api/analytics` — descriptive summaries
- `POST /api/chart` — generate a chart at `/static/charts/summary.png`

Example JSON body for `POST /api/records`:
```json
{
  "patient_code": "DEMO-001",
  "department": "General Medicine",
  "visit_date": "2026-03-12",
  "age_band": "18-29",
  "visit_type": "Outpatient"
}
```
The patient code must exist in the `patients` table.

## Safety and limitations
Use fictional or approved data only. This app does not diagnose, recommend treatment, or provide validated clinical risk predictions. Risk indicator rows are illustrative records, not clinical decisions. Keep passwords and secrets in `.env`; commit `.env.example` only.
