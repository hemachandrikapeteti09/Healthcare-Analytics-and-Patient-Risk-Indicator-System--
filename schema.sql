-- Healthcare Analytics and Patient Risk Indicator System
-- Run in MySQL Workbench. Synthetic/demo data only.
CREATE DATABASE IF NOT EXISTS healthcare_analytics_and_patient_risk_indicator_system;
USE healthcare_analytics_and_patient_risk_indicator_system;

CREATE TABLE IF NOT EXISTS patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_code VARCHAR(40) NOT NULL UNIQUE,
    age_band VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS visits (
    visit_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_code VARCHAR(40) NOT NULL,
    department VARCHAR(100) NOT NULL,
    visit_date DATE NOT NULL,
    age_band VARCHAR(30),
    visit_type VARCHAR(60),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_visits_date (visit_date),
    INDEX idx_visits_department (department),
    CONSTRAINT fk_visits_patient_code
      FOREIGN KEY (patient_code) REFERENCES patients(patient_code)
      ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS measurements (
    measurement_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_code VARCHAR(40) NOT NULL,
    measurement_name VARCHAR(100) NOT NULL,
    measurement_value DECIMAL(10,2) NOT NULL,
    measurement_unit VARCHAR(30),
    measured_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_measurements_patient (patient_code),
    CONSTRAINT fk_measurements_patient_code
      FOREIGN KEY (patient_code) REFERENCES patients(patient_code)
      ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS risk_indicators (
    indicator_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_code VARCHAR(40) NOT NULL,
    indicator_name VARCHAR(100) NOT NULL,
    indicator_value DECIMAL(10,2),
    indicator_level ENUM('low','moderate','high','unknown') NOT NULL DEFAULT 'unknown',
    rationale VARCHAR(255),
    assessed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_risk_patient (patient_code),
    CONSTRAINT fk_risk_patient_code
      FOREIGN KEY (patient_code) REFERENCES patients(patient_code)
      ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Synthetic demo records (not real patient data).
INSERT IGNORE INTO patients (patient_code, age_band) VALUES
('DEMO-001', '18-29'), ('DEMO-002', '30-44'), ('DEMO-003', '45-59'),
('DEMO-004', '60+'), ('DEMO-005', '30-44');

INSERT INTO visits (patient_code, department, visit_date, age_band, visit_type)
SELECT 'DEMO-001', 'General Medicine', '2026-01-12', '18-29', 'Outpatient'
WHERE NOT EXISTS (SELECT 1 FROM visits WHERE patient_code='DEMO-001' AND visit_date='2026-01-12' AND department='General Medicine');
INSERT INTO visits (patient_code, department, visit_date, age_band, visit_type)
SELECT 'DEMO-002', 'Cardiology', '2026-01-15', '30-44', 'Follow-up'
WHERE NOT EXISTS (SELECT 1 FROM visits WHERE patient_code='DEMO-002' AND visit_date='2026-01-15' AND department='Cardiology');
INSERT INTO visits (patient_code, department, visit_date, age_band, visit_type)
SELECT 'DEMO-003', 'General Medicine', '2026-02-02', '45-59', 'Outpatient'
WHERE NOT EXISTS (SELECT 1 FROM visits WHERE patient_code='DEMO-003' AND visit_date='2026-02-02' AND department='General Medicine');
INSERT INTO visits (patient_code, department, visit_date, age_band, visit_type)
SELECT 'DEMO-004', 'Orthopedics', '2026-02-10', '60+', 'Follow-up'
WHERE NOT EXISTS (SELECT 1 FROM visits WHERE patient_code='DEMO-004' AND visit_date='2026-02-10' AND department='Orthopedics');
INSERT INTO visits (patient_code, department, visit_date, age_band, visit_type)
SELECT 'DEMO-005', 'Cardiology', '2026-03-05', '30-44', 'Outpatient'
WHERE NOT EXISTS (SELECT 1 FROM visits WHERE patient_code='DEMO-005' AND visit_date='2026-03-05' AND department='Cardiology');
