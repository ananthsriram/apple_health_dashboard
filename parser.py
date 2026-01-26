import xml.etree.ElementTree as ET
import csv
import os
from datetime import datetime
from collections import defaultdict

def parse_workouts_to_csv(xml_file, output_dir='processed_data'):
    """
    Parses the Apple Health export XML file and generates CSV files for each activity type.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Cache file handles to avoid opening/closing repeatedly
    # activity_type -> csv_writer
    csv_handles = {}
    csv_files = {}

    try:
        context = ET.iterparse(xml_file, events=('end',))
        
        for event, elem in context:
            if elem.tag == 'Workout':
                activity_type = elem.get('workoutActivityType')
                if activity_type:
                    # Strip prefix if present (e.g., HKWorkoutActivityTypeRunning -> Running)
                    if activity_type.startswith('HKWorkoutActivityType'):
                        activity_type = activity_type[len('HKWorkoutActivityType'):]
                    
                    # Create directory for activity if needed
                    activity_dir = os.path.join(output_dir, activity_type)
                    if not os.path.exists(activity_dir):
                        os.makedirs(activity_dir)
                        
                    csv_path = os.path.join(activity_dir, 'workouts.csv')
                    
                    # Initialize CSV if not already open
                    if activity_type not in csv_handles:
                        f = open(csv_path, 'w', newline='')
                        writer = csv.writer(f)
                        writer.writerow(['startDate', 'duration', 'totalEnergyBurned', 'totalDistance'])
                        csv_files[activity_type] = f
                        csv_handles[activity_type] = writer
                    
                    # Extract data
                    start_date = elem.get('startDate')
                    duration = elem.get('duration', '0')
                    energy = elem.get('totalEnergyBurned', '0')
                    distance = elem.get('totalDistance', '0')
                    
                    csv_handles[activity_type].writerow([start_date, duration, energy, distance])

                elem.clear()
        
    except Exception as e:
        print(f"Error parsing XML: {e}")
        raise e
    finally:
        # Close all files
        for f in csv_files.values():
            f.close()

def parse_sleep_data(xml_file, output_dir='processed_data'):
    """
    Parses sleep analysis data from Apple Health export.
    Sleep data is stored as HKCategoryTypeIdentifierSleepAnalysis records.
    """
    sleep_dir = os.path.join(output_dir, 'sleep')
    if not os.path.exists(sleep_dir):
        os.makedirs(sleep_dir)
    
    csv_path = os.path.join(sleep_dir, 'sleep.csv')
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['startDate', 'endDate', 'value', 'duration'])
        
        try:
            context = ET.iterparse(xml_file, events=('end',))
            
            for event, elem in context:
                if elem.tag == 'Record':
                    record_type = elem.get('type')
                    if record_type == 'HKCategoryTypeIdentifierSleepAnalysis':
                        start_date = elem.get('startDate')
                        end_date = elem.get('endDate')
                        value = elem.get('value', '0')  # 0=InBed, 1=Asleep, 2=Awake
                        
                        # Calculate duration in minutes
                        try:
                            start = datetime.strptime(start_date[:19], '%Y-%m-%d %H:%M:%S')
                            end = datetime.strptime(end_date[:19], '%Y-%m-%d %H:%M:%S')
                            duration = (end - start).total_seconds() / 60
                        except:
                            duration = 0
                        
                        writer.writerow([start_date, end_date, value, duration])
                    
                    elem.clear()
                    
        except Exception as e:
            print(f"Error parsing sleep data: {e}")
            raise e

def parse_steps_data(xml_file, output_dir='processed_data'):
    """
    Parses step count data from Apple Health export.
    Steps are stored as HKQuantityTypeIdentifierStepCount records.
    """
    steps_dir = os.path.join(output_dir, 'steps')
    if not os.path.exists(steps_dir):
        os.makedirs(steps_dir)
    
    csv_path = os.path.join(steps_dir, 'steps.csv')
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['startDate', 'endDate', 'value'])
        
        try:
            context = ET.iterparse(xml_file, events=('end',))
            
            for event, elem in context:
                if elem.tag == 'Record':
                    record_type = elem.get('type')
                    if record_type == 'HKQuantityTypeIdentifierStepCount':
                        start_date = elem.get('startDate')
                        end_date = elem.get('endDate')
                        value = elem.get('value', '0')
                        
                        writer.writerow([start_date, end_date, value])
                    
                    elem.clear()
                    
        except Exception as e:
            print(f"Error parsing steps data: {e}")
            raise e

def parse_heart_rate_data(xml_file, output_dir='processed_data'):
    """
    Parses heart rate data from Apple Health export.
    Heart rate is stored as HKQuantityTypeIdentifierHeartRate records.
    """
    hr_dir = os.path.join(output_dir, 'heart_rate')
    if not os.path.exists(hr_dir):
        os.makedirs(hr_dir)
    
    csv_path = os.path.join(hr_dir, 'heart_rate.csv')
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['startDate', 'value'])
        
        try:
            context = ET.iterparse(xml_file, events=('end',))
            
            for event, elem in context:
                if elem.tag == 'Record':
                    record_type = elem.get('type')
                    if record_type == 'HKQuantityTypeIdentifierHeartRate':
                        start_date = elem.get('startDate')
                        value = elem.get('value', '0')
                        
                        writer.writerow([start_date, value])
                    
                    elem.clear()
                    
        except Exception as e:
            print(f"Error parsing heart rate data: {e}")
            raise e

def aggregate_sleep_data(csv_path):
    """
    Aggregates sleep data by date (total sleep hours per night).
    """
    aggregated_data = defaultdict(lambda: defaultdict(lambda: {
        'total_sleep_minutes': 0.0,
        'in_bed_minutes': 0.0,
        'awake_minutes': 0.0
    }))
    
    if not os.path.exists(csv_path):
        return aggregated_data
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                start_date_str = row['startDate']
                date_obj = datetime.strptime(start_date_str[:10], '%Y-%m-%d')
                year = date_obj.year
                month = date_obj.strftime('%B')
                
                duration = float(row['duration'])
                value = row['value']
                
                # value: 0=InBed, 1=Asleep, 2=Awake
                if value == '1':  # Asleep
                    aggregated_data[year][month]['total_sleep_minutes'] += duration
                elif value == '0':  # InBed
                    aggregated_data[year][month]['in_bed_minutes'] += duration
                elif value == '2':  # Awake
                    aggregated_data[year][month]['awake_minutes'] += duration
                    
            except (ValueError, KeyError):
                continue
    
    return aggregated_data

def aggregate_steps_data(csv_path):
    """
    Aggregates step count data by year/month.
    """
    aggregated_data = defaultdict(lambda: defaultdict(lambda: {
        'total_steps': 0,
        'count': 0
    }))
    
    if not os.path.exists(csv_path):
        return aggregated_data
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                start_date_str = row['startDate']
                date_obj = datetime.strptime(start_date_str[:10], '%Y-%m-%d')
                year = date_obj.year
                month = date_obj.strftime('%B')
                
                steps = int(float(row['value']))
                aggregated_data[year][month]['total_steps'] += steps
                aggregated_data[year][month]['count'] += 1
                
            except (ValueError, KeyError):
                continue
    
    return aggregated_data

def aggregate_heart_rate_data(csv_path):
    """
    Aggregates heart rate data by year/month (average, min, max).
    """
    aggregated_data = defaultdict(lambda: defaultdict(lambda: {
        'sum': 0.0,
        'count': 0,
        'min': float('inf'),
        'max': 0.0
    }))
    
    if not os.path.exists(csv_path):
        return aggregated_data
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                start_date_str = row['startDate']
                date_obj = datetime.strptime(start_date_str[:10], '%Y-%m-%d')
                year = date_obj.year
                month = date_obj.strftime('%B')
                
                hr = float(row['value'])
                aggregated_data[year][month]['sum'] += hr
                aggregated_data[year][month]['count'] += 1
                aggregated_data[year][month]['min'] = min(aggregated_data[year][month]['min'], hr)
                aggregated_data[year][month]['max'] = max(aggregated_data[year][month]['max'], hr)
                
            except (ValueError, KeyError):
                continue
    
    return aggregated_data

def format_sleep_data(aggregated_data):
    """
    Formats sleep data for Chart.js visualization.
    """
    result = []
    sorted_years = sorted(aggregated_data.keys())
    
    for year in sorted_years:
        months_data = aggregated_data[year]
        month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        
        sorted_months = [m for m in month_order if m in months_data]
        
        sleep_hours = [months_data[m]['total_sleep_minutes'] / 60 for m in sorted_months]
        in_bed_hours = [months_data[m]['in_bed_minutes'] / 60 for m in sorted_months]
        
        result.append({
            'year': year,
            'labels': sorted_months,
            'datasets': {
                'sleep_hours': sleep_hours,
                'in_bed_hours': in_bed_hours
            }
        })
    
    return result

def format_steps_data(aggregated_data):
    """
    Formats steps data for Chart.js visualization.
    """
    result = []
    sorted_years = sorted(aggregated_data.keys())
    
    for year in sorted_years:
        months_data = aggregated_data[year]
        month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        
        sorted_months = [m for m in month_order if m in months_data]
        
        total_steps = [months_data[m]['total_steps'] for m in sorted_months]
        
        result.append({
            'year': year,
            'labels': sorted_months,
            'datasets': {
                'total_steps': total_steps
            }
        })
    
    return result

def format_heart_rate_data(aggregated_data):
    """
    Formats heart rate data for Chart.js visualization.
    """
    result = []
    sorted_years = sorted(aggregated_data.keys())
    
    for year in sorted_years:
        months_data = aggregated_data[year]
        month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        
        sorted_months = [m for m in month_order if m in months_data]
        
        avg_hr = [months_data[m]['sum'] / months_data[m]['count'] if months_data[m]['count'] > 0 else 0 
                  for m in sorted_months]
        min_hr = [months_data[m]['min'] if months_data[m]['min'] != float('inf') else 0 
                  for m in sorted_months]
        max_hr = [months_data[m]['max'] for m in sorted_months]
        
        result.append({
            'year': year,
            'labels': sorted_months,
            'datasets': {
                'avg_heart_rate': avg_hr,
                'min_heart_rate': min_hr,
                'max_heart_rate': max_hr
            }
        })
    
    return result

def aggregate_from_csv(csv_path):
    """
    Reads a workout CSV and returns aggregated data by year/month.
    """
    aggregated_data = defaultdict(lambda: defaultdict(lambda: {
        'count': 0,
        'duration': 0.0,
        'energy': 0.0,
        'distance': 0.0
    }))
    
    if not os.path.exists(csv_path):
        return aggregated_data

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                start_date_str = row['startDate']
                # Robust date parsing
                date_obj = datetime.strptime(start_date_str[:10], '%Y-%m-%d')
                year = date_obj.year
                month = date_obj.strftime('%B')
                
                aggregated_data[year][month]['count'] += 1
                aggregated_data[year][month]['duration'] += float(row['duration'])
                aggregated_data[year][month]['energy'] += float(row['totalEnergyBurned'])
                aggregated_data[year][month]['distance'] += float(row['totalDistance'])
            except (ValueError, IndexError):
                continue
                
    return aggregated_data

def format_aggregated_data(aggregated_data):
    """
    Formats aggregated data for Chart.js (same as before).
    """
    result = []
    sorted_years = sorted(aggregated_data.keys())
    
    for year in sorted_years:
        months_data = aggregated_data[year]
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December']
        
        sorted_months = [m for m in month_order if m in months_data]
        
        durations = [months_data[m]['duration'] for m in sorted_months]
        energies = [months_data[m]['energy'] for m in sorted_months]
        distances = [months_data[m]['distance'] for m in sorted_months]
        counts = [months_data[m]['count'] for m in sorted_months]
        
        result.append({
            'year': year,
            'labels': sorted_months,
            'datasets': {
                'duration': durations,
                'energy': energies,
                'distance': distances,
                'count': counts
            }
        })
        
    return result
