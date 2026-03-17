# dashboards/a6_clinical_alerts.py – Module A6: Clinical Alert System
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from backend.models import (
    get_patients, insert_patient, get_patient_by_id, delete_patient,
    get_vitals_for_patient, insert_vital_sign, get_all_recent_vitals,
    get_alert_rules, insert_alert_rule, delete_alert_rule, update_alert_rule,
    get_devices, insert_device, delete_device, assign_device_to_patient, unassign_device,
    get_escalation_pathways, insert_escalation_pathway, delete_escalation_pathway,
    get_alerts, acknowledge_alert, resolve_alert, get_latest_vitals,
)
from backend.ews import calculate_mews, calculate_news, calculate_pews
from backend.alert_engine import evaluate_vitals, evaluate_ews_for_vitals, get_active_alerts
from backend.trend_analysis import get_moving_average, detect_deterioration, get_vital_time_series


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY
# ═══════════════════════════════════════════════════════════════════════════

def a6_clinical_alerts_page():
    st.markdown("# ⚠️ A6 – Clinical Alert System for Abnormal Vital Values")
    st.caption("Real-time vital sign monitoring · EWS calculation · Threshold-based alerting · Trend analysis")

    tab_names = [
        "📊 Dashboard",
        "👥 Patients",
        "💓 Vital Signs",
        "🔔 Alert Rules",
        "📟 Devices",
        "🚨 Escalation",
        "📈 Analytics",
    ]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        _tab_dashboard()
    with tabs[1]:
        _tab_patients()
    with tabs[2]:
        _tab_vital_signs()
    with tabs[3]:
        _tab_alert_rules()
    with tabs[4]:
        _tab_devices()
    with tabs[5]:
        _tab_escalation()
    with tabs[6]:
        _tab_analytics()

    st.divider()
    if st.button("⬅ Back to Modules"):
        st.session_state.view = "category"
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

def _tab_dashboard():
    st.subheader("📊 Live Dashboard")

    # ── Metrics row ───────────────────────────────────────────────────────
    patients = get_patients()
    active_alerts = get_active_alerts()
    devices = get_devices()
    rules = get_alert_rules()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Patients", len(patients))
    c2.metric("⚠️ Active Alerts", len(active_alerts))
    c3.metric("📟 Devices", len([d for d in devices if d.get("status") == "Active"]))
    c4.metric("📏 Alert Rules", len(rules))

    st.divider()

    # ── Active Alerts ─────────────────────────────────────────────────────
    st.markdown("### 🔴 Active Alerts")
    if active_alerts:
        for alert in active_alerts[:10]:
            sev = alert.get("severity_level", "Medium")
            icon = {"Low": "🟡", "Medium": "🟠", "High": "🔴", "Critical": "⛔"}.get(sev, "🟠")
            pid = alert.get("patient_id", "")
            pat = get_patient_by_id(pid) if pid else None
            pat_name = f"{pat['first_name']} {pat['last_name']}" if pat else pid

            col_a, col_b, col_c = st.columns([5, 2, 2])
            with col_a:
                st.markdown(f"{icon} **{alert.get('message', '')}**")
                st.caption(f"Patient: {pat_name} · {alert.get('created_at', '')}")
            with col_b:
                st.markdown(f"**{sev}**")
            with col_c:
                ack_key = f"ack_{alert['_id']}"
                if alert.get("status") == "Active":
                    if st.button("✔ Ack", key=ack_key):
                        acknowledge_alert(str(alert["_id"]))
                        st.rerun()
            st.markdown("---")
            if alert.get("status") != "Resolved":
                with st.expander("🩺 Resolve Alert & Log Actions"):
                    with st.form(f"resolve_form_{alert['_id']}"):
                        action_notes = st.text_area(
                            "Clinical Steps Taken",
                            placeholder="e.g., Administered O2 at 2L/min, notified Dr. Smith",
                        )
                        if st.form_submit_button("✅ Resolve Alert"):
                            if action_notes.strip():
                                resolve_alert(str(alert["_id"]), action_notes)
                                st.success("Alert resolved with action log.")
                                st.rerun()
                            else:
                                st.error("Please log the actions taken before resolving.")
    else:
        st.success("✅ No active alerts. All vitals are within normal ranges.")

    st.divider()

    # ── EWS Score Cards ───────────────────────────────────────────────────
    st.markdown("### 📋 Patient EWS Scores")
    if patients:
        cols = st.columns(min(len(patients), 3))
        for idx, p in enumerate(patients):
            pid = str(p["_id"])
            latest = get_latest_vitals(pid)
            with cols[idx % 3]:
                name = f"{p.get('first_name', '')} {p.get('last_name', '')}"
                st.markdown(f"**{name}**")
                if latest:
                    score, sev = calculate_news(
                        latest.get("respiratory_rate", 16),
                        latest.get("spo2", 98),
                        latest.get("temperature", 37.0),
                        latest.get("systolic_bp", 120),
                        latest.get("heart_rate", 80),
                        latest.get("consciousness", "Alert"),
                    )
                    color = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}.get(sev, "⚪")
                    st.markdown(f"NEWS Score: **{score}** {color} {sev}")
                    st.caption(
                        f"HR {latest.get('heart_rate')} · T {latest.get('temperature')}°C · "
                        f"BP {latest.get('systolic_bp')}/{latest.get('diastolic_bp')} · "
                        f"SpO₂ {latest.get('spo2')}%"
                    )
                else:
                    st.caption("No vital data recorded yet")
                st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: PATIENTS
# ═══════════════════════════════════════════════════════════════════════════

def _tab_patients():
    st.subheader("👥 Patient Management")

    # ── Add Patient Form ──────────────────────────────────────────────────
    with st.expander("➕ Register New Patient"):
        with st.form("add_patient_form"):
            fc1, fc2, fc3 = st.columns(3)
            first = fc1.text_input("First Name")
            middle = fc2.text_input("Middle Name")
            last = fc3.text_input("Last Name")

            fc4, fc5, fc6 = st.columns(3)
            dob = fc4.date_input("Date of Birth")
            age = fc5.number_input("Age", 0, 150, 30)
            gender = fc6.selectbox("Gender", ["Male", "Female", "Other"])

            phone = st.text_input("Phone Number")

            if st.form_submit_button("Register Patient"):
                if first and last:
                    insert_patient({
                        "first_name": first, "middle_name": middle, "last_name": last,
                        "dob": str(dob), "age": age, "gender": gender, "phone_no": phone,
                    })
                    st.success(f"✅ {first} {last} registered!")
                    st.rerun()
                else:
                    st.error("First and last name are required.")

    st.divider()

    # ── Patient List ──────────────────────────────────────────────────────
    patients = get_patients()
    if patients:
        rows = []
        for p in patients:
            rows.append({
                "ID": str(p["_id"]),
                "Name": f"{p.get('first_name', '')} {p.get('middle_name', '')} {p.get('last_name', '')}",
                "Age": p.get("age", ""),
                "Gender": p.get("gender", ""),
                "DOB": p.get("dob", ""),
                "Phone": p.get("phone_no", ""),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No patients registered yet. Use the form above to add one.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3: VITAL SIGNS
# ═══════════════════════════════════════════════════════════════════════════

def _tab_vital_signs():
    st.subheader("💓 Vital Signs")

    patients = get_patients()
    if not patients:
        st.info("No patients found. Register patients first.")
        return

    patient_map = {f"{p['first_name']} {p['last_name']}": str(p["_id"]) for p in patients}

    # ── Record New Vitals ─────────────────────────────────────────────────
    with st.expander("➕ Record New Vital Signs"):
        with st.form("add_vitals_form"):
            sel_patient = st.selectbox("Patient", list(patient_map.keys()))
            pid = patient_map[sel_patient]

            vc1, vc2, vc3 = st.columns(3)
            hr = vc1.number_input("Heart Rate (bpm)", 20, 250, 80)
            temp = vc2.number_input("Temperature (°C)", 30.0, 45.0, 37.0, step=0.1)
            rr = vc3.number_input("Respiratory Rate", 4, 60, 16)

            vc4, vc5, vc6 = st.columns(3)
            sbp = vc4.number_input("Systolic BP", 50, 300, 120)
            dbp = vc5.number_input("Diastolic BP", 20, 200, 80)
            spo2 = vc6.number_input("SpO₂ (%)", 50.0, 100.0, 98.0, step=0.1)

            vc7, vc8 = st.columns(2)
            pain = vc7.slider("Pain Score (0-10)", 0, 10, 0)
            consciousness = vc8.selectbox("Consciousness", ["Alert", "Voice", "Pain", "Unresponsive"])

            # select device
            devices = get_devices({"status": "Active"})
            device_names = {d["device_name"]: str(d["_id"]) for d in devices}
            selected_device = st.selectbox("Monitoring Device", ["None"] + list(device_names.keys()))

            if st.form_submit_button("💾 Save Vital Signs"):
                vitals_doc = {
                    "patient_id": pid,
                    "heart_rate": hr, "temperature": temp,
                    "respiratory_rate": rr, "systolic_bp": sbp, "diastolic_bp": dbp,
                    "spo2": spo2, "pain_score": pain, "consciousness": consciousness,
                    "recorded_time": datetime.utcnow(),
                }
                if selected_device != "None":
                    vitals_doc["device_id"] = device_names[selected_device]

                insert_vital_sign(vitals_doc)
                st.success("✅ Vitals recorded!")

                # Evaluate against rules & EWS
                fired = evaluate_vitals(pid, vitals_doc)
                ews_score, ews_sev = evaluate_ews_for_vitals(pid, vitals_doc)

                if fired:
                    for a in fired:
                        st.warning(f"🔔 Alert: {a['message']} (Severity: {a['severity_level']})")
                st.info(f"📋 NEWS Score: **{ews_score}** — {ews_sev}")
                st.rerun()

    st.divider()

    # ── View Patient History ──────────────────────────────────────────────
    st.markdown("### 📜 Vital Sign History")
    view_patient = st.selectbox("Select Patient", list(patient_map.keys()), key="vs_hist_pat")
    vpid = patient_map[view_patient]

    vitals = get_vitals_for_patient(vpid, limit=50)
    if vitals:
        rows = []
        for v in vitals:
            rows.append({
                "Time": v.get("recorded_time", ""),
                "HR": v.get("heart_rate", ""),
                "Temp (°C)": v.get("temperature", ""),
                "RR": v.get("respiratory_rate", ""),
                "SBP": v.get("systolic_bp", ""),
                "DBP": v.get("diastolic_bp", ""),
                "SpO₂": v.get("spo2", ""),
                "Pain": v.get("pain_score", ""),
                "AVPU": v.get("consciousness", ""),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ── Inline line chart ─────────────────────────────────────────────
        st.markdown("### 📉 Vital Trend Chart")
        chart_vital = st.selectbox(
            "Select vital to chart",
            ["heart_rate", "temperature", "systolic_bp", "respiratory_rate", "spo2", "pain_score"],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        ts_data = get_vital_time_series(vpid, chart_vital, limit=50)
        if ts_data:
            times = [d["time"] for d in ts_data]
            vals = [d["value"] for d in ts_data]
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.plot(times, vals, marker="o", linewidth=2, markersize=4, color="#5B47D8")
            ax.set_ylabel(chart_vital.replace("_", " ").title())
            ax.set_xlabel("Time")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
            fig.autofmt_xdate()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
    else:
        st.info("No vital signs recorded for this patient yet.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4: ALERT RULES
# ═══════════════════════════════════════════════════════════════════════════

def _tab_alert_rules():
    st.subheader("🔔 Alert Rules")

    # ── Add Rule ──────────────────────────────────────────────────────────
    with st.expander("➕ Add New Alert Rule"):
        with st.form("add_rule_form"):
            rc1, rc2 = st.columns(2)
            vtype = rc1.selectbox("Vital Type",
                                  ["Heart Rate", "Temperature", "Systolic BP",
                                   "Diastolic BP", "Respiratory Rate", "SpO2", "Pain Score"])
            scoring = rc2.selectbox("Scoring System", ["NEWS", "MEWS", "PEWS"])

            rc3, rc4, rc5 = st.columns(3)
            min_val = rc3.number_input("Min Value", value=0.0, step=0.1)
            max_val = rc4.number_input("Max Value", value=100.0, step=0.1)
            severity = rc5.selectbox("Severity", ["Low", "Medium", "High", "Critical"])

            if st.form_submit_button("Save Rule"):
                insert_alert_rule({
                    "vital_type": vtype, "min_value": min_val, "max_value": max_val,
                    "severity_level": severity, "scoring_system": scoring,
                })
                st.success("✅ Alert rule created!")
                st.rerun()

    st.divider()

    # ── List Rules ────────────────────────────────────────────────────────
    rules = get_alert_rules()
    if rules:
        rows = []
        for r in rules:
            rows.append({
                "ID": str(r["_id"]),
                "Vital Type": r.get("vital_type", ""),
                "Min": r.get("min_value", ""),
                "Max": r.get("max_value", ""),
                "Severity": r.get("severity_level", ""),
                "Scoring": r.get("scoring_system", ""),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Delete / Edit Section
        st.divider()
        st.markdown("### Update or Delete Rule")
        
        rule_opts = {f"{r.get('vital_type')} ({r.get('severity_level')})": str(r["_id"]) for r in rules}
        sel_rule_key = st.selectbox("Select Rule to Modify", ["None"] + list(rule_opts.keys()))
        
        if sel_rule_key != "None":
            rule_id_str = rule_opts[sel_rule_key]
            # find original rule data
            r_data = next((x for x in rules if str(x["_id"]) == rule_id_str), None)
            
            with st.expander("✏️ Edit Selected Rule"):
                with st.form(f"edit_rule_{rule_id_str}"):
                    er3, er4 = st.columns(2)
                    new_min = er3.number_input("Min Value", value=float(r_data.get("min_value", 0.0)), step=0.1)
                    new_max = er4.number_input("Max Value", value=float(r_data.get("max_value", 100.0)), step=0.1)
                    
                    if st.form_submit_button("Update Rule Limits"):
                        update_alert_rule(rule_id_str, {"min_value": new_min, "max_value": new_max})
                        st.success("Rule updated successfully.")
                        st.rerun()

            with st.expander("🗑️ Delete Selected Rule"):
                st.warning("Are you sure you want to delete this rule?")
                if st.button("Confirm Delete"):
                    delete_alert_rule(rule_id_str)
                    st.success("Rule deleted.")
                    st.rerun()
    else:
        st.info("No alert rules configured. Add rules above.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 5: MONITORING DEVICES
# ═══════════════════════════════════════════════════════════════════════════

def _tab_devices():
    st.subheader("📟 Monitoring Devices")

    with st.expander("➕ Register New Device"):
        with st.form("add_device_form"):
            dc1, dc2 = st.columns(2)
            dname = dc1.text_input("Device Name")
            dtype = dc2.text_input("Device Type")

            dc3, dc4 = st.columns(2)
            location = dc3.text_input("Location")
            status = dc4.selectbox("Status", ["Active", "Maintenance", "Inactive"])

            if st.form_submit_button("Register Device"):
                if dname:
                    insert_device({
                        "device_name": dname, "device_type": dtype,
                        "location": location, "status": status,
                    })
                    st.success(f"✅ Device '{dname}' registered!")
                    st.rerun()
                else:
                    st.error("Device name is required.")

    st.divider()

    # ── Assign Device to Patient ──────────────────────────────────────────
    with st.expander("🔗 Assign Device to Patient"):
        devices = get_devices()
        patients = get_patients()
        
        if not devices or not patients:
            st.info("Ensure both Devices and Patients are registered to make assignments.")
        else:
            with st.form("assign_device_form"):
                d_c1, d_c2 = st.columns(2)
                
                device_opts = {f"{d['device_name']} ({d['location']})": str(d["_id"]) for d in devices if d.get("status") == "Active"}
                patient_opts = {f"{p['first_name']} {p['last_name']}": str(p["_id"]) for p in patients}
                
                sel_device = d_c1.selectbox("Select Device", ["None"] + list(device_opts.keys()))
                sel_patient = d_c2.selectbox("Select Patient", ["None"] + list(patient_opts.keys()))
                
                submit_assign = st.form_submit_button("Assign")
                
                if submit_assign:
                    if sel_device != "None" and sel_patient != "None":
                        assign_device_to_patient(device_opts[sel_device], patient_opts[sel_patient])
                        st.success("✅ Device successfully assigned!")
                        st.rerun()
                    else:
                        st.error("Please select both a valid Device and Patient.")

    st.divider()

    devices = get_devices()
    if devices:
        rows = []
        for d in devices:
            assigned_id = d.get("assigned_patient_id")
            patient_name = "None"
            if assigned_id:
                pat = get_patient_by_id(assigned_id)
                if pat:
                    patient_name = f"{pat.get('first_name', '')} {pat.get('last_name', '')}"
            
            rows.append({
                "ID": str(d["_id"]),
                "Name": d.get("device_name", ""),
                "Type": d.get("device_type", ""),
                "Location": d.get("location", ""),
                "Status": d.get("status", ""),
                "Assigned Patient": patient_name
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        d_col1, d_col2 = st.columns(2)
        with d_col1:
            unassign_id = st.text_input("Enter Device ID to unassign", key="unassign_device")
            if st.button("🔗 Unassign Device"):
                if unassign_id:
                    unassign_device(unassign_id)
                    st.success("Device unassigned.")
                    st.rerun()
        
        with d_col2:
            del_id = st.text_input("Enter Device ID to delete", key="del_device")
            if st.button("🗑️ Delete Device"):
                if del_id:
                    delete_device(del_id)
                    st.success("Device deleted.")
                    st.rerun()
    else:
        st.info("No devices registered yet.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 6: ESCALATION PATHWAYS
# ═══════════════════════════════════════════════════════════════════════════

def _tab_escalation():
    st.subheader("🚨 Escalation Pathways")

    with st.expander("➕ Add Escalation Pathway"):
        with st.form("add_esc_form"):
            ec1, ec2 = st.columns(2)
            sev = ec1.selectbox("Severity Level", ["Low", "Medium", "High", "Critical"])
            notify = ec2.text_input("Notify Role", placeholder="e.g. Nurse + Resident")

            ec3, ec4 = st.columns(2)
            resp_time = ec3.text_input("Response Time", placeholder="e.g. 15 min")
            method = ec4.selectbox("Notification Method",
                                   ["In-App", "In-App + SMS", "Phone Call + SMS",
                                    "Overhead Page + Phone + SMS"])

            if st.form_submit_button("Save Pathway"):
                insert_escalation_pathway({
                    "severity_level": sev, "notify_role": notify,
                    "response_time": resp_time, "notification_method": method,
                })
                st.success("✅ Escalation pathway created!")
                st.rerun()

    st.divider()

    pathways = get_escalation_pathways()
    if pathways:
        rows = []
        for pw in pathways:
            rows.append({
                "ID": str(pw["_id"]),
                "Severity": pw.get("severity_level", ""),
                "Notify Role": pw.get("notify_role", ""),
                "Response Time": pw.get("response_time", ""),
                "Method": pw.get("notification_method", ""),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        del_id = st.text_input("Enter Pathway ID to delete", key="del_esc")
        if st.button("🗑️ Delete Pathway"):
            if del_id:
                delete_escalation_pathway(del_id)
                st.success("Pathway deleted.")
                st.rerun()
    else:
        st.info("No escalation pathways configured.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 7: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════

def _tab_analytics():
    st.subheader("📈 Trend Analysis & Analytics")

    patients = get_patients()
    if not patients:
        st.info("No patients found.")
        return

    patient_map = {f"{p['first_name']} {p['last_name']}": str(p["_id"]) for p in patients}
    sel = st.selectbox("Select Patient", list(patient_map.keys()), key="analytics_pat")
    pid = patient_map[sel]

    st.divider()

    # ── Moving Averages ───────────────────────────────────────────────────
    st.markdown("### 📊 Moving Averages")
    vital_choice = st.selectbox(
        "Vital Parameter",
        ["heart_rate", "temperature", "systolic_bp", "respiratory_rate", "spo2"],
        format_func=lambda x: x.replace("_", " ").title(),
        key="ma_vital",
    )
    window = st.slider("Window size", 3, 10, 5)

    ma_data = get_moving_average(pid, vital_choice, window)
    if ma_data:
        times = [d[0] for d in ma_data]
        avgs = [d[1] for d in ma_data]

        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(times, avgs, marker="s", linewidth=2, markersize=4, color="#E74C3C", label="Moving Avg")

        # overlay raw
        raw = get_vital_time_series(pid, vital_choice, 50)
        if raw:
            ax.plot([r["time"] for r in raw], [r["value"] for r in raw],
                    alpha=0.4, linewidth=1, color="#95A5A6", label="Raw")

        ax.set_ylabel(vital_choice.replace("_", " ").title())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        fig.autofmt_xdate()
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
    else:
        st.info("Not enough data for moving average calculation.")

    st.divider()

    # ── Deterioration Detection ───────────────────────────────────────────
    st.markdown("### 🩺 Multi-Parameter Deterioration Detection")
    det = detect_deterioration(pid, window=5)
    if det:
        for field, status in det.items():
            icon = {"deteriorating": "🔴", "stable": "🟢", "improving": "🟢",
                    "insufficient data": "⚪"}.get(status, "⚪")
            label = field.replace("_", " ").title()
            st.markdown(f"{icon} **{label}**: {status.capitalize()}")
    else:
        st.info("Not enough data for deterioration analysis.")

    st.divider()

    # ── EWS Comparison ────────────────────────────────────────────────────
    st.markdown("### 📋 EWS Score Comparison (MEWS vs NEWS vs PEWS)")
    latest = get_latest_vitals(pid)
    if latest:
        hr = latest.get("heart_rate", 80)
        rr = latest.get("respiratory_rate", 16)
        temp = latest.get("temperature", 37.0)
        sbp = latest.get("systolic_bp", 120)
        spo2_val = latest.get("spo2", 98)
        avpu = latest.get("consciousness", "Alert")

        mews_s, mews_sev = calculate_mews(hr, sbp, rr, temp, avpu)
        news_s, news_sev = calculate_news(rr, spo2_val, temp, sbp, hr, avpu)
        pews_s, pews_sev = calculate_pews(hr, rr, spo2_val, temp, avpu)

        ec1, ec2, ec3 = st.columns(3)
        ec1.metric("MEWS", mews_s, mews_sev)
        ec2.metric("NEWS", news_s, news_sev)
        ec3.metric("PEWS", pews_s, pews_sev)

        st.caption(
            f"Based on latest vitals: HR={hr}, RR={rr}, Temp={temp}°C, "
            f"SBP={sbp}, SpO₂={spo2_val}%, AVPU={avpu}"
        )
    else:
        st.info("No vitals recorded for EWS calculation.")
