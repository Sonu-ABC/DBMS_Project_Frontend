# backend/alert_engine.py – Threshold-based alerting with escalation
from datetime import datetime
from backend.db import get_db
from backend.models import (
    get_alert_rules,
    insert_alert,
    get_alerts,
    get_escalation_pathways,
)
from backend.ews import calculate_news


# Vital-type → field name in a vitals document
VITAL_FIELDS = {
    "Heart Rate": "heart_rate",
    "Temperature": "temperature",
    "Systolic BP": "systolic_bp",
    "Diastolic BP": "diastolic_bp",
    "Respiratory Rate": "respiratory_rate",
    "SpO2": "spo2",
    "Pain Score": "pain_score",
}


def evaluate_vitals(patient_id: str, vitals: dict):
    """
    Check a vitals dict against every active AlertRule.
    Creates Alert documents for any violations.
    Returns a list of newly created alert dicts.
    """
    rules = get_alert_rules({"scoring_system": {"$exists": True}})
    if not rules:
        rules = get_alert_rules()

    fired = []
    for rule in rules:
        vtype = rule.get("vital_type", "")
        field = VITAL_FIELDS.get(vtype)
        if not field or field not in vitals:
            continue

        value = vitals[field]
        min_val = rule.get("min_value")
        max_val = rule.get("max_value")
        severity = rule.get("severity_level", "Medium")

        violated = False
        if min_val is not None and value < min_val:
            violated = True
        if max_val is not None and value > max_val:
            violated = True

        if violated:
            alert_doc = {
                "patient_id": patient_id,
                "vital_type": vtype,
                "value": value,
                "rule_id": str(rule["_id"]),
                "severity_level": severity,
                "message": f"{vtype} = {value} is outside range [{min_val}, {max_val}]",
                "status": "Active",
                "created_at": datetime.utcnow(),
            }
            # attach escalation if exists
            pathways = get_escalation_pathways({"severity_level": severity})
            if pathways:
                pw = pathways[0]
                alert_doc["escalation"] = {
                    "notify_role": pw.get("notify_role"),
                    "response_time": pw.get("response_time"),
                    "notification_method": pw.get("notification_method"),
                }
            insert_alert(alert_doc)
            fired.append(alert_doc)

    return fired


def evaluate_ews_for_vitals(patient_id: str, vitals: dict):
    """
    Compute NEWS score and fire an alert if score is Medium or above.
    Returns (score, severity) tuple.
    """
    hr = vitals.get("heart_rate", 80)
    rr = vitals.get("respiratory_rate", 16)
    spo2 = vitals.get("spo2", 98)
    temp = vitals.get("temperature", 37.0)
    sbp = vitals.get("systolic_bp", 120)
    consciousness = vitals.get("consciousness", "Alert")

    score, severity = calculate_news(rr, spo2, temp, sbp, hr, consciousness)

    if severity in ("Medium", "High", "Critical"):
        alert_doc = {
            "patient_id": patient_id,
            "vital_type": "EWS",
            "value": score,
            "severity_level": severity,
            "message": f"NEWS score = {score} ({severity}) – clinical review required",
            "status": "Active",
            "created_at": datetime.utcnow(),
        }
        insert_alert(alert_doc)

    return score, severity


def get_active_alerts(patient_id: str = None):
    """Return active (non-resolved) alerts, optionally filtered by patient."""
    query = {"status": {"$ne": "Resolved"}}
    if patient_id:
        query["patient_id"] = patient_id
    return get_alerts(query)
