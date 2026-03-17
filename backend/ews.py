# backend/ews.py – Early Warning Score calculators
"""
Scoring systems:
  MEWS  – Modified Early Warning Score  (adults, general ward)
  NEWS  – National Early Warning Score  (adults, recommended by NHS)
  PEWS  – Pediatric Early Warning Score (children)

Each function returns (score: int, severity: str).
Severity levels: Low, Medium, High, Critical
"""


def _severity(score, thresholds=(3, 5, 7)):
    """Map a numeric score to a severity label."""
    low, med, high = thresholds
    if score <= low:
        return "Low"
    elif score <= med:
        return "Medium"
    elif score <= high:
        return "High"
    return "Critical"


# ── MEWS ──────────────────────────────────────────────────────────────────

def _mews_hr(hr):
    if hr < 40:
        return 2
    if hr <= 50:
        return 1
    if hr <= 100:
        return 0
    if hr <= 110:
        return 1
    if hr <= 130:
        return 2
    return 3


def _mews_sbp(sbp):
    if sbp < 70:
        return 3
    if sbp <= 80:
        return 2
    if sbp <= 100:
        return 1
    if sbp <= 199:
        return 0
    return 2


def _mews_rr(rr):
    if rr < 9:
        return 2
    if rr <= 14:
        return 0
    if rr <= 20:
        return 1
    if rr <= 29:
        return 2
    return 3


def _mews_temp(temp):
    if temp < 35.0:
        return 2
    if temp <= 38.4:
        return 0
    return 2


def _mews_avpu(avpu: str):
    """avpu: 'Alert', 'Voice', 'Pain', 'Unresponsive'"""
    mapping = {"Alert": 0, "Voice": 1, "Pain": 2, "Unresponsive": 3}
    return mapping.get(avpu, 0)


def calculate_mews(hr, sbp, rr, temp, avpu="Alert"):
    """Return (score, severity) for Modified Early Warning Score."""
    score = (
        _mews_hr(hr)
        + _mews_sbp(sbp)
        + _mews_rr(rr)
        + _mews_temp(temp)
        + _mews_avpu(avpu)
    )
    return score, _severity(score)


# ── NEWS ──────────────────────────────────────────────────────────────────

def _news_rr(rr):
    if rr <= 8:
        return 3
    if rr <= 11:
        return 1
    if rr <= 20:
        return 0
    if rr <= 24:
        return 2
    return 3


def _news_spo2(spo2):
    if spo2 <= 91:
        return 3
    if spo2 <= 93:
        return 2
    if spo2 <= 95:
        return 1
    return 0


def _news_temp(temp):
    if temp <= 35.0:
        return 3
    if temp <= 36.0:
        return 1
    if temp <= 38.0:
        return 0
    if temp <= 39.0:
        return 1
    return 2


def _news_sbp(sbp):
    if sbp <= 90:
        return 3
    if sbp <= 100:
        return 2
    if sbp <= 110:
        return 1
    if sbp <= 219:
        return 0
    return 3


def _news_hr(hr):
    if hr <= 40:
        return 3
    if hr <= 50:
        return 1
    if hr <= 90:
        return 0
    if hr <= 110:
        return 1
    if hr <= 130:
        return 2
    return 3


def _news_consciousness(c: str):
    return 0 if c == "Alert" else 3


def calculate_news(rr, spo2, temp, sbp, hr, consciousness="Alert"):
    """Return (score, severity) for National Early Warning Score."""
    score = (
        _news_rr(rr)
        + _news_spo2(spo2)
        + _news_temp(temp)
        + _news_sbp(sbp)
        + _news_hr(hr)
        + _news_consciousness(consciousness)
    )
    return score, _severity(score)


# ── PEWS ──────────────────────────────────────────────────────────────────

def _pews_hr(hr):
    if hr < 60:
        return 3
    if hr <= 80:
        return 1
    if hr <= 130:
        return 0
    if hr <= 150:
        return 1
    return 3


def _pews_rr(rr):
    if rr < 10:
        return 3
    if rr <= 16:
        return 0
    if rr <= 24:
        return 1
    return 3


def _pews_spo2(spo2):
    if spo2 <= 91:
        return 3
    if spo2 <= 94:
        return 2
    if spo2 <= 96:
        return 1
    return 0


def _pews_temp(temp):
    if temp < 35.5:
        return 2
    if temp <= 37.5:
        return 0
    if temp <= 38.5:
        return 1
    return 2


def _pews_consciousness(c: str):
    return 0 if c == "Alert" else 3


def calculate_pews(hr, rr, spo2, temp, consciousness="Alert"):
    """Return (score, severity) for Pediatric Early Warning Score."""
    score = (
        _pews_hr(hr)
        + _pews_rr(rr)
        + _pews_spo2(spo2)
        + _pews_temp(temp)
        + _pews_consciousness(consciousness)
    )
    return score, _severity(score, thresholds=(2, 4, 6))
