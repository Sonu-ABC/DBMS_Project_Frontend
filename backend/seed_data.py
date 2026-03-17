# backend/seed_data.py – Populate MongoDB with sample A6 data
"""
Run:  python -m backend.seed_data
"""
import random
from datetime import datetime, timedelta
from backend.db import get_db
from backend.models import (
    insert_patient, insert_vital_sign, insert_alert_rule,
    insert_escalation_pathway, insert_device,
)


def seed():
    db = get_db()

    # ── Clear existing data ───────────────────────────────────────────────
    for col in ["patients", "vital_signs", "alert_rules",
                "escalation_pathways", "monitoring_devices", "alerts"]:
        db[col].delete_many({})
    print("🗑️  Cleared existing collections.")

    # ── Patients ──────────────────────────────────────────────────────────
    patients = [
        {"first_name": "Sarah", "middle_name": "M", "last_name": "Johnson",
         "dob": "1985-06-15", "age": 40, "gender": "Female", "phone_no": "555-0101"},
        {"first_name": "James", "middle_name": "R", "last_name": "Williams",
         "dob": "1972-03-22", "age": 53, "gender": "Male", "phone_no": "555-0102"},
        {"first_name": "Emily", "middle_name": "A", "last_name": "Brown",
         "dob": "1990-11-08", "age": 35, "gender": "Female", "phone_no": "555-0103"},
        {"first_name": "Robert", "middle_name": "T", "last_name": "Davis",
         "dob": "1965-01-30", "age": 61, "gender": "Male", "phone_no": "555-0104"},
        {"first_name": "Maria", "middle_name": "L", "last_name": "Garcia",
         "dob": "2018-07-12", "age": 7, "gender": "Female", "phone_no": "555-0105"},
    ]
    patient_ids = []
    for p in patients:
        pid = insert_patient(p)
        patient_ids.append(pid)
        print(f"  ✅ Patient: {p['first_name']} {p['last_name']}  →  {pid}")

    # ── Monitoring Devices ────────────────────────────────────────────────
    devices = [
        {"device_name": "Philips IntelliVue MX800", "device_type": "Multi-Parameter Monitor",
         "location": "ICU Bed 1", "status": "Active"},
        {"device_name": "GE CARESCAPE B650", "device_type": "Bedside Monitor",
         "location": "ICU Bed 2", "status": "Active"},
        {"device_name": "Masimo Root", "device_type": "SpO2 / Pulse Oximeter",
         "location": "Ward A Room 3", "status": "Active"},
        {"device_name": "Welch Allyn Connex", "device_type": "Vital Signs Monitor",
         "location": "ER Bay 4", "status": "Maintenance"},
    ]
    device_ids = []
    for d in devices:
        did = insert_device(d)
        device_ids.append(did)
        print(f"  ✅ Device: {d['device_name']}  →  {did}")

    # ── Alert Rules ───────────────────────────────────────────────────────
    rules = [
        {"vital_type": "Heart Rate", "min_value": 50, "max_value": 100,
         "severity_level": "Medium", "scoring_system": "NEWS"},
        {"vital_type": "Heart Rate", "min_value": 40, "max_value": 130,
         "severity_level": "Critical", "scoring_system": "NEWS"},
        {"vital_type": "Temperature", "min_value": 36.0, "max_value": 38.0,
         "severity_level": "Medium", "scoring_system": "NEWS"},
        {"vital_type": "Temperature", "min_value": 35.0, "max_value": 39.0,
         "severity_level": "Critical", "scoring_system": "NEWS"},
        {"vital_type": "Systolic BP", "min_value": 100, "max_value": 180,
         "severity_level": "Medium", "scoring_system": "NEWS"},
        {"vital_type": "Systolic BP", "min_value": 90, "max_value": 220,
         "severity_level": "Critical", "scoring_system": "NEWS"},
        {"vital_type": "Respiratory Rate", "min_value": 12, "max_value": 20,
         "severity_level": "Medium", "scoring_system": "NEWS"},
        {"vital_type": "SpO2", "min_value": 95, "max_value": 100,
         "severity_level": "Medium", "scoring_system": "NEWS"},
        {"vital_type": "SpO2", "min_value": 92, "max_value": 100,
         "severity_level": "Critical", "scoring_system": "NEWS"},
        {"vital_type": "Pain Score", "min_value": 0, "max_value": 4,
         "severity_level": "Medium", "scoring_system": "MEWS"},
    ]
    for r in rules:
        rid = insert_alert_rule(r)
        print(f"  ✅ Rule: {r['vital_type']} ({r['severity_level']})  →  {rid}")

    # ── Escalation Pathways ───────────────────────────────────────────────
    pathways = [
        {"pathway_id": "EP-001", "severity_level": "Low",
         "notify_role": "Nurse", "response_time": "30 min",
         "notification_method": "In-App"},
        {"pathway_id": "EP-002", "severity_level": "Medium",
         "notify_role": "Nurse + Resident", "response_time": "15 min",
         "notification_method": "In-App + SMS"},
        {"pathway_id": "EP-003", "severity_level": "High",
         "notify_role": "Attending Physician", "response_time": "5 min",
         "notification_method": "Phone Call + SMS"},
        {"pathway_id": "EP-004", "severity_level": "Critical",
         "notify_role": "Rapid Response Team", "response_time": "Immediate",
         "notification_method": "Overhead Page + Phone + SMS"},
    ]
    for pw in pathways:
        pwid = insert_escalation_pathway(pw)
        print(f"  ✅ Escalation: {pw['severity_level']}  →  {pwid}")

    # ── Vital Signs (time-series for each patient) ────────────────────────
    now = datetime.utcnow()
    vital_count = 0
    for idx, pid in enumerate(patient_ids):
        # 20 readings spread over the last 24 hrs
        for i in range(20):
            ts = now - timedelta(hours=24 - i * 1.2)
            # slightly different baselines per patient
            hr_base = 72 + idx * 5
            temp_base = 36.8 + idx * 0.15
            sbp_base = 118 + idx * 4
            dbp_base = 76 + idx * 2
            rr_base = 16 + idx
            spo2_base = 98 - idx * 0.5

            vitals_doc = {
                "patient_id": pid,
                "device_id": device_ids[idx % len(device_ids)],
                "heart_rate": round(hr_base + random.uniform(-8, 12), 1),
                "temperature": round(temp_base + random.uniform(-0.4, 0.6), 1),
                "systolic_bp": round(sbp_base + random.uniform(-10, 15)),
                "diastolic_bp": round(dbp_base + random.uniform(-5, 8)),
                "respiratory_rate": round(rr_base + random.uniform(-3, 4)),
                "spo2": round(spo2_base + random.uniform(-2, 1), 1),
                "pain_score": random.randint(0, 6),
                "consciousness": random.choice(["Alert"] * 9 + ["Voice"]),
                "recorded_time": ts,
            }
            insert_vital_sign(vitals_doc)
            vital_count += 1

    print(f"  ✅ Inserted {vital_count} vital-sign readings across {len(patient_ids)} patients.")
    print("\n🎉 Seed complete!")


if __name__ == "__main__":
    seed()
