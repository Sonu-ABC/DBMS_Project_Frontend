# backend/trend_analysis.py – Moving averages & deterioration detection
from backend.models import get_vitals_for_patient

VITAL_FIELDS = [
    "heart_rate", "temperature", "systolic_bp", "diastolic_bp",
    "respiratory_rate", "spo2", "pain_score",
]


def get_moving_average(patient_id: str, vital_field: str, window: int = 5):
    """
    Return a list of (recorded_time, moving_avg) tuples for the given vital.
    Uses a simple rolling window over the last *window* readings.
    """
    vitals = get_vitals_for_patient(patient_id, limit=200)
    vitals.reverse()  # oldest first

    values = []
    result = []
    for v in vitals:
        val = v.get(vital_field)
        if val is None:
            continue
        values.append(val)
        if len(values) >= window:
            avg = sum(values[-window:]) / window
            result.append((v.get("recorded_time"), round(avg, 2)))

    return result


def detect_deterioration(patient_id: str, window: int = 5):
    """
    Check whether the patient's vitals show a sustained worsening trend
    across multiple parameters.

    Returns a dict: {vital_field: 'improving' | 'stable' | 'deteriorating'}
    A field is 'deteriorating' if the last *window* readings show a monotone
    worsening direction.
    """
    vitals = get_vitals_for_patient(patient_id, limit=window + 1)
    vitals.reverse()

    # define which direction is "bad"
    bad_direction = {
        "heart_rate": "rising",
        "temperature": "rising",
        "systolic_bp": "falling",
        "diastolic_bp": "falling",
        "respiratory_rate": "rising",
        "spo2": "falling",
        "pain_score": "rising",
    }

    status = {}
    for field in VITAL_FIELDS:
        vals = [v.get(field) for v in vitals if v.get(field) is not None]
        if len(vals) < 3:
            status[field] = "insufficient data"
            continue

        recent = vals[-window:] if len(vals) >= window else vals
        diffs = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]

        if all(d > 0 for d in diffs):
            trend = "rising"
        elif all(d < 0 for d in diffs):
            trend = "falling"
        elif all(d == 0 for d in diffs):
            trend = "flat"
        else:
            avg_diff = sum(diffs) / len(diffs)
            if abs(avg_diff) < 0.5:
                trend = "stable"
            elif avg_diff > 0:
                trend = "rising"
            else:
                trend = "falling"

        bad = bad_direction.get(field, "rising")
        if trend == bad:
            status[field] = "deteriorating"
        elif trend == "flat" or trend == "stable":
            status[field] = "stable"
        else:
            status[field] = "improving"

    return status


def get_vital_time_series(patient_id: str, vital_field: str, limit: int = 50):
    """
    Return a list of dicts with recorded_time and value for charting.
    """
    vitals = get_vitals_for_patient(patient_id, limit=limit)
    vitals.reverse()
    return [
        {"time": v.get("recorded_time"), "value": v.get(vital_field)}
        for v in vitals
        if v.get(vital_field) is not None
    ]
