from flask import Flask, render_template, jsonify, request
import os
import json
import csv
from collections import defaultdict
from datetime import datetime, timedelta
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

def parse_date(date_str):
    if not date_str:
        return None
    try:
        # Standardize date format: sometimes Apple Health export or CSVs might have different lengths
        # Just grab the date part YYYY-MM-DD
        return datetime.strptime(date_str[:10], '%Y-%m-%d')
    except:
        return None

def categorize_activity(activity_name):
    """Map Apple Health activity types to Strength Training or Cardio"""
    if not activity_name:
        return 'Cardio'
    
    strength_keywords = {'strength', 'core', 'bodyweight', 'yoga', 'mindandbody', 'resistance'}
    lower_name = activity_name.lower()
    
    for kw in strength_keywords:
        if kw in lower_name:
            return 'Strength Training'
            
    return 'Cardio'

def safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        # Handle cases with units or spaces
        clean_val = str(value).split()[0].replace(',', '')
        return float(clean_val)
    except (ValueError, IndexError):
        return default

def aggregate_metric_by_date(csv_path, date_col, val_col, start_date_str, end_date_str, dataset_name, granularity='monthly'):
    """Helper to aggregate CSV data by month or day with date range filtering"""
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    # Structure: all_data[year][label] += value
    all_data = defaultdict(lambda: defaultdict(float))
    
    if not os.path.exists(csv_path):
        return []

    with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt_str = row.get(date_col, '')
                dt = parse_date(dt_str)
                if not dt: continue
                
                if start_date and dt < start_date: continue
                if end_date and dt > end_date: continue
                
                year = dt.year
                
                if granularity == 'daily':
                    label = dt.strftime('%Y-%m-%d')
                else:
                    label = dt.strftime('%B')
                    
                all_data[year][label] += safe_float(row.get(val_col, 0))
            except:
                continue
    
    # Format results
    formatted_result = []
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
                  
    for year in sorted(all_data.keys()):
        year_data = all_data[year]
        
        if granularity == 'daily':
            sorted_labels = sorted(year_data.keys())
        else:
            sorted_labels = [m for m in month_order if m in year_data]
            
        values = [year_data[lbl] for lbl in sorted_labels]
        
        formatted_result.append({
            'year': year,
            'labels': sorted_labels,
            'datasets': {
                dataset_name: values
            }
        })
        
    return formatted_result

def aggregate_heart_rate_by_date(csv_path, start_date_str, end_date_str):
    """Special helper for heart rate aggregation"""
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    # Store lists of values to calculate avg and max
    vals = defaultdict(lambda: defaultdict(list))
    
    if not os.path.exists(csv_path):
        return []

    with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt_str = row.get('startDate', '')
                dt = parse_date(dt_str)
                if not dt: continue
                
                if start_date and dt < start_date: continue
                if end_date and dt > end_date: continue
                
                year = dt.year
                month = dt.strftime('%B')
                val = safe_float(row.get('value', 0))
                if val > 0:
                    vals[year][month].append(val)
            except:
                continue
                
    result = []
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
                  
    for year in sorted(vals.keys()):
        months_data = vals[year]
        sorted_months = [m for m in month_order if m in months_data]
        
        avg_hr = [round(sum(months_data[m])/len(months_data[m]), 1) for m in sorted_months]
        max_hr = [max(months_data[m]) for m in sorted_months]
        
        result.append({
            'year': year,
            'labels': sorted_months,
            'datasets': {
                'avg_heart_rate': avg_hr,
                'max_heart_rate': max_hr
            }
        })
    return result

def format_monthly_data(all_data, dataset_name):
    """Generic monthly data formatter"""
    formatted_result = []
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
                  
    for year in sorted(all_data.keys()):
        months_data = all_data[year]
        sorted_months = [m for m in month_order if m in months_data]
        values = [months_data[m] for m in sorted_months]
        
        formatted_result.append({
            'year': year,
            'labels': sorted_months,
            'datasets': {
                dataset_name: values
            }
        })
    return formatted_result

@app.route('/api/activities')
def get_activities():
    ensure_data_processed()
    if not os.path.exists(PROCESSED_DIR):
        return jsonify([])
    
    # Filter out special directories (sleep, steps, heart_rate)
    special_dirs = {'sleep', 'steps', 'heart_rate'}
    activities = [d for d in os.listdir(PROCESSED_DIR) 
                  if os.path.isdir(os.path.join(PROCESSED_DIR, d)) and d not in special_dirs]
    return jsonify(sorted(activities))

# Simple in-memory cache: activity_name -> formatted_data
DATA_CACHE = {}

@app.route('/api/data')
def data():
    activity = request.args.get('activity')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    granularity = request.args.get('granularity', 'monthly') # daily or monthly
    group_by_category = request.args.get('group_by_category') == 'true'
    
    if not activity:
        return jsonify([])
    
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    # Simple in-memory cache skip for variety of params
    if not (start_date_str or end_date_str or granularity != 'monthly' or group_by_category) and activity in DATA_CACHE:
        return jsonify(DATA_CACHE[activity])
    
    # all_data[year][label][bucket_name] = stats
    # bucket_name will be activity name or category name
    all_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        'count': 0,
        'duration': 0.0,
        'energy': 0.0,
        'distance': 0.0
    })))
    
    activities_to_process = []
    if activity == 'Total':
        special_dirs = {'sleep', 'steps', 'heart_rate'}
        if os.path.exists(PROCESSED_DIR):
            activities_to_process = [d for d in os.listdir(PROCESSED_DIR) if d not in special_dirs]
    else:
        activities_to_process = [activity]

    for act in activities_to_process:
        csv_path = os.path.join(PROCESSED_DIR, act, 'workouts.csv')
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        dt_str = row.get('startDate', '')
                        dt = parse_date(dt_str)
                        if not dt: continue
                        
                        if start_date and dt < start_date: continue
                        if end_date and dt > end_date: continue
                        
                        year = dt.year
                        label = dt.strftime('%Y-%m-%d') if granularity == 'daily' else dt.strftime('%B')
                        
                        # Decide bucket
                        bucket = categorize_activity(act) if group_by_category else act
                        
                        stats = all_data[year][label][bucket]
                        stats['count'] += 1
                        stats['duration'] += safe_float(row.get('duration', 0))
                        stats['energy'] += safe_float(row.get('stat_ActiveEnergyBurned_sum') or row.get('totalEnergyBurned') or 0)
                        stats['distance'] += safe_float(row.get('stat_DistanceWalkingRunning_sum') or row.get('totalDistance') or 0)
                    except:
                        continue

    # Format result
    formatted_result = []
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
                  
    for year in sorted(all_data.keys()):
        year_data = all_data[year]
        sorted_labels = sorted(year_data.keys()) if granularity == 'daily' else [m for m in month_order if m in year_data]
        
        datasets = {
            'count': {}, 'duration': {}, 'energy': {}, 'distance': {},
            'avg_duration': {}, 'avg_energy': {}
        }
        
        # Collect all buckets present in this year
        found_buckets = set()
        for label in sorted_labels:
            for b in year_data[label]:
                found_buckets.add(b)
        
        metrics = ['count', 'duration', 'energy', 'distance']
        avg_metrics = [('avg_duration', 'duration'), ('avg_energy', 'energy')]
        
        # If activity is Total or group_by_category is enabled
        if activity == 'Total' or group_by_category:
            all_m = metrics + [am[0] for am in avg_metrics]
            buckets_to_show = sorted(found_buckets)
            
            for m in all_m:
                datasets[m]['Total'] = []
                for b in buckets_to_show:
                    datasets[m][b] = []
                
            for label in sorted_labels:
                totals = {m: 0 for m in metrics}
                for b in buckets_to_show:
                    b_stats = year_data[label][b]
                    for m in metrics:
                        val = b_stats[m]
                        datasets[m][b].append(round(val, 1))
                        totals[m] += val
                    
                    # Individual bucket averages
                    c = b_stats['count']
                    for m_avg, m_sum in avg_metrics:
                        datasets[m_avg][b].append(round(b_stats[m_sum] / c, 1) if c > 0 else 0)
                
                # Append Overall Totals
                for m in metrics:
                    datasets[m]['Total'].append(round(totals[m], 1))
                total_c = totals['count']
                for m_avg, m_sum in avg_metrics:
                    datasets[m_avg]['Total'].append(round(totals[m_sum] / total_c, 1) if total_c > 0 else 0)
        else:
            # Single activity, no categorization
            for m in metrics:
                datasets[m] = [round(year_data[label][activity][m], 1) for label in sorted_labels]
            for m_avg, m_sum in avg_metrics:
                datasets[m_avg] = [
                    round(year_data[label][activity][m_sum] / year_data[label][activity]['count'], 1) 
                    if year_data[label][activity]['count'] > 0 else 0 
                    for label in sorted_labels
                ]
        
        formatted_result.append({
            'year': year,
            'labels': sorted_labels,
            'datasets': datasets
        })
    
    if not (start_date_str or end_date_str or granularity != 'monthly' or group_by_category):
        DATA_CACHE[activity] = formatted_result
        
    return jsonify(formatted_result)

@app.route('/api/sleep')
def get_sleep_data():
    """Get sleep data with date filtering"""
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    json_path = os.path.join(PROCESSED_DIR, 'sleep', 'aggregated.json')
    if not os.path.exists(json_path):
        return jsonify([])
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    if not (start_date_str or end_date_str):
        return jsonify(data)
        
    # If filtered, we need to recalculate from original source if possible, 
    # but for now let's just filter the aggregated data by month if it fits,
    # or better, look for the source CSV.
    csv_path = os.path.join(PROCESSED_DIR, 'sleep', 'sleep.csv')
    if os.path.exists(csv_path):
        # Implement on-the-fly aggregation for filtered data
        return jsonify(aggregate_metric_by_date(csv_path, 'startDate', 'value', start_date_str, end_date_str, 'sleep_hours'))
        
    return jsonify(data)

@app.route('/api/steps')
def get_steps_data():
    """Get steps data with date filtering and granularity"""
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    granularity = request.args.get('granularity', 'monthly')
    
    csv_path = os.path.join(PROCESSED_DIR, 'steps', 'steps.csv')
    
    # If daily or filtered, stick to CSV aggregation for consistency
    if os.path.exists(csv_path) and (granularity == 'daily' or start_date_str or end_date_str):
        return jsonify(aggregate_metric_by_date(csv_path, 'startDate', 'value', start_date_str, end_date_str, 'total_steps', granularity))

    json_path = os.path.join(PROCESSED_DIR, 'steps', 'aggregated.json')
    if not os.path.exists(json_path):
        return jsonify([])
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    return jsonify(data)

@app.route('/api/heart_rate')
def get_heart_rate_data():
    """Get heart rate data with date filtering"""
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    json_path = os.path.join(PROCESSED_DIR, 'heart_rate', 'aggregated.json')
    if not os.path.exists(json_path):
        return jsonify([])
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    if not (start_date_str or end_date_str):
        return jsonify(data)
        
    csv_path = os.path.join(PROCESSED_DIR, 'heart_rate', 'heart_rate.csv')
    if os.path.exists(csv_path):
        # Heart rate is special (avg and max)
        return jsonify(aggregate_heart_rate_by_date(csv_path, start_date_str, end_date_str))
        
    return jsonify(data)

@app.route('/api/statistics')
def get_statistics():
    """
    Calculate and return summary statistics across all workouts
    Supports optional date range filtering via start_date and end_date parameters
    """
    # Get date range parameters
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except:
            pass
    
    stats = {
        'total_workouts': 0,
        'total_duration_minutes': 0,
        'total_energy_burned': 0,
        'total_distance': 0,
        'avg_workouts_per_week': 0,
        'avg_workouts_per_month': 0,
        'avg_duration_per_workout': 0,
        'date_range': {
            'start': start_date_str or 'All time',
            'end': end_date_str or 'Present'
        }
    }
    
    if not os.path.exists(PROCESSED_DIR):
        return jsonify(stats)
    
    special_dirs = {'sleep', 'steps', 'heart_rate'}
    all_workouts = []
    
    for activity_dir in os.listdir(PROCESSED_DIR):
        if activity_dir in special_dirs:
            continue
        csv_path = os.path.join(PROCESSED_DIR, activity_dir, 'workouts.csv')
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # Parse workout date
                        dt_str = row.get('startDate', '')
                        dt = parse_date(dt_str)
                        if not dt: continue
                        
                        # Apply date range filter
                        if start_date and dt < start_date:
                            continue
                        if end_date and dt > end_date:
                            continue
                        
                        stats['total_workouts'] += 1
                        
                        stats['total_duration_minutes'] += safe_float(row.get('duration', 0))
                        
                        energy = row.get('stat_ActiveEnergyBurned_sum') or row.get('totalEnergyBurned') or 0
                        stats['total_energy_burned'] += safe_float(energy)
                        
                        distance = row.get('stat_DistanceWalkingRunning_sum') or row.get('totalDistance') or 0
                        stats['total_distance'] += safe_float(distance)
                        
                        all_workouts.append(dt_str[:10])
                    except Exception as e:
                        continue
    
    # Calculate averages
    if stats['total_workouts'] > 0:
        stats['avg_duration_per_workout'] = stats['total_duration_minutes'] / stats['total_workouts']
        
        # Calculate date range for averages
        if all_workouts:
            dates = [datetime.strptime(d, '%Y-%m-%d') for d in all_workouts]
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                total_days = (max_date - min_date).days + 1
                total_weeks = total_days / 7
                total_months = total_days / 30.44
                
                if total_weeks > 0:
                    stats['avg_workouts_per_week'] = stats['total_workouts'] / total_weeks
                if total_months > 0:
                    stats['avg_workouts_per_month'] = stats['total_workouts'] / total_months
    
    # Round values
    for key in stats:
        if isinstance(stats[key], (int, float)):
            stats[key] = round(stats[key], 2)
    
    return jsonify(stats)


@app.route('/api/personal_records')
def get_personal_records():
    """
    Calculate personal records with global streak support
    """
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    records = {
        'longest_workout': {'duration': 0, 'activity': '', 'date': ''},
        'most_active_month': {'count': 0, 'month': '', 'year': 0},
        'current_streak': 0,
        'longest_streak': 0,
        'streak_type': 'Workout'
    }
    
    if not os.path.exists(PROCESSED_DIR):
        return jsonify(records)
    
    special_dirs = {'sleep', 'steps', 'heart_rate'}
    filtered_workouts = [] # For personal bests within range
    global_workouts = []   # For current streak calculation
    monthly_counts = defaultdict(int)
    
    for activity_dir in os.listdir(PROCESSED_DIR):
        if activity_dir in special_dirs:
            continue
        
        csv_path = os.path.join(PROCESSED_DIR, activity_dir, 'workouts.csv')
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        dt_str = row.get('startDate', '')
                        dt = parse_date(dt_str)
                        if not dt: continue
                        
                        date_str = dt_str[:10]
                        global_workouts.append(date_str)
                        
                        # Apply date range filter for personal records
                        if start_date and dt < start_date: continue
                        if end_date and dt > end_date: continue
                        
                        duration = safe_float(row.get('duration', 0))
                        if duration > records['longest_workout']['duration']:
                            records['longest_workout'] = {
                                'duration': round(duration, 2),
                                'activity': activity_dir,
                                'date': date_str
                            }
                        
                        filtered_workouts.append(date_str)
                        month_key = f"{dt.strftime('%B')} {dt.year}"
                        monthly_counts[month_key] += 1
                    except:
                        continue
    
    # Find most active month (within filtered range)
    if monthly_counts:
        most_active = max(monthly_counts.items(), key=lambda x: x[1])
        month_year = most_active[0].split()
        records['most_active_month'] = {
            'count': most_active[1],
            'month': month_year[0],
            'year': int(month_year[1])
        }
    
    # Calculate streaks
    if global_workouts:
        unique_dates = sorted(set(global_workouts))
        workout_dates = [datetime.strptime(d, '%Y-%m-%d') for d in unique_dates]
        
        # Longest streak overall (or within range? User said streaks plural, 
        # but usually personal best is overall. Let's keep it global for now 
        # to ensure it's truly a 'record'.)
        longest_streak = 0
        temp_streak = 1
        
        today = datetime.now().date()
        
        for i in range(len(workout_dates) - 1):
            diff = (workout_dates[i + 1] - workout_dates[i]).days
            if diff == 1:
                temp_streak += 1
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
        
        longest_streak = max(longest_streak, temp_streak)
        records['longest_streak'] = longest_streak
        
        # Current streak (Global)
        current_streak = 0
        if workout_dates:
            last_workout = workout_dates[-1].date()
            # If today is 26th, and last workout was 25th or 26th, streak is alive
            days_since = (today - last_workout).days
            if days_since <= 1:
                current_streak = 1
                for i in range(len(workout_dates) - 2, -1, -1):
                    diff = (workout_dates[i + 1] - workout_dates[i]).days
                    if diff == 1:
                        current_streak += 1
                    else:
                        break
        records['current_streak'] = current_streak
    
    return jsonify(records)

@app.route('/api/workout_details')
def get_workout_details():
    """
    Get detailed workout data with pagination and filtering
    """
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    activity_filter = request.args.get('activity', '')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    all_workouts = []
    special_dirs = {'sleep', 'steps', 'heart_rate'}
    
    for activity_dir in os.listdir(PROCESSED_DIR):
        if activity_dir in special_dirs:
            continue
        if activity_filter and activity_dir != activity_filter:
            continue
            
        csv_path = os.path.join(PROCESSED_DIR, activity_dir, 'workouts.csv')
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        dt_str = row.get('startDate', '')
                        dt = parse_date(dt_str)
                        if not dt: continue
                        
                        if start_date and dt < start_date: continue
                        if end_date and dt > end_date: continue
                        
                        workout = {
                            'activity': activity_dir,
                            'startDate': dt_str,
                            'duration': round(safe_float(row.get('duration', 0)), 2),
                            'energy': round(safe_float(row.get('stat_ActiveEnergyBurned_sum') or row.get('totalEnergyBurned')), 2),
                            'distance': round(safe_float(row.get('stat_DistanceWalkingRunning_sum') or row.get('totalDistance')), 2)
                        }
                        all_workouts.append(workout)
                    except:
                        continue
    
    # Sort by date (most recent first)
    all_workouts.sort(key=lambda x: x['startDate'], reverse=True)
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_workouts[start:end]
    
    return jsonify({
        'data': paginated,
        'total': len(all_workouts),
        'page': page,
        'per_page': per_page,
        'total_pages': (len(all_workouts) + per_page - 1) // per_page
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
