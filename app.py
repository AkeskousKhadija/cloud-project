from flask import Flask, render_template, request
import pandas as pd
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
import random
import time
import os

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    logger=True,
    engineio_logger=True
)

# Dictionary to store client sessions
client_sessions = {}

# ✅ FIX: Safe Excel path for Railway
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(BASE_DIR, "Healthcare_Dashboard_Full_Data.xlsx")

df_patients = pd.read_excel(file_path, sheet_name="Patients")
df_staff = pd.read_excel(file_path, sheet_name="Staff")
df_vehicles = pd.read_excel(file_path, sheet_name="Vehicles")

today = datetime(2026, 4, 14)

# Compute monthly inpatients and outpatients
df_patients['Month'] = df_patients['Registration_Date'].dt.to_period('M')
monthly_counts = df_patients.groupby(['Month', 'Type']).size().unstack(fill_value=0)

inpatient_counts = monthly_counts.get('Inpatient', pd.Series()).values.tolist()
outpatient_counts = monthly_counts.get('Outpatient', pd.Series()).values.tolist()

# Real-time data
real_time_labels = []
real_time_in_data = []
real_time_out_data = []
counter = 0


def generate_real_time_patient_values():
    inpatients = random.choice(inpatient_counts) if inpatient_counts else random.randint(100, 200)
    outpatients = random.choice(outpatient_counts) if outpatient_counts else random.randint(200, 400)
    return inpatients, outpatients


# Init realtime data
for i in range(10):
    in_val, out_val = generate_real_time_patient_values()
    current_time = (datetime.now() - timedelta(seconds=(10 - i) * 10)).strftime('%H:%M:%S')
    real_time_labels.append(current_time)
    real_time_in_data.append(in_val)
    real_time_out_data.append(out_val)

# Precompute
total_patients = int(len(df_patients))
hospitalized = int(df_patients['Discharge_Date'].isna().sum())

years = sorted(df_patients['Registration_Date'].dt.year.unique().tolist())
years = ["Total"] + years

staff_counts = df_staff['Role'].value_counts().to_dict()
staff_labels = list(staff_counts.keys())

vehicle_counts = df_vehicles['Status'].value_counts()
vehicles_data = [
    int(vehicle_counts.get('Available', 0)),
    int(vehicle_counts.get('In Mission', 0))
]


def compute_data_for_year(year):
    if year == 2025:
        months = [f'{year}-{str(i).zfill(2)}' for i in range(1, 13)]
        trend_in_data = [120, 135, 110, 145, 160, 130, 140, 155, 125, 170, 180, 165]
        trend_out_data = [300, 320, 280, 350, 380, 310, 340, 370, 290, 400, 420, 390]

    elif year == "Total":
        months = real_time_labels
        trend_in_data = real_time_in_data
        trend_out_data = real_time_out_data

    else:
        months = [f'{year}-{str(i).zfill(2)}' for i in range(1, 13)]
        trend_in_data = [100] * 12
        trend_out_data = [200] * 12

    return {
        'trend_labels': months,
        'trend_out_data': trend_out_data,
        'trend_in_data': trend_in_data,
        'staff_labels': staff_labels,
        'vehicles_data': vehicles_data,
        'total_patients': total_patients,
        'hospitalized': hospitalized,
    }


@socketio.on('connect')
def handle_connect():
    client_sessions[request.sid] = {'year': 'Total'}
    emit('update_data', compute_data_for_year("Total"))


@socketio.on('disconnect')
def handle_disconnect():
    client_sessions.pop(request.sid, None)


@socketio.on('change_year')
def handle_change_year(data):
    year = data['year']
    client_sessions[request.sid]['year'] = year
    emit('update_data', compute_data_for_year(year))


@socketio.on('refresh_data')
def handle_refresh_data():
    year = client_sessions[request.sid]['year']
    emit('update_data', compute_data_for_year(year))


def background_task():
    global counter
    while True:
        socketio.sleep(1)
        counter += 1

        if counter % 10 == 0:
            in_val, out_val = generate_real_time_patient_values()
            current_time = datetime.now().strftime('%H:%M:%S')

            real_time_labels.append(current_time)
            real_time_in_data.append(in_val)
            real_time_out_data.append(out_val)

            if len(real_time_labels) > 20:
                real_time_labels.pop(0)
                real_time_in_data.pop(0)
                real_time_out_data.pop(0)

        for sid in list(client_sessions.keys()):
            year = client_sessions[sid]['year']
            socketio.emit('update_data', compute_data_for_year(year), to=sid)


@app.route('/')
def index():
    data = compute_data_for_year("Total")
    data['years'] = years
    data['default_year'] = "Total"
    return render_template("index.html", data=data)


if __name__ == "__main__":
    socketio.start_background_task(background_task)
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)