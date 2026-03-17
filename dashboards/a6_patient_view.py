# dashboards/a6_patient_view.py – Patient-facing A6: Clinical Alert System
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from backend.models import (
    get_patients, get_patient_by_id,
    get_vitals_for_patient, get_latest_vitals,
)
from backend.ews import calculate_mews, calculate_news, calculate_pews
from backend.alert_engine import get_active_alerts
from backend.trend_analysis import get_moving_average, detect_deterioration, get_vital_time_series


# ═══════════════════════════════════════════════════════════════════════════
# HELPER – resolve the logged-in patient
# ═══════════════════════════════════════════════════════════════════════════

def _get_current_patient():
    """Return (patient_dict, patient_id_str) for the logged-in patient.
    Falls back to the first patient in the database (no real auth yet)."""
    patients = get_patients()
    if not patients:
        return None, None
    p = patients[0]
    return p, str(p["_id"])


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY
# ═══════════════════════════════════════════════════════════════════════════

def a6_patient_view_page():
    st.markdown("# ⚠️ A6 – Clinical Alert System")
    st.caption("Your personal health monitoring dashboard · Vital signs · Alerts · Trends")

    patient, pid = _get_current_patient()
    if not patient:
        st.warning("⚠️ No patient record found. Please contact your healthcare provider.")
        _back_button()
        return

    patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}"
    st.markdown(f"👤 **Patient:** {patient_name}")

    tab_names = [
        "📊 My Health Overview",
        "💓 My Vitals",
        "🔔 My Alerts",
        "📈 Health Trends",
        "📋 Health Report",
    ]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        _tab_health_overview(pid, patient_name)
    with tabs[1]:
        _tab_my_vitals(pid)
    with tabs[2]:
        _tab_my_alerts(pid)
    with tabs[3]:
        _tab_health_trends(pid)
    with tabs[4]:
        _tab_health_report(pid)

    _back_button()


def _back_button():
    st.divider()
    if st.button("⬅ Back to Modules"):
        st.session_state.view = "category"
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: MY HEALTH OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════

def _tab_health_overview(pid, patient_name):
    st.subheader("📊 My Health Overview")

    latest = get_latest_vitals(pid)

    if not latest:
        st.info("No vital signs recorded yet. Your vitals will appear here once your care team records them.")
        return

    # ── Latest Vitals as metric cards ─────────────────────────────────────
    st.markdown("### Latest Vital Signs")
    c1, c2, c3 = st.columns(3)
    c1.metric("❤️ Heart Rate", f"{latest.get('heart_rate', '—')} bpm")
    c2.metric("🌡️ Temperature", f"{latest.get('temperature', '—')} °C")
    c3.metric("🩸 Blood Pressure", f"{latest.get('systolic_bp', '—')}/{latest.get('diastolic_bp', '—')} mmHg")

    c4, c5, c6 = st.columns(3)
    c4.metric("🫁 Respiratory Rate", f"{latest.get('respiratory_rate', '—')} /min")
    c5.metric("💨 SpO₂", f"{latest.get('spo2', '—')} %")
    c6.metric("😣 Pain Score", f"{latest.get('pain_score', '—')} / 10")

    st.divider()

    # ── EWS Score Badge ───────────────────────────────────────────────────
    st.markdown("### 🏥 Early Warning Score (NEWS)")
    score, severity = calculate_news(
        latest.get("respiratory_rate", 16),
        latest.get("spo2", 98),
        latest.get("temperature", 37.0),
        latest.get("systolic_bp", 120),
        latest.get("heart_rate", 80),
        latest.get("consciousness", "Alert"),
    )

    severity_color = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}.get(severity, "⚪")
    severity_msg = {
        "Low": "Your vitals are within normal ranges. Keep up the good health!",
        "Medium": "Some vitals need monitoring. Your care team has been notified.",
        "High": "Important: Some vitals are outside normal ranges. Medical review in progress.",
        "Critical": "Urgent: Your care team is being alerted for immediate review.",
    }.get(severity, "")

    col_score, col_msg = st.columns([1, 3])
    with col_score:
        st.metric("NEWS Score", score)
        st.markdown(f"### {severity_color} {severity}")
    with col_msg:
        if severity == "Low":
            st.success(severity_msg)
        elif severity == "Medium":
            st.warning(severity_msg)
        else:
            st.error(severity_msg)

    st.divider()

    # ── Active Alerts Summary ─────────────────────────────────────────────
    st.markdown("### 🔔 Alert Summary")
    
    # Fetch all ongoing alerts but filter them by status
    all_ongoing = get_active_alerts(pid)
    true_active = [a for a in all_ongoing if a.get("status") == "Active"]
    in_progress = [a for a in all_ongoing if a.get("status") == "Acknowledged"]

    if true_active:
        critical = sum(1 for a in true_active if a.get("severity_level") == "Critical")
        high = sum(1 for a in true_active if a.get("severity_level") == "High")
        medium = sum(1 for a in true_active if a.get("severity_level") == "Medium")
        low = sum(1 for a in true_active if a.get("severity_level") == "Low")

        ac1, ac2, ac3, ac4 = st.columns(4)
        ac1.metric("⛔ Critical", critical)
        ac2.metric("🔴 High", high)
        ac3.metric("🟠 Medium", medium)
        ac4.metric("🟡 Low", low)

        st.warning(f"💡 You have **{len(true_active)}** new alert(s) needing attention.")
    elif in_progress:
        # Reassure the patient if all alerts are already being handled
        st.info(f"👨‍⚕️ You have **{len(in_progress)}** alert(s) currently being reviewed by your doctor.")
    else:
        st.success("✅ No active alerts. All your vitals are within normal ranges!")

# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: MY VITALS
# ═══════════════════════════════════════════════════════════════════════════

def _tab_my_vitals(pid):
    st.subheader("💓 My Vital Signs")

    latest = get_latest_vitals(pid)

    # ── Latest Reading ────────────────────────────────────────────────────
    if latest:
        st.markdown("### 📌 Most Recent Reading")
        rec_time = latest.get("recorded_time", "N/A")
        st.caption(f"Recorded at: {rec_time}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("❤️ Heart Rate", f"{latest.get('heart_rate', '—')} bpm")
        c2.metric("🌡️ Temp", f"{latest.get('temperature', '—')} °C")
        c3.metric("🩸 BP", f"{latest.get('systolic_bp', '—')}/{latest.get('diastolic_bp', '—')}")
        c4.metric("💨 SpO₂", f"{latest.get('spo2', '—')}%")

        c5, c6, c7 = st.columns(3)
        c5.metric("🫁 Resp Rate", f"{latest.get('respiratory_rate', '—')} /min")
        c6.metric("😣 Pain", f"{latest.get('pain_score', '—')}/10")
        c7.metric("🧠 Consciousness", latest.get("consciousness", "—"))

        st.divider()

    # ── History Table ─────────────────────────────────────────────────────
    st.markdown("### 📜 Vital Sign History")
    vitals = get_vitals_for_patient(pid, limit=20)
    if vitals:
        rows = []
        for v in vitals:
            rows.append({
                "Time": str(v.get("recorded_time", ""))[:19],
                "HR (bpm)": v.get("heart_rate", ""),
                "Temp (°C)": v.get("temperature", ""),
                "RR": v.get("respiratory_rate", ""),
                "BP": f"{v.get('systolic_bp', '')}/{v.get('diastolic_bp', '')}",
                "SpO₂ (%)": v.get("spo2", ""),
                "Pain": v.get("pain_score", ""),
                "AVPU": v.get("consciousness", ""),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No vital sign history available yet.")
        return

    st.divider()

    # ── Trend Chart ───────────────────────────────────────────────────────
    st.markdown("### 📉 Vital Trend Chart")
    chart_vital = st.selectbox(
        "Select a vital to chart",
        ["heart_rate", "temperature", "systolic_bp", "respiratory_rate", "spo2", "pain_score"],
        format_func=lambda x: x.replace("_", " ").title(),
        key="patient_vital_chart",
    )
    ts_data = get_vital_time_series(pid, chart_vital, limit=50)
    if ts_data:
        times = [d["time"] for d in ts_data]
        vals = [d["value"] for d in ts_data]
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(times, vals, marker="o", linewidth=2, markersize=5, color="#5B47D8")
        ax.fill_between(times, vals, alpha=0.1, color="#5B47D8")
        ax.set_ylabel(chart_vital.replace("_", " ").title())
        ax.set_xlabel("Time")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        fig.autofmt_xdate()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
    else:
        st.info("Not enough data to display a trend chart.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3: MY ALERTS
# ═══════════════════════════════════════════════════════════════════════════

def _tab_my_alerts(pid):
    st.subheader("🔔 My Alerts")

    all_ongoing = get_active_alerts(pid)
    true_active = [a for a in all_ongoing if a.get("status") == "Active"]
    acknowledged = [a for a in all_ongoing if a.get("status") == "Acknowledged"]

    if not all_ongoing:
        st.success("✅ You have no active alerts. All your vitals are within normal ranges!")
        return

    # Internal helper to keep the rendering clean
    def render_alert_row(alert):
        sev = alert.get("severity_level", "Medium")
        icon = {"Low": "🟡", "Medium": "🟠", "High": "🔴", "Critical": "⛔"}.get(sev, "🟠")
        status = alert.get("status", "Active")
        status_icon = {"Active": "🔴", "Acknowledged": "🟡", "Resolved": "🟢"}.get(status, "⚪")

        col_icon, col_detail, col_status = st.columns([1, 5, 2])

        with col_icon:
            st.markdown(f"## {icon}")

        with col_detail:
            st.markdown(f"**{alert.get('message', 'Alert')}**")
            vtype = alert.get("vital_type", "")
            value = alert.get("value", "")
            if vtype and value:
                st.caption(f"Parameter: {vtype} · Value: {value}")
            created = alert.get("created_at", "")
            st.caption(f"🕐 {created}")

        with col_status:
            st.markdown(f"{status_icon} **{status}**")
            st.markdown(f"Severity: **{sev}**")

        st.markdown("---")

    # Render true active alerts first
    if true_active:
        st.markdown(f"#### 🔴 Action Required ({len(true_active)})")
        for alert in true_active:
            render_alert_row(alert)

    # Render acknowledged alerts in a reassuring section
    if acknowledged:
        st.markdown(f"#### 👨‍⚕️ Under Doctor Review ({len(acknowledged)})")
        st.info("Your care team has seen these alerts and is actively working on them.")
        for alert in acknowledged:
            render_alert_row(alert)

    # Legend
    st.markdown("#### 📖 Understanding Alert Levels")
    lc1, lc2, lc3, lc4 = st.columns(4)
    lc1.markdown("🟡 **Low**\nMinor deviation")
    lc2.markdown("🟠 **Medium**\nNeeds monitoring")
    lc3.markdown("🔴 **High**\nMedical review needed")
    lc4.markdown("⛔ **Critical**\nImmediate attention")

# ═══════════════════════════════════════════════════════════════════════════
# TAB 4: HEALTH TRENDS
# ═══════════════════════════════════════════════════════════════════════════

def _tab_health_trends(pid):
    st.subheader("📈 Health Trends & Analysis")

    # ── Moving Averages ───────────────────────────────────────────────────
    st.markdown("### 📊 Smoothed Vital Trends")
    st.caption("Moving average smooths out short-term fluctuations to show the overall direction of your vitals.")

    vital_choice = st.selectbox(
        "Select vital parameter",
        ["heart_rate", "temperature", "systolic_bp", "respiratory_rate", "spo2"],
        format_func=lambda x: x.replace("_", " ").title(),
        key="patient_ma_vital",
    )
    window = st.slider("Smoothing window", 3, 10, 5, key="patient_ma_window")

    ma_data = get_moving_average(pid, vital_choice, window)
    if ma_data:
        times = [d[0] for d in ma_data]
        avgs = [d[1] for d in ma_data]

        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.plot(times, avgs, marker="s", linewidth=2.5, markersize=4, color="#E74C3C", label="Trend (Moving Avg)")

        # overlay raw data
        raw = get_vital_time_series(pid, vital_choice, 50)
        if raw:
            ax.plot(
                [r["time"] for r in raw], [r["value"] for r in raw],
                alpha=0.35, linewidth=1, color="#95A5A6", label="Raw Readings",
            )

        ax.set_ylabel(vital_choice.replace("_", " ").title())
        ax.set_xlabel("Time")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        fig.autofmt_xdate()
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
    else:
        st.info("Not enough data for trend analysis. More readings are needed.")

    st.divider()

    # ── Deterioration Detection ───────────────────────────────────────────
    st.markdown("### 🩺 Overall Health Direction")
    st.caption("Shows whether each vital parameter is improving, stable, or deteriorating based on recent readings.")

    det = detect_deterioration(pid, window=5)
    if det:
        det_cols = st.columns(3)
        for idx, (field, status) in enumerate(det.items()):
            icon = {
                "deteriorating": "🔴",
                "stable": "🟢",
                "improving": "🟢",
                "insufficient data": "⚪",
            }.get(status, "⚪")
            label = field.replace("_", " ").title()
            with det_cols[idx % 3]:
                st.markdown(f"{icon} **{label}**")
                st.caption(status.capitalize())
    else:
        st.info("Not enough data for health direction analysis.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 5: HEALTH REPORT
# ═══════════════════════════════════════════════════════════════════════════

def _tab_health_report(pid):
    st.subheader("📋 Health Report")

    latest = get_latest_vitals(pid)
    if not latest:
        st.info("No vitals recorded yet. Your health report will be generated once your care team records your vitals.")
        return

    hr = latest.get("heart_rate", 80)
    rr = latest.get("respiratory_rate", 16)
    temp = latest.get("temperature", 37.0)
    sbp = latest.get("systolic_bp", 120)
    spo2_val = latest.get("spo2", 98)
    avpu = latest.get("consciousness", "Alert")

    # ── EWS Comparison ────────────────────────────────────────────────────
    st.markdown("### 📊 Early Warning Score Comparison")
    st.caption("Three different clinical scoring systems evaluate your vitals. Lower scores are better.")

    mews_s, mews_sev = calculate_mews(hr, sbp, rr, temp, avpu)
    news_s, news_sev = calculate_news(rr, spo2_val, temp, sbp, hr, avpu)
    pews_s, pews_sev = calculate_pews(hr, rr, spo2_val, temp, avpu)

    def _sev_color(sev):
        return {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}.get(sev, "⚪")

    ec1, ec2, ec3 = st.columns(3)

    with ec1:
        st.metric("MEWS Score", mews_s)
        st.markdown(f"{_sev_color(mews_sev)} **{mews_sev}**")
        st.caption("Modified Early Warning Score · General Ward")

    with ec2:
        st.metric("NEWS Score", news_s)
        st.markdown(f"{_sev_color(news_sev)} **{news_sev}**")
        st.caption("National Early Warning Score · NHS Recommended")

    with ec3:
        st.metric("PEWS Score", pews_s)
        st.markdown(f"{_sev_color(pews_sev)} **{pews_sev}**")
        st.caption("Pediatric Early Warning Score · Children")

    st.divider()

    # ── Vitals Summary Used ───────────────────────────────────────────────
    st.markdown("### 📝 Vitals Used for Scoring")
    st.caption("These are the latest readings used to calculate your scores above.")

    vc1, vc2, vc3 = st.columns(3)
    vc1.markdown(f"**Heart Rate:** {hr} bpm")
    vc2.markdown(f"**Respiratory Rate:** {rr} /min")
    vc3.markdown(f"**Temperature:** {temp} °C")

    vc4, vc5, vc6 = st.columns(3)
    vc4.markdown(f"**Systolic BP:** {sbp} mmHg")
    vc5.markdown(f"**SpO₂:** {spo2_val}%")
    vc6.markdown(f"**Consciousness:** {avpu}")

    st.divider()

    # ── What Do These Scores Mean? ────────────────────────────────────────
    st.markdown("### ❓ What Do These Scores Mean?")

    with st.expander("🟢 Low (Score 0–3)", expanded=False):
        st.markdown(
            "Your vitals are within normal ranges. Continue with routine monitoring. "
            "No immediate clinical action is needed."
        )

    with st.expander("🟡 Medium (Score 4–5)", expanded=False):
        st.markdown(
            "Some vitals are slightly outside normal ranges. Your care team will increase "
            "monitoring frequency. This is a precautionary measure."
        )

    with st.expander("🟠 High (Score 6–7)", expanded=False):
        st.markdown(
            "Several vitals need attention. A doctor or senior clinician will review your "
            "condition urgently. You may notice increased monitoring."
        )

    with st.expander("🔴 Critical (Score 8+)", expanded=False):
        st.markdown(
            "Your vitals indicate a serious concern. The rapid response team is being notified. "
            "Immediate clinical review and intervention may be required."
        )
