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
