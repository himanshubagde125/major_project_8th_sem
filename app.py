from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

def load_timetable_data():
    """Load timetable data from output JSON file"""
    try:
        output_file = 'classes/output1.json'
        
        with open(output_file, 'r') as file:
            data = json.load(file)
        print(f"Loaded {len(data)} entries from {output_file}")
        return data
    except Exception as e:
        print(f"Error loading timetable data: {e}")
        return []

def get_unique_professors(data):
    """Extract unique professors from the timetable data"""
    professors = set()
    for entry in data:
        professors.add(entry['Professor'])
    return sorted(list(professors))

def get_unique_classrooms(data):
    """Extract unique classrooms from the timetable data"""
    classrooms = set()
    for entry in data:
        classrooms.add(entry['AssignedClassromm'])
    return sorted(list(classrooms))

def time_index_to_day_hour(time_index):
    """Convert time index to day and hour
    
    Time index mapping:
    0 = Monday 9-11 AM
    2 = Monday 11 AM-1 PM
    4 = Monday 3-5 PM
    6 = Monday 5-7 PM
    8 = Tuesday 9-11 AM
    ...and so on
    """
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    # 8 time slots per day (4 slots of 2 hours each)
    day_index = time_index // 8
    slot_index = time_index % 8  # 0,2,4,6 represent the four 2-hour slots in a day
    
    # Convert slot index to actual time
    if slot_index == 0:
        start_hour = 9
        end_hour = 11
        time_str = "9:00-11:00 AM"
    elif slot_index == 2:
        start_hour = 11
        end_hour = 13  # 1 PM
        time_str = "11:00-1:00 PM"
    elif slot_index == 4:
        start_hour = 15  # 3 PM
        end_hour = 17    # 5 PM
        time_str = "3:00-5:00 PM"
    elif slot_index == 6:
        start_hour = 17  # 5 PM
        end_hour = 19    # 7 PM
        time_str = "5:00-7:00 PM"
    else:
        # Handle odd time indices (shouldn't happen with the input data)
        if slot_index == 1:
            time_str = "10:00-11:00 AM"
        elif slot_index == 3:
            time_str = "12:00-1:00 PM"
        elif slot_index == 5:
            time_str = "4:00-5:00 PM"
        elif slot_index == 7:
            time_str = "6:00-7:00 PM"
        else:
            time_str = f"Unknown time slot {slot_index}"
    
    # Handle day index out of range
    if day_index >= len(days):
        day_index = day_index % len(days)
        
    return days[day_index], time_str

def get_class_type_display(type_code):
    """Convert type code to display text"""
    if type_code == 'P':
        return 'Practical'
    elif type_code == 'V':
        return 'Lecture'
    elif type_code == 'L':
        return 'Lab'
    else:
        return type_code  # Return as is if unknown

@app.route('/')
def index():
    data = load_timetable_data()
    professors = get_unique_professors(data)
    classrooms = get_unique_classrooms(data)
    return render_template('index.html', professors=professors, classrooms=classrooms)

@app.route('/timetable')
def get_timetable():
    data = load_timetable_data()
    filter_type = request.args.get('filter_type', 'none')
    filter_value = request.args.get('filter_value', '')
    
    if filter_type == 'professor':
        filtered_data = [entry for entry in data if entry['Professor'].strip() == filter_value.strip()]
    elif filter_type == 'classroom':
        filtered_data = [entry for entry in data if entry['AssignedClassromm'] == filter_value]
    else:
        filtered_data = data
    
    # Print debugging info
    print(f"Original data count: {len(data)}")
    print(f"Filtered data count: {len(filtered_data)}")
    
    # First, group by time slot and subject to prioritize by type (P, V, L)
    subject_time_groups = {}
    
    # Group entries by subject and time
    for entry in filtered_data:
        time_index = int(entry['Assignedtime'])
        subject = entry['Subject']
        key = f"{subject}_{time_index}"
        
        if key not in subject_time_groups:
            subject_time_groups[key] = []
        
        subject_time_groups[key].append(entry)
    
    # For each group, sort by type priority and select only one entry
    # Type priority: P > V > L
    prioritized_data = []
    for key, entries in subject_time_groups.items():
        # Define type priority (P=Practical first, V=Lecture second, L=Lab third)
        type_priority = {'P': 0, 'V': 1, 'L': 2}
        
        # Sort entries by type priority
        sorted_entries = sorted(entries, key=lambda e: type_priority.get(e['Type'], 999))
        
        # Take only the highest priority entry for this subject and time
        prioritized_data.append(sorted_entries[0])
    
    print(f"After type prioritization: {len(prioritized_data)} entries")
    
    # Group by time slot and count subject entries to ensure fair representation
    subject_counts = {}
    for entry in prioritized_data:
        subject = entry['Subject']
        if subject not in subject_counts:
            subject_counts[subject] = 0
        subject_counts[subject] += 1
    
    # Now, handle time slot conflicts (different subjects at the same time)
    # Group by time slot
    time_slot_groups = {}
    for entry in prioritized_data:
        time_index = int(entry['Assignedtime'])
        if time_index not in time_slot_groups:
            time_slot_groups[time_index] = []
        time_slot_groups[time_index].append(entry)
    
    # For each time slot, prioritize subjects
    # Instead of alphabetical order, we'll prioritize subjects that are underrepresented
    final_prioritized_data = []
    
    for time_index, entries in time_slot_groups.items():
        if len(entries) == 1:
            # If only one subject, add it directly
            final_prioritized_data.append(entries[0])
        else:
            # Find which subjects are represented the least
            # First check for specified subjects that need representation
            priority_subjects = ['Graphics and visual computing', 'Cyber Security']
            for priority_subject in priority_subjects:
                priority_entry = next((e for e in entries if e['Subject'] == priority_subject), None)
                if priority_entry and subject_counts.get(priority_subject, 0) < 2:
                    # Add this subject and increase its count
                    final_prioritized_data.append(priority_entry)
                    subject_counts[priority_subject] = subject_counts.get(priority_subject, 0) + 1
                    print(f"Prioritizing {priority_subject} at time {time_index} (now count: {subject_counts[priority_subject]})")
                    break
            else:
                # If no priority subject found or all have enough representation,
                # choose the subject with lowest representation
                sorted_entries = sorted(entries, key=lambda e: (subject_counts.get(e['Subject'], 0), e['Subject']))
                chosen_entry = sorted_entries[0]
                final_prioritized_data.append(chosen_entry)
                subject_counts[chosen_entry['Subject']] = subject_counts.get(chosen_entry['Subject'], 0) + 1
    
    # Quick verification of subject representation
    final_subject_counts = {}
    for entry in final_prioritized_data:
        subject = entry['Subject']
        if subject not in final_subject_counts:
            final_subject_counts[subject] = 0
        final_subject_counts[subject] += 1
    
    print(f"Subject representation: {final_subject_counts}")
    print(f"After time slot conflict resolution: {len(final_prioritized_data)} entries")
    
    # Process the timetable data with day and time information
    processed_data = []
    skipped_entries = []
    
    for entry in final_prioritized_data:
        try:
            time_index = int(entry['Assignedtime'])
            length = int(entry['Length'])
            day, start_time = time_index_to_day_hour(time_index)
            
            # Calculate end time
            end_index = time_index + length - 1
            _, end_time = time_index_to_day_hour(end_index)
            
            class_type = entry['Type']
            class_type_display = get_class_type_display(class_type)
            classroom = entry['AssignedClassromm']
            
            # Generate a unique identifier for each entry
            unique_id = f"{entry['Subject']}_{class_type}_{time_index}"
            
            processed_entry = {
                'subject': entry['Subject'].lower().title(),  # Normalize titles for consistency
                'professor': entry['Professor'].strip(),
                'type': class_type,
                'type_display': class_type_display,
                'groups': ', '.join(entry['Groups']),
                'classroom': classroom,
                'length': length,
                'day': day,
                'start_time': start_time,
                'end_time': end_time,
                'time_index': time_index,
                'unique_id': unique_id
            }
            processed_data.append(processed_entry)
            
            print(f"Processed: {entry['Subject']} ({class_type}) - Day: {day}, Time: {time_index}, Room: {classroom}")
            
        except Exception as e:
            skipped_entries.append({"entry": entry, "reason": str(e)})
            print(f"Error processing entry {entry}: {e}")
    
    # Print details about missing entries
    if skipped_entries:
        print(f"Skipped {len(skipped_entries)} entries due to errors:")
        for skipped in skipped_entries:
            if "entry" in skipped and "reason" in skipped:
                entry = skipped["entry"]
                print(f"  - {entry['Subject']} ({entry['Type']}) at time {entry['Assignedtime']}: {skipped['reason']}")
    
    # Sort by day and time for better display
    processed_data.sort(key=lambda x: (x['time_index'] // 8, x['time_index'] % 8, x['type']))
    
    print(f"Processed {len(processed_data)} entries for display (after conflict resolution)")
    return jsonify(processed_data)

if __name__ == '__main__':
    app.run(debug=True) 