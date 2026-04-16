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
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    manage_session=False
)

# Dictionary to store client sessions
client_sessions = {}

df_patients = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Patients")
df_staff = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Staff")
df_vehicles = pd.read_excel("./Healthcare_Dashboard_Full_Data.xlsx", sheet_name="Vehicles")
today = datetime(2026, 4, 14)

# Compute monthly inpatients and outpatients from historical data (2025)
df_patients_2025 = df_patients[df_patients['Registration_Date'].dt.year == 2025].copy()
df_patients_2025['Month'] = df_patients_2025['Registration_Date'].dt.to_period('M')
monthly_counts_2025 = df_patients_2025.groupby(['Month', 'Type']).size().unstack(fill_value=0)
inpatient_counts_2025 = monthly_counts_2025.get('Inpatient', pd.Series()).values.tolist()
outpatient_counts_2025 = monthly_counts_2025.get('Outpatient', pd.Series()).values.tolist()

# Global variables for real-time trend data (for 2026)
real_time_labels = []
real_time_in_data = []
real_time_out_data = []
counter = 0

def generate_real_time_patient_values():
    """
    Function to generate real-time values for inpatients and outpatients for 2026.
    Randomly selects from historical monthly counts from 2025 data.
    """
    inpatients = random.choice(inpatient_counts_2025) if inpatient_counts_2025 else random.randint(100, 200)
    outpatients = random.choice(outpatient_counts_2025) if outpatient_counts_2025 else random.randint(200, 400)
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
        # Utiliser les données réelles de l'Excel pour 2025
        df_2025 = df_patients[df_patients['Registration_Date'].dt.year == 2025].copy()
        
        total_patients = int(len(df_2025))
        hospitalized = int(df_2025['Discharge_Date'].isna().sum())
        
        # Calculer les admissions pour 2025
        target_date_2025 = datetime(2025, today.month, today.day)
        admissions_week = int(df_2025[(df_2025['Registration_Date'] >= target_date_2025 - timedelta(days=7))].shape[0])
        admissions_month = int(df_2025[(df_2025['Registration_Date'] >= target_date_2025 - timedelta(days=30))].shape[0])
        
        # Calculer les tendances mensuelles pour 2025
        df_2025['Month'] = df_2025['Registration_Date'].dt.to_period('M')
        monthly_data = df_2025.groupby(['Month', 'Type']).size().unstack(fill_value=0)
        months = [f'2025-{str(i).zfill(2)}' for i in range(1, 13)]
        
        trend_in_data = []
        trend_out_data = []
        for month in months:
            month_period = pd.Period(month)
            if month_period in monthly_data.index:
                trend_in_data.append(int(monthly_data.loc[month_period].get('Inpatient', 0)))
                trend_out_data.append(int(monthly_data.loc[month_period].get('Outpatient', 0)))
            else:
                trend_in_data.append(0)
                trend_out_data.append(0)
        
        # Données des départements pour 2025
        dept_data = [138, 52, 58, 126, 83]
        dept_status = ['Increasing', 'Stable', 'Decreasing', 'Increasing', 'Stable']
        
        # Données des genres pour 2025
        gender_counts = df_2025['Gender'].value_counts()
        gender_data = [int(gender_counts.get('Female', 0)), int(gender_counts.get('Male', 0))]
        
        # Données du staff pour 2025
        staff_2025 = df_staff[df_staff['Hire_Date'].dt.year == 2025] if 'Hire_Date' in df_staff.columns else df_staff
        staff_counts_2025 = staff_2025['Role'].value_counts().to_dict()
        staff_data = [int(staff_counts_2025.get(role, 0)) for role in staff_labels]
        
        # Données des véhicules pour 2025
        vehicles_data = [12, 7, 3]
        
        # Calculer les pourcentages de changement
        delta_total = 5.2
        delta_hospitalized = -2.1
        delta_week = 10.5
        delta_month = 8.3
        
    elif year == 2026:
        # Utiliser les données générées aléatoirement pour 2026
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
        
        months = [f'2026-{str(i).zfill(2)}' for i in range(1, today.month + 1)]
        
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
        
    else:  # "Total" - Comparaison entre mois actuel et même mois de l'année dernière
        # Récupérer les données de 2025 et 2026
        data_2025 = compute_data_for_year(2025)
        data_2026 = compute_data_for_year(2026)
        
        # Sommer les données principales
        total_patients = data_2025['total_patients'] + data_2026['total_patients']
        hospitalized = data_2025['hospitalized'] + data_2026['hospitalized']
        admissions_week = data_2025['admissions_week'] + data_2026['admissions_week']
        admissions_month = data_2025['admissions_month'] + data_2026['admissions_month']
        
        # Calculer les moyennes pondérées pour les deltas
        delta_total = (data_2025['delta_total'] * data_2025['total_patients'] + 
                      data_2026['delta_total'] * data_2026['total_patients']) / total_patients if total_patients > 0 else 0
        delta_hospitalized = (data_2025['delta_hospitalized'] * data_2025['hospitalized'] + 
                             data_2026['delta_hospitalized'] * data_2026['hospitalized']) / hospitalized if hospitalized > 0 else 0
        delta_week = (data_2025['delta_week'] * data_2025['admissions_week'] + 
                     data_2026['delta_week'] * data_2026['admissions_week']) / admissions_week if admissions_week > 0 else 0
        delta_month = (data_2025['delta_month'] * data_2025['admissions_month'] + 
                      data_2026['delta_month'] * data_2026['admissions_month']) / admissions_month if admissions_month > 0 else 0
        
        # POUR TOTAL : Comparaison entre le mois actuel et le même mois de l'année dernière
        current_month_num = today.month
        current_month_str = f"{current_month_num:02d}/{today.year}"
        last_year_month_str = f"{current_month_num:02d}/{today.year - 1}"
        
        # Labels pour le graphique (2 barres: mois actuel vs même mois année dernière)
        months = [last_year_month_str, current_month_str]
        
        # Extraire les données pour le mois actuel de 2026
        current_month_in_2026 = 0
        current_month_out_2026 = 0
        
        # Extraire les données pour le même mois de 2025
        current_month_in_2025 = 0
        current_month_out_2025 = 0
        
        # Chercher les données pour 2026 (mois actuel)
        for i, label in enumerate(data_2026['trend_labels']):
            if len(label) >= 7 and '-' in label:
                month_num = int(label.split('-')[1])
                if month_num == current_month_num:
                    current_month_in_2026 = data_2026['trend_in_data'][i]
                    current_month_out_2026 = data_2026['trend_out_data'][i]
                    break
        
        # Chercher les données pour 2025 (même mois)
        for i, label in enumerate(data_2025['trend_labels']):
            if len(label) >= 7 and '-' in label:
                month_num = int(label.split('-')[1])
                if month_num == current_month_num:
                    current_month_in_2025 = data_2025['trend_in_data'][i]
                    current_month_out_2025 = data_2025['trend_out_data'][i]
                    break
        
        # Données du graphique: [année dernière, année actuelle]
        trend_in_data = [current_month_in_2025, current_month_in_2026]
        trend_out_data = [current_month_out_2025, current_month_out_2026]
        
        # Sommer les données des départements
        dept_data = [data_2025['dept_data'][i] + data_2026['dept_data'][i] for i in range(len(data_2025['dept_data']))]
        dept_status = random.choices(['Stable', 'Increasing', 'Decreasing'], k=5)
        
        # Sommer les données des genres
        gender_data = [data_2025['gender_data'][0] + data_2026['gender_data'][0], 
                      data_2025['gender_data'][1] + data_2026['gender_data'][1]]
        
        # Sommer les données du staff
        staff_data = [data_2025['staff_data'][i] + data_2026['staff_data'][i] for i in range(len(data_2025['staff_data']))]
        
        # Sommer les données des véhicules
        vehicles_data = [data_2025['vehicles_data'][i] + data_2026['vehicles_data'][i] for i in range(len(data_2025['vehicles_data']))]
    
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

socketio.start_background_task(background_task)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)