from flask import Flask, render_template
import pandas as pd
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
from flask import request
import random
import time
import os

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Dictionary to store client sessions
client_sessions = {}

df_patients = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Patients")
df_staff = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Staff")
df_vehicles = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Vehicles")
today = datetime(2026, 4, 14)

# Compute monthly inpatients and outpatients from historical data
df_patients['Month'] = df_patients['Registration_Date'].dt.to_period('M')
monthly_counts = df_patients.groupby(['Month', 'Type']).size().unstack(fill_value=0)
inpatient_counts = monthly_counts.get('Inpatient', pd.Series()).values.tolist()
outpatient_counts = monthly_counts.get('Outpatient', pd.Series()).values.tolist()

# Global variables for real-time trend data
real_time_labels = []
real_time_in_data = []
real_time_out_data = []
counter = 0

def generate_real_time_patient_values():
    """
    Function to generate real-time values for inpatients and outpatients.
    Randomly selects from historical monthly counts in the Excel data.
    """
    inpatients = random.choice(inpatient_counts) if inpatient_counts else random.randint(100, 200)
    outpatients = random.choice(outpatient_counts) if outpatient_counts else random.randint(200, 400)
    return inpatients, outpatients

# Initialize real-time data with some initial points
for i in range(10):
    in_val, out_val = generate_real_time_patient_values()
    current_time = (datetime.now() - timedelta(seconds=(10 - i) * 10)).strftime('%H:%M:%S')
    real_time_labels.append(current_time)
    real_time_in_data.append(in_val)
    real_time_out_data.append(out_val)

# Precompute original data
total_patients = int(len(df_patients))
hospitalized = int(df_patients['Discharge_Date'].isna().sum())
admissions_week = int(df_patients[(df_patients['Registration_Date'] >= today - timedelta(days=7))].shape[0])
admissions_month = int(df_patients[(df_patients['Registration_Date'] >= today - timedelta(days=30))].shape[0])

df_patients['Month'] = df_patients['Registration_Date'].dt.to_period('M')
df_patients['Year'] = df_patients['Registration_Date'].dt.year
years = sorted(df_patients['Year'].unique().tolist())
years = ["Total"] + years

staff_counts = df_staff['Role'].value_counts().to_dict()
staff_labels = list(staff_counts.keys())
staff_data = [int(v) for v in staff_counts.values()]

vehicle_counts = df_vehicles['Status'].value_counts()
vehicles_data = [int(vehicle_counts.get('Available', 0)), int(vehicle_counts.get('In Mission', 0))]

dept_labels = []

def compute_data_for_year(year):
    # Fixed data for each year
    if year == 2025:
        total_patients = 1200
        hospitalized = 350
        admissions_week = 23
        admissions_month = 100
        delta_total = 5.2
        delta_hospitalized = -2.1
        delta_week = 10.5
        delta_month = 8.3
        months = [f'{year}-{str(i).zfill(2)}' for i in range(1, 13)]
        trend_in_data = [120, 135, 110, 145, 160, 130, 140, 155, 125, 170, 180, 165]
        trend_out_data = [300, 320, 280, 350, 380, 310, 340, 370, 290, 400, 420, 390]
        dept_data = [100, 80, 120, 90, 110]
        dept_status = ['Increasing', 'Stable', 'Decreasing', 'Increasing', 'Stable']
        gender_data = [660, 540]  # ~55% female, 45% male
        staff_data = [50, 60, 55]
        vehicles_data = [10, 5, 3]  # Available, In Mission, Maintenance
    elif year == "Total":
        base_patients = 1450
        base_hospitalized = 420
        base_week = 28
        base_month = 121
        total_patients = base_patients + random.randint(-100, 100)
        hospitalized = base_hospitalized + random.randint(-50, 50)
        admissions_week = base_week + random.randint(-10, 10)
        admissions_month = base_month + random.randint(-20, 20)
        delta_total = 3.5 + random.uniform(-3, 3)
        delta_hospitalized = 1.2 + random.uniform(-2, 2)
        delta_week = -5.0 + random.uniform(-5, 5)
        delta_month = 2.8 + random.uniform(-4, 4)
        # Use real-time trend data for Total
        months = real_time_labels
        trend_in_data = real_time_in_data
        trend_out_data = real_time_out_data
        dept_data = [val + random.randint(-20, 20) for val in [138, 52, 58, 126, 83]]
        dept_status = random.choices(['Stable', 'Increasing', 'Decreasing'], k=5)
        gender_data = [val + random.randint(-50, 50) for val in [788, 662]]
        staff_data = [val + random.randint(-10, 10) for val in [67, 59, 51]]
        vehicles_data = [val + random.randint(-3, 3) for val in [12, 7, 3]]
    else:  # 2026 - with slight variation for live feel
        base_patients = 1350
        base_hospitalized = 380
        base_week = 26
        base_month = 113
        total_patients = base_patients + random.randint(-50, 50)
        hospitalized = base_hospitalized + random.randint(-20, 20)
        admissions_week = base_week + random.randint(-5, 5)
        admissions_month = base_month + random.randint(-10, 10)
        delta_total = -1.8 + random.uniform(-2, 2)
        delta_hospitalized = 4.5 + random.uniform(-2, 2)
        delta_week = 12.3 + random.uniform(-5, 5)
        delta_month = -3.2 + random.uniform(-3, 3)
        months = [f'{year}-{str(i).zfill(2)}' for i in range(1, today.month + 1)]
        # Adjust trend data to match number of months
        num_months = len(months)
        base_in = [130, 145, 120, 155][:num_months]
        base_out = [310, 330, 290, 360][:num_months]
        trend_in_data = [val + random.randint(-10, 10) for val in base_in]
        trend_out_data = [val + random.randint(-20, 20) for val in base_out]
        dept_data = [val + random.randint(-10, 10) for val in [138, 52, 58, 126, 83]]
        dept_status = ['Decreasing', 'Decreasing', 'Increasing', 'Decreasing', 'Stable']
        gender_data = [val + random.randint(-20, 20) for val in [729, 621]]
        staff_data = [val + random.randint(-5, 5) for val in [67, 59, 51]]
        vehicles_data = [val + random.randint(-2, 2) for val in [12, 7, 3]]

    dept_labels = ["Cardiology", "Neurology", "Surgery", "Pediatrics", "Oncology"]

    return {
        'trend_labels': months,
        'trend_out_data': trend_out_data,
        'trend_in_data': trend_in_data,
        'dept_labels': dept_labels,
        'dept_data': dept_data,
        'dept_status': dept_status,
        'gender_data': gender_data,
        'staff_data': staff_data,
        'vehicles_data': vehicles_data,
        'total_patients': total_patients,
        'hospitalized': hospitalized,
        'admissions_week': admissions_week,
        'admissions_month': admissions_month,
        'delta_total': delta_total,
        'delta_hospitalized': delta_hospitalized,
        'delta_week': delta_week,
        'delta_month': delta_month
    }

dashboardData = compute_data_for_year(2026)

def generate_random_data(original, variation=1.0):
    return [max(0, int(val + val * (random.random() - 0.5) * variation * 2)) for val in original]

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    client_sessions[request.sid] = {'year': 'Total'}
    initial_data = compute_data_for_year("Total")
    emit('update_data', initial_data)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in client_sessions:
        del client_sessions[request.sid]

@socketio.on('change_year')
def handle_change_year(data):
    year = data['year']
    client_sessions[request.sid]['year'] = year
    new_data = compute_data_for_year(year)
    emit('update_data', new_data)

@socketio.on('refresh_data')
def handle_refresh_data():
    year = client_sessions[request.sid]['year']
    new_data = compute_data_for_year(year)
    emit('update_data', new_data)

def background_task():
    global counter
    while True:
        time.sleep(1)  # Update every 1 second for true real-time feel
        counter += 1
        if counter % 10 == 0:  # Every 10 seconds, add a new real-time data point
            in_val, out_val = generate_real_time_patient_values()
            current_time = datetime.now().strftime('%H:%M:%S')
            real_time_labels.append(current_time)
            real_time_in_data.append(in_val)
            real_time_out_data.append(out_val)
            # Keep only the last 20 points
            if len(real_time_labels) > 20:
                real_time_labels.pop(0)
                real_time_in_data.pop(0)
                real_time_out_data.pop(0)
        print(f"Sending real-time updates to {len(client_sessions)} clients")
        # Emit to each connected client based on their selected year
        for sid in list(client_sessions.keys()):
            year = client_sessions[sid]['year']
            new_data = compute_data_for_year(year)
            socketio.emit('update_data', new_data, to=sid)

@app.route('/')
def index():
    initial_data = compute_data_for_year("Total")
    data = initial_data.copy()
    data['years'] = years
    data['default_year'] = "Total"
    data['staff_labels'] = staff_labels  # Ensure staff_labels is included
    return render_template("index.html", data=data)

if __name__ == "__main__":
    socketio.start_background_task(background_task)
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)