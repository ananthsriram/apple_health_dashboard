import lxml.etree as ET
import csv
import os
import json
from datetime import datetime
from tqdm import tqdm
from collections import defaultdict

try:
    from config import DATA_DIR
except ImportError:
    # Fallback if config.py doesn't exist
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))

EXPORT_FILE = os.path.join(DATA_DIR, 'export.xml')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed_data')

def process_data():
    """
    Parses the Apple Health export XML file using lxml.
    Extracts ALL attributes, MetadataEntry, and WorkoutStatistics.
    Uses a 2-pass approach: XML -> JSONL -> CSV to handle dynamic schemas.
    """
    if not os.path.exists(EXPORT_FILE):
        print(f"Error: {EXPORT_FILE} not found.")
        return

    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR)

    file_size = os.path.getsize(EXPORT_FILE)
    print(f"Processing {EXPORT_FILE} ({file_size / (1024*1024*1024):.2f} GB)...")
    
    # Pass 1: XML -> JSONL
    print("Pass 1: Extracting data to JSONL...")
    jsonl_files = {} # activity_type -> file_handle
    
    try:
        context = ET.iterparse(EXPORT_FILE, events=('end',), tag='Workout')
        
        with tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
            count = 0
            for event, elem in context:
                activity_type = elem.get('workoutActivityType')
                if activity_type:
                    if activity_type.startswith('HKWorkoutActivityType'):
                        activity_type = activity_type[len('HKWorkoutActivityType'):]
                    
                    activity_dir = os.path.join(PROCESSED_DIR, activity_type)
                    if not os.path.exists(activity_dir):
                        os.makedirs(activity_dir)
                    
                    jsonl_path = os.path.join(activity_dir, 'workouts.jsonl')
                    
                    if activity_type not in jsonl_files:
                        jsonl_files[activity_type] = open(jsonl_path, 'w')
                    
                    # Extract all attributes
                    record = dict(elem.attrib)
                    
                    # Extract children (Metadata, Statistics)
                    for child in elem:
                        if child.tag == 'MetadataEntry':
                            key = child.get('key')
                            val = child.get('value')
                            if key:
                                record[f"meta_{key}"] = val
                        elif child.tag == 'WorkoutStatistics':
                            stat_type = child.get('type')
                            if stat_type:
                                # Shorten stat type if possible
                                if stat_type.startswith('HKQuantityTypeIdentifier'):
                                    stat_type = stat_type[len('HKQuantityTypeIdentifier'):]
                                
                                for k, v in child.attrib.items():
                                    if k != 'type':
                                        record[f"stat_{stat_type}_{k}"] = v
                    
                    # Write to JSONL
                    jsonl_files[activity_type].write(json.dumps(record) + '\n')
                    count += 1
                    
                    if count % 1000 == 0:
                        pbar.update(0) # Keep pbar alive

                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
                    
    except Exception as e:
        print(f"\nError parsing XML: {e}")
    finally:
        for f in jsonl_files.values():
            f.close()
            
    # Pass 2: JSONL -> CSV
    print("\nPass 2: Converting JSONL to CSV (flattening schema)...")
    
    activity_dirs = [d for d in os.listdir(PROCESSED_DIR) if os.path.isdir(os.path.join(PROCESSED_DIR, d))]
    
    for activity in tqdm(activity_dirs, desc="Activities"):
        jsonl_path = os.path.join(PROCESSED_DIR, activity, 'workouts.jsonl')
        csv_path = os.path.join(PROCESSED_DIR, activity, 'workouts.csv')
        
        if not os.path.exists(jsonl_path):
            continue
            
        # Scan for all possible keys
        all_keys = set()
        with open(jsonl_path, 'r') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    all_keys.update(record.keys())
                except:
                    pass
        
        # Sort keys: standard ones first, then others alphabetically
        standard_keys = ['startDate', 'endDate', 'duration', 'totalEnergyBurned', 'totalDistance', 'sourceName']
        other_keys = sorted([k for k in all_keys if k not in standard_keys])
        final_headers = [k for k in standard_keys if k in all_keys] + other_keys
        
        # Write CSV
        with open(csv_path, 'w', newline='') as out_f:
            writer = csv.DictWriter(out_f, fieldnames=final_headers)
            writer.writeheader()
            
            with open(jsonl_path, 'r') as in_f:
                for line in in_f:
                    try:
                        record = json.loads(line)
                        writer.writerow(record)
                    except:
                        pass
        
        # Clean up JSONL
        os.remove(jsonl_path)

        # ---------------------------------------------------------
        # Step 3: Pre-aggregate data for the dashboard
        # ---------------------------------------------------------
        print(f"  Aggregating {activity}...")
        aggregated_data = defaultdict(lambda: defaultdict(lambda: {
            'count': 0,
            'duration': 0.0,
            'energy': 0.0,
            'distance': 0.0
        }))

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    start_date_str = row.get('startDate', '')
                    if not start_date_str: continue
                    
                    # Robust date parsing
                    # Expected format: YYYY-MM-DD HH:MM:SS ...
                    date_obj = datetime.strptime(start_date_str[:10], '%Y-%m-%d')
                    year = date_obj.year
                    month = date_obj.strftime('%B')
                    
                    aggregated_data[year][month]['count'] += 1
                    aggregated_data[year][month]['duration'] += float(row.get('duration', 0) or 0)
                    
                    # Energy: try stat_ActiveEnergyBurned_sum first, fallback to totalEnergyBurned
                    energy = row.get('stat_ActiveEnergyBurned_sum') or row.get('totalEnergyBurned', 0) or 0
                    aggregated_data[year][month]['energy'] += float(energy)
                    
                    # Distance: try stat_DistanceWalkingRunning_sum first, fallback to totalDistance
                    distance = row.get('stat_DistanceWalkingRunning_sum') or row.get('totalDistance', 0) or 0
                    aggregated_data[year][month]['distance'] += float(distance)
                except (ValueError, IndexError):
                    continue
        
        # Format for Chart.js immediately to save app processing time
        formatted_result = []
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

        # Save to JSON
        json_path = os.path.join(PROCESSED_DIR, activity, 'aggregated.json')
        with open(json_path, 'w') as f:
            json.dump(formatted_result, f)

    print("\nDone! Granular CSVs and Aggregated JSONs generated.")

if __name__ == '__main__':
    process_data()
