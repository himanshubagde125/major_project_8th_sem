import json
import random

def load_data(path):
    with open(path, 'r') as read_file:
        data = json.load(read_file)

    for university_class in data['Casovi']:
        classroom = university_class['Classroom']
        university_class['Classroom'] = data['Ucionice'][classroom]

    data = data['Casovi']

    return data

def generate_chromosome(data):
    professors = {}
    classrooms = {}
    groups = {}
    subjects = {}

    new_data = []

    for single_class in data:
        professors[single_class['Professor']] = [0] * 60
        for classroom in single_class['Classroom']:
            classrooms[classroom] = [0] * 60
        for group in single_class['Groups']:
            groups[group] = [0] * 60
        subjects[single_class['Subject']] = {'P' : [], 'V' : [], 'L' : []}

    for single_class in data:
        new_single_class = single_class.copy()

        classroom = random.choice(single_class['Classroom'])
        day = random.randrange(0, 5)
        if day == 4:
            period = random.randrange(0, 12 - int(single_class['Length']))
        else:
            period = random.randrange(0, 13 - int(single_class['Length']))
        new_single_class['AssignedClassromm'] = classroom
        time = 12 * day + period
        new_single_class['Assignedtime'] = time

        for i in range(time, time + int(single_class['Length'])):
            professors[new_single_class['Professor']][i] += 1
            classrooms[classroom][i] += 1
            for group in new_single_class['Groups']:
                groups[group][i] += 1
        subjects[new_single_class['Subject']][new_single_class['Type']].append((time, new_single_class['Groups']))

        new_data.append(new_single_class)

    return (new_data, professors, classrooms, groups, subjects)

def write_data(data, path):
    with open(path, 'w') as write_file:
        json.dump(data, write_file, indent=4)