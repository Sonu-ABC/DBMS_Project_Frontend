# backend/models.py – CRUD helpers for A6 collections
from datetime import datetime
from bson import ObjectId
from backend.db import get_db

# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------

def insert_patient(data: dict) -> str:
    """Insert a patient document. Returns inserted ID as string."""
    data.setdefault("created_at", datetime.utcnow())
    result = get_db().patients.insert_one(data)
    return str(result.inserted_id)


def get_patients(query: dict = None):
    """Return list of patient dicts."""
    return list(get_db().patients.find(query or {}))


def get_patient_by_id(patient_id: str):
    return get_db().patients.find_one({"_id": ObjectId(patient_id)})


def update_patient(patient_id: str, update_data: dict):
    get_db().patients.update_one(
        {"_id": ObjectId(patient_id)},
        {"$set": update_data}
    )


def delete_patient(patient_id: str):
    get_db().patients.delete_one({"_id": ObjectId(patient_id)})


# ---------------------------------------------------------------------------
# Vital Signs
# ---------------------------------------------------------------------------

def insert_vital_sign(data: dict) -> str:
    data.setdefault("recorded_time", datetime.utcnow())
    result = get_db().vital_signs.insert_one(data)
    return str(result.inserted_id)


def get_vitals_for_patient(patient_id: str, limit: int = 100):
    return list(
        get_db().vital_signs
        .find({"patient_id": patient_id})
        .sort("recorded_time", -1)
        .limit(limit)
    )


def get_latest_vitals(patient_id: str):
    """Return the most recent vital-sign document for a patient."""
    return get_db().vital_signs.find_one(
        {"patient_id": patient_id},
        sort=[("recorded_time", -1)]
    )


def get_all_recent_vitals(limit: int = 50):
    return list(
        get_db().vital_signs
        .find()
        .sort("recorded_time", -1)
        .limit(limit)
    )


# ---------------------------------------------------------------------------
# Alert Rules
# ---------------------------------------------------------------------------

def insert_alert_rule(data: dict) -> str:
    result = get_db().alert_rules.insert_one(data)
    return str(result.inserted_id)


def get_alert_rules(query: dict = None):
    return list(get_db().alert_rules.find(query or {}))


def update_alert_rule(rule_id: str, update_data: dict):
    get_db().alert_rules.update_one(
        {"_id": ObjectId(rule_id)},
        {"$set": update_data}
    )


def delete_alert_rule(rule_id: str):
    get_db().alert_rules.delete_one({"_id": ObjectId(rule_id)})


# ---------------------------------------------------------------------------
# Escalation Pathways
# ---------------------------------------------------------------------------

def insert_escalation_pathway(data: dict) -> str:
    result = get_db().escalation_pathways.insert_one(data)
    return str(result.inserted_id)


def get_escalation_pathways(query: dict = None):
    return list(get_db().escalation_pathways.find(query or {}))


def update_escalation_pathway(pathway_id: str, update_data: dict):
    get_db().escalation_pathways.update_one(
        {"_id": ObjectId(pathway_id)},
        {"$set": update_data}
    )


def delete_escalation_pathway(pathway_id: str):
    get_db().escalation_pathways.delete_one({"_id": ObjectId(pathway_id)})


# ---------------------------------------------------------------------------
# Monitoring Devices
# ---------------------------------------------------------------------------

def insert_device(data: dict) -> str:
    data.setdefault("status", "Active")
    result = get_db().monitoring_devices.insert_one(data)
    return str(result.inserted_id)


def get_devices(query: dict = None):
    return list(get_db().monitoring_devices.find(query or {}))


def update_device(device_id: str, update_data: dict):
    get_db().monitoring_devices.update_one(
        {"_id": ObjectId(device_id)},
        {"$set": update_data}
    )


def delete_device(device_id: str):
    get_db().monitoring_devices.delete_one({"_id": ObjectId(device_id)})


def assign_device_to_patient(device_id: str, patient_id: str):
    """Assign a monitoring device to a specific patient."""
    get_db().monitoring_devices.update_one(
        {"_id": ObjectId(device_id)},
        {"$set": {"assigned_patient_id": patient_id}}
    )


def unassign_device(device_id: str):
    """Remove patient assignment from a device."""
    get_db().monitoring_devices.update_one(
        {"_id": ObjectId(device_id)},
        {"$unset": {"assigned_patient_id": ""}}
    )


# ---------------------------------------------------------------------------
# Alerts (generated)
# ---------------------------------------------------------------------------

def insert_alert(data: dict) -> str:
    data.setdefault("created_at", datetime.utcnow())
    data.setdefault("status", "Active")
    result = get_db().alerts.insert_one(data)
    return str(result.inserted_id)


def get_alerts(query: dict = None, limit: int = 100):
    return list(
        get_db().alerts
        .find(query or {})
        .sort("created_at", -1)
        .limit(limit)
    )

def get_resolved_alerts(patient_id: str = None, limit: int = 50):
    """Fetch the audit trail of resolved alerts."""
    query = {"status": "Resolved"}
    if patient_id:
        query["patient_id"] = patient_id
        
    return list(
        get_db().alerts
        .find(query)
        .sort("resolved_at", -1)
        .limit(limit)
    )

def acknowledge_alert(alert_id: str):
    get_db().alerts.update_one(
        {"_id": ObjectId(alert_id)},
        {"$set": {"status": "Acknowledged", "acknowledged_at": datetime.utcnow()}}
    )

def resolve_alert(alert_id: str, action_notes: str = None):
    """Mark an alert as resolved and optionally log the clinical steps taken."""
    update_fields = {
        "status": "Resolved",
        "resolved_at": datetime.utcnow()
    }
    if action_notes:
        update_fields["action_notes"] = action_notes # Synced with the UI variable

    get_db().alerts.update_one(
        {"_id": ObjectId(alert_id)},
        {"$set": update_fields}
    )
    