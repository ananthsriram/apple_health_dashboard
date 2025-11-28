from flask import Flask, render_template, jsonify, request
import os
import json
from collections import defaultdict
from parser import parse_workouts_to_csv, aggregate_from_csv, format_aggregated_data

try:
    from config import DATA_DIR
except ImportError:
    # Fallback if config.py doesn't exist
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_FILE = os.path.join(DATA_DIR, 'export.xml')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed_data')

def ensure_data_processed():
    """
    Checks if processed data exists.
    """
    if not os.path.exists(PROCESSED_DIR) or not os.listdir(PROCESSED_DIR):
        return False
    return True

@app.route('/')
def index():
    if not ensure_data_processed():
        return "Data not processed. Please run 'python process_data.py' in your terminal first."
    return render_template('index.html')

@app.route('/api/activities')
def get_activities():
    ensure_data_processed()
    if not os.path.exists(PROCESSED_DIR):
        return jsonify([])
    
    activities = [d for d in os.listdir(PROCESSED_DIR) if os.path.isdir(os.path.join(PROCESSED_DIR, d))]
    return jsonify(sorted(activities))

# Simple in-memory cache: activity_name -> formatted_data
DATA_CACHE = {}

@app.route('/api/data')
def data():
    activity = request.args.get('activity')
    if not activity:
        return jsonify([])
    
    # Check cache first
    if activity in DATA_CACHE:
        return jsonify(DATA_CACHE[activity])
    
    # Handle "Total" - aggregate all activities
    if activity == 'Total':
        all_data = defaultdict(lambda: defaultdict(lambda: {
            'count': 0,
            'duration': 0.0,
            'energy': 0.0,
            'distance': 0.0
        }))
        
        # Read all activity JSONs and aggregate
        if os.path.exists(PROCESSED_DIR):
            for activity_dir in os.listdir(PROCESSED_DIR):
                json_path = os.path.join(PROCESSED_DIR, activity_dir, 'aggregated.json')
                if os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        activity_data = json.load(f)
                        for year_data in activity_data:
                            year = year_data['year']
                            for i, month in enumerate(year_data['labels']):
                                all_data[year][month]['count'] += year_data['datasets']['count'][i]
                                all_data[year][month]['duration'] += year_data['datasets']['duration'][i]
                                all_data[year][month]['energy'] += year_data['datasets']['energy'][i]
                                all_data[year][month]['distance'] += year_data['datasets']['distance'][i]
        
        # Format the aggregated data
        formatted_result = []
        sorted_years = sorted(all_data.keys())
        
        for year in sorted_years:
            months_data = all_data[year]
            month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                        'July', 'August', 'September', 'October', 'November', 'December']
            
            sorted_months = [m for m in month_order if m in months_data]
            
            durations = [months_data[m]['duration'] for m in sorted_months]
            energies = [months_data[m]['energy'] for m in sorted_months]
            distances = [months_data[m]['distance'] for m in sorted_months]
            counts = [months_data[m]['count'] for m in sorted_months]
            
            formatted_result.append({
                'year': year,
                'labels': sorted_months,
                'datasets': {
                    'duration': durations,
                    'energy': energies,
                    'distance': distances,
                    'count': counts
                }
            })
        
        DATA_CACHE[activity] = formatted_result
        return jsonify(formatted_result)
    
    # Try reading pre-aggregated JSON
    json_path = os.path.join(PROCESSED_DIR, activity, 'aggregated.json')
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            formatted_data = json.load(f)
            DATA_CACHE[activity] = formatted_data
            return jsonify(formatted_data)

    # Fallback to CSV (slow)
    csv_path = os.path.join(PROCESSED_DIR, activity, 'workouts.csv')
    if os.path.exists(csv_path):
        aggregated_data = aggregate_from_csv(csv_path)
        formatted_data = format_aggregated_data(aggregated_data)
        DATA_CACHE[activity] = formatted_data
        return jsonify(formatted_data)
        
    return jsonify([])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
