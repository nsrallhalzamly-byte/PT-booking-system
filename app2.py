import streamlit as st
import datetime
import pandas as pd
import os

st.set_page_config(page_title="PT Clinic & Modality Manager", layout="wide")

# --- DATA STORAGE SETUP ---
PLANS_FILE = "patient_plans.csv"
LOGS_FILE = "device_logs.csv"

def load_data():
    if os.path.exists(PLANS_FILE):
        plans = pd.read_csv(PLANS_FILE).to_dict("records")
    else:
        plans = []
        
    if os.path.exists(LOGS_FILE):
        logs = pd.read_csv(LOGS_FILE).to_dict("records")
    else:
        logs = []
    return plans, logs

def save_data(plans, logs):
    pd.DataFrame(plans).to_csv(PLANS_FILE, index=False)
    pd.DataFrame(logs).to_csv(LOGS_FILE, index=False)

if "care_plans" not in st.session_state:
    plans, logs = load_data()
    st.session_state.care_plans = plans
    st.session_state.usage_logs = logs

if "doctors" not in st.session_state:
    st.session_state.doctors = ["PT 1", "PT 2", "PT 3", "PT 4"]

if "devices" not in st.session_state:
    st.session_state.devices = [
        "TENS", "Faradic / IFT", "Hot Pack", "Cold Pack", 
        "Shockwave", "Ultrasound", "Laser", "Manual Therapy / Massage"
    ]

TIME_SLOTS = [
    "09:00 AM (50 mins)", "10:00 AM (50 mins)", "11:00 AM (50 mins)", 
    "12:00 PM (50 mins)", "01:00 PM (50 mins)", "02:00 PM (50 mins)"
]

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December"
]

st.title("Physical Therapy Practice & Device Manager")

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
menu = st.sidebar.radio("Select View:", [
    "Monthly Schedule & Bookings", 
    "Active Care Plans & Session Logging", 
    "New Patient Plan (Auto-Schedule)", 
    "Edit / Manage Patients",
    "Device Analytics", 
    "Settings"
])

# ---------------------------------------------------------
# 1. MONTHLY SCHEDULE & BOOKINGS
# ---------------------------------------------------------
if menu == "Monthly Schedule & Bookings":
    st.header("Daily Schedule & Booking Slots")
    
    selected_date = st.date_input("Select Date to View Schedule:", datetime.date.today())
    st.subheader(f"Schedule for {selected_date.strftime('%A, %B %d, %Y')}")
    
    active_plans = [p for p in st.session_state.care_plans if str(p.get("status")) == "Active"]
    
    for slot in TIME_SLOTS:
        st.markdown(f"### 🕒 {slot}")
        slot_bookings = [p for p in active_plans if p.get("time_slot") == slot and str(p.get("booking_date")) == str(selected_date)]
        
        if slot_bookings:
            cols = st.columns(len(slot_bookings))
            for idx, b in enumerate(slot_bookings):
                with cols[idx]:
                    st.info(
                        f"**Patient:** {b['patient']}\n\n"
                        f"**PT:** {b['doctor']}\n\n"
                        f"**Setting:** {b['type']}\n\n"
                        f"**Session:** {b['completed_sessions']}/{b['total_sessions']}"
                    )
        else:
            st.caption("No patients scheduled for this 50-min slot.")
        st.divider()

# ---------------------------------------------------------
# 2. ACTIVE CARE PLANS & SESSION LOGGING (GROUPED BY PATIENT)
# ---------------------------------------------------------
elif menu == "Active Care Plans & Session Logging":
    st.header("Active Care Plans")
    
    if not st.session_state.care_plans:
        st.info("No active patient plans found.")
    else:
        df_plans = pd.DataFrame(st.session_state.care_plans)
        active_df = df_plans[df_plans['status'] == 'Active']
        
        if active_df.empty:
            st.info("No active patient plans found.")
        else:
            unique_patients = active_df['patient'].unique()
            
            for patient_name in unique_patients:
                patient_entries = [p for p in st.session_state.care_plans if p['patient'] == patient_name]
                first_entry = patient_entries[0]
                
                completed = int(first_entry.get('completed_sessions', 0))
                total = int(first_entry.get('total_sessions', 12))
                doctor = first_entry.get('doctor', '')
                modalities = first_entry.get('selected_modalities', '')
                
                with st.expander(f"Patient: {patient_name} | PT: {doctor} ({completed}/{total} Completed)", expanded=True):
                    col1, col2, col3 = st.columns([2, 2, 2])
                    
                    rem = total - completed
                    col1.write(f"**Remaining:** {rem} / {total} sessions (50 mins each)")
                    col1.progress(min(completed / total, 1.0))
                    
                    col2.write("**Assigned Devices / Modalities:**")
                    col2.write(modalities)
                    
                    # Log Session
                    if col3.button("Log Session (+1)", key=f"log_{patient_name}"):
                        if completed < total:
                            new_completed = completed + 1
                            
                            for p in st.session_state.care_plans:
                                if p['patient'] == patient_name:
                                    p['completed_sessions'] = new_completed
                                    if new_completed >= total:
                                        p['status'] = "Completed"
                            
                            today_str = str(datetime.date.today())
                            mods = str(modalities).split(", ")
                            for m in mods:
                                st.session_state.usage_logs.append({
                                    "date": today_str,
                                    "device": m,
                                    "patient": patient_name
                                })
                            
                            save_data(st.session_state.care_plans, st.session_state.usage_logs)
                            st.success(f"Logged session for {patient_name} ({new_completed}/{total})!")
                            st.rerun()
                    
                    # Undo Button
                    if completed > 0:
                        if col3.button("↩️ Undo Last Session", key=f"undo_{patient_name}"):
                            new_completed = completed - 1
                            for p in st.session_state.care_plans:
                                if p['patient'] == patient_name:
                                    p['completed_sessions'] = new_completed
                                    p['status'] = "Active"
                            
                            # Remove the last logged device entry for this patient
                            st.session_state.usage_logs = [
                                log for log in st.session_state.usage_logs 
                                if not (log.get('patient') == patient_name and log.get('date') == str(datetime.date.today()))
                            ]
                            
                            save_data(st.session_state.care_plans, st.session_state.usage_logs)
                            st.warning(f"Undid last session for {patient_name}.")
                            st.rerun()

# ---------------------------------------------------------
# 3. NEW PATIENT PLAN (AUTO-RECURRING SCHEDULE)
# ---------------------------------------------------------
elif menu == "New Patient Plan (Auto-Schedule)":
    st.header("Register New Patient & Auto-Schedule Sessions")
    
    with st.form("new_plan_auto"):
        col1, col2 = st.columns(2)
        patient_name = col1.text_input("Patient Full Name")
        care_type = col1.selectbox("Bed / Setting", ["Bed 1", "Bed 2", "Bed 3", "Bed 4", "Bed 5", "Bed 6", "Inpatient Room Visit"])
        assigned_pt = col2.selectbox("Assigned Physiotherapist", st.session_state.doctors)
        total_sessions = col2.number_input("Total Prescribed Sessions", min_value=1, max_value=12, value=12)
        
        st.subheader("Recurring 3-Day/Week Schedule Setup")
        col3, col4, col5 = st.columns(3)
        start_date = col3.date_input("First Session Date", datetime.date.today())
        time_slot = col4.selectbox("Fixed 50-Min Slot", TIME_SLOTS)
        schedule_pattern = col5.selectbox("Weekly Pattern", ["Sat / Mon / Wed", "Sun / Tue / Thu"])
        
        selected_mods = st.multiselect("Select Modalities & Devices", st.session_state.devices)
        
        submitted = st.form_submit_button("Generate & Auto-Save Plan")
        
        if submitted:
            if patient_name.strip() and selected_mods:
                current_date = start_date
                sessions_created = 0
                
                allowed_days = [5, 0, 2] if schedule_pattern == "Sat / Mon / Wed" else [6, 1, 3]
                
                while sessions_created < total_sessions:
                    if current_date.weekday() in allowed_days:
                        new_entry = {
                            "patient": patient_name.strip(),
                            "doctor": assigned_pt,
                            "type": care_type,
                            "total_sessions": int(total_sessions),
                            "completed_sessions": 0,
                            "selected_modalities": ", ".join(selected_mods),
                            "booking_date": str(current_date),
                            "time_slot": time_slot,
                            "status": "Active"
                        }
                        st.session_state.care_plans.append(new_entry)
                        sessions_created += 1
                    current_date += datetime.timedelta(days=1)
                
                save_data(st.session_state.care_plans, st.session_state.usage_logs)
                st.success(f"Successfully created and auto-scheduled {total_sessions} recurring sessions for {patient_name}!")
            else:
                st.error("Please enter patient name and select at least one modality.")

# ---------------------------------------------------------
# 4. EDIT / MANAGE PATIENTS
# ---------------------------------------------------------
elif menu == "Edit / Manage Patients":
    st.header("Edit or Remove Patient Bookings")
    
    if not st.session_state.care_plans:
        st.info("No patient records to edit.")
    else:
        unique_patients = list(set([p['patient'] for p in st.session_state.care_plans]))
        selected_p = st.selectbox("Select Patient to Modify or Remove:", unique_patients)
        
        st.divider()
        col_edit, col_del = st.columns([3, 1])
        
        with col_edit:
            st.subheader(f"Edit Details for: {selected_p}")
            new_name = st.text_input("Correct Patient Name", value=selected_p)
            new_doc = st.selectbox("Change Assigned PT", st.session_state.doctors)
            
            if st.button("Update Patient Info"):
                for p in st.session_state.care_plans:
                    if p['patient'] == selected_p:
                        p['patient'] = new_name.strip()
                        p['doctor'] = new_doc
                save_data(st.session_state.care_plans, st.session_state.usage_logs)
                st.success(f"Updated info for {selected_p} to {new_name}!")
                st.rerun()

        with col_del:
            st.subheader("Remove Patient")
            st.write("Remove schedule bookings (keeps device analytics history intact)?")
            if st.button("🔴 Remove Patient Schedule"):
                st.session_state.care_plans = [p for p in st.session_state.care_plans if p['patient'] != selected_p]
                save_data(st.session_state.care_plans, st.session_state.usage_logs)
                st.warning(f"Removed active bookings for {selected_p}. Device usage statistics remain preserved.")
                st.rerun()

# ---------------------------------------------------------
# 5. DEVICE ANALYTICS & MANUAL ADJUSTMENTS
# ---------------------------------------------------------
elif menu == "Device Analytics":
    st.header("Monthly Device Usage Analytics & Adjustments")
    
    col_m, col_y = st.columns(2)
    selected_month_name = col_m.selectbox("Select Month:", MONTH_NAMES, index=datetime.date.today().month - 1)
    selected_year = col_y.number_input("Select Year:", min_value=2024, max_value=2030, value=datetime.date.today().year)
    
    target_month_str = f"{selected_month_name} {selected_year}"
    
    # Process logs
    if st.session_state.usage_logs:
        df = pd.DataFrame(st.session_state.usage_logs)
        df['date'] = pd.to_datetime(df['date'])
        df['Month_Year'] = df['date'].dt.strftime('%B %Y')
        filtered = df[df['Month_Year'] == target_month_str]
    else:
        filtered = pd.DataFrame()

    if filtered.empty:
        st.info(f"No device usage recorded for {target_month_str}.")
        counts = pd.DataFrame({'Device / Modality': st.session_state.devices, 'Monthly Uses': [0]*len(st.session_state.devices)})
    else:
        counts = filtered['device'].value_counts().reset_index()
        counts.columns = ['Device / Modality', 'Monthly Uses']
        
        # Ensure all registered devices are displayed
        all_devs = pd.DataFrame({'Device / Modality': st.session_state.devices})
        counts = pd.merge(all_devs, counts, on='Device / Modality', how='left').fillna(0)
        counts['Monthly Uses'] = counts['Monthly Uses'].astype(int)

    c1, c2 = st.columns([2, 3])
    c1.dataframe(counts, use_container_width=True)
    c2.bar_chart(data=counts, x='Device / Modality', y='Monthly Uses')
    
    st.divider()
    st.subheader("Manual Device Count Adjustment")
    st.caption("Use this section to correct or log missed device uses manually.")
    
    with st.form("manual_device_adj"):
        col_d, col_num = st.columns(2)
        adj_device = col_d.selectbox("Select Device to Adjust", st.session_state.devices)
        adj_count = col_num.number_input("Add or Subtract Count (e.g. +1 or -1)", value=1, step=1)
        
        if st.form_submit_button("Apply Count Adjustment"):
            selected_month_idx = MONTH_NAMES.index(selected_month_name) + 1
            adj_date = str(datetime.date(selected_year, selected_month_idx, 1))
            
            if adj_count > 0:
                for _ in range(int(adj_count)):
                    st.session_state.usage_logs.append({
                        "date": adj_date,
                        "device": adj_device,
                        "patient": "Manual Adjustment"
                    })
            elif adj_count < 0:
                # Remove specified number of entries
                to_remove = abs(int(adj_count))
                new_logs = []
                for log in st.session_state.usage_logs:
                    log_month = pd.to_datetime(log['date']).strftime('%B %Y')
                    if log['device'] == adj_device and log_month == target_month_str and to_remove > 0:
                        to_remove -= 1
                    else:
                        new_logs.append(log)
                st.session_state.usage_logs = new_logs

            save_data(st.session_state.care_plans, st.session_state.usage_logs)
            st.success(f"Updated {adj_device} usage count for {target_month_str}!")
            st.rerun()

# ---------------------------------------------------------
# 6. SETTINGS
# ---------------------------------------------------------
elif menu == "Settings":
    st.header("Clinic Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Equipment List")
        for d in st.session_state.devices:
            st.write(f"• {d}")
        new_d = st.text_input("Add Device")
        if st.button("Add Equipment"):
            if new_d.strip() and new_d not in st.session_state.devices:
                st.session_state.devices.append(new_d.strip())
                st.rerun()

    with col2:
        st.subheader("Physiotherapists")
        for doc in st.session_state.doctors:
            st.write(f"• {doc}")
        new_doc = st.text_input("Add PT")
        if st.button("Add Therapist"):
            if new_doc.strip() and new_doc not in st.session_state.doctors:
                st.session_state.doctors.append(new_doc.strip())
                st.rerun()