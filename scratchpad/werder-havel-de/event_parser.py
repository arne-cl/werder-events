import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from jinja2 import Template
import re
import os

def parse_events(input_file):
    if input_file.startswith('http'):
        response = requests.get(input_file)
        soup = BeautifulSoup(response.text, 'html.parser')
    else:
        with open(input_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

    events = []
    event_boxes = soup.find_all('div', class_='event__wrapper')

    for box in event_boxes:
        event = {}
        event['link'] = box.find('a', class_='openerBild')['href']
        event['image'] = box.find('div', class_='event__image__image')['style'].split('url(')[1].split(')')[0]
        event['title'] = box.find('h4', class_='event__title').text.strip()
        event['location'] = box.find('div', class_='event-ort').text.strip()
        event['address'] = box.find('div', class_='event-stele').text.strip()
        
        date_time = box.find('p', class_='subhead').text.strip().split('|')
        event['date'] = date_time[0].strip()
        event['time'] = date_time[1].strip() if len(date_time) > 1 else ''

        events.append(event)

    return events

def get_event_details(event):
    if event['link'].startswith('http'):
        response = requests.get(event['link'])
        soup = BeautifulSoup(response.text, 'html.parser')
    else:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
        event_id = event['link'].split('eventid=')[1]
        detail_file = os.path.join(base_dir, f'eventid_{event_id}.html')
        with open(detail_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

    description = soup.find('p', class_='margin-bottom-2').text.strip()
    event['description'] = description

    info_box = soup.find('div', class_='service__sidebox')
    date_time = info_box.find_all('p')[0].text.strip().split('|')
    
    if len(date_time) > 1:
        date_str = date_time[0].strip()
        time_str = date_time[1].strip()
        
        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', date_str)
        if date_match:
            event['start'] = datetime.strptime(f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}", "%Y-%m-%d").date()
        
        time_match = re.search(r'(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})', time_str)
        if time_match:
            event['start_time'] = time_match.group(1)
            event['end_time'] = time_match.group(2)

    event['type'] = "Single Day"
    if 'start' in event and 'end' in event and event['start'] != event['end']:
        event['type'] = "Multi-Day"

    return event


import json
from datetime import date

class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def generate_html(events, output_file):
    template = Template('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Event Viewer</title>
        <style>
            table {
                border-collapse: collapse;
                width: 100%;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
            .sortable {
                cursor: pointer;
            }
            .sortable:hover {
                background-color: #e6e6e6;
            }
            .filter-input {
                width: 100%;
                box-sizing: border-box;
                margin-bottom: 5px;
            }
            .single-day {
                background-color: #e6ffe6;
            }
            .multi-day {
                background-color: #e6e6ff;
            }
            .recurring {
                background-color: #ffe6e6;
            }
        </style>
    </head>
    <body>
        <h1>Event Viewer</h1>
        <table id="eventTable">
            <thead>
                <tr>
                    <th class="sortable" data-sort="title">
                        Title
                        <input type="text" class="filter-input" data-column="title" placeholder="Filter title...">
                    </th>
                    <th class="sortable" data-sort="start">
                        Date
                        <input type="text" class="filter-input" data-column="start" placeholder="Filter date...">
                    </th>
                    <th class="sortable" data-sort="start_time">
                        Start Time
                        <input type="text" class="filter-input" data-column="start_time" placeholder="Filter start time...">
                    </th>
                    <th class="sortable" data-sort="end_time">
                        End Time
                        <input type="text" class="filter-input" data-column="end_time" placeholder="Filter end time...">
                    </th>
                    <th>
                        Location
                        <input type="text" class="filter-input" data-column="location" placeholder="Filter location...">
                    </th>
                    <th>
                        Description
                        <input type="text" class="filter-input" data-column="description" placeholder="Filter description...">
                    </th>
                    <th>
                        Type
                        <input type="text" class="filter-input" data-column="type" placeholder="Filter type...">
                    </th>
                </tr>
            </thead>
            <tbody id="eventBody">
                {% for event in events %}
                <tr class="{{ event.type.lower().replace(' ', '-') }}">
                    <td>{{ event.title }}</td>
                    <td>{{ event.start }}</td>
                    <td>{{ event.start_time }}</td>
                    <td>{{ event.end_time }}</td>
                    <td>{{ event.location }}</td>
                    <td>{{ event.description }}</td>
                    <td>{{ event.type }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <script>
            const eventTable = document.getElementById('eventTable');
            const eventBody = document.getElementById('eventBody');
            let events = {{ events|tojson }};
            let filteredEvents = [...events];

            function renderEvents() {
                eventBody.innerHTML = '';
                filteredEvents.forEach(event => {
                    const row = document.createElement('tr');
                    row.classList.add(event.type.toLowerCase().replace(' ', '-'));
                    row.innerHTML = `
                        <td>${event.title}</td>
                        <td>${event.start || ''}</td>
                        <td>${event.start_time || ''}</td>
                        <td>${event.end_time || ''}</td>
                        <td>${event.location || ''}</td>
                        <td>${event.description || ''}</td>
                        <td>${event.type}</td>
                    `;
                    eventBody.appendChild(row);
                });
            }

            eventTable.addEventListener('click', (e) => {
                if (e.target.classList.contains('sortable')) {
                    const sortBy = e.target.dataset.sort;
                    filteredEvents.sort((a, b) => {
                        if (a[sortBy] < b[sortBy]) return -1;
                        if (a[sortBy] > b[sortBy]) return 1;
                        return 0;
                    });
                    renderEvents();
                }
            });

            document.querySelectorAll('.filter-input').forEach(input => {
                input.addEventListener('input', () => {
                    const column = input.dataset.column;
                    const filterValue = input.value.toLowerCase();

                    filteredEvents = events.filter(event => {
                        const value = event[column];
                        return value && value.toString().toLowerCase().includes(filterValue);
                    });

                    renderEvents();
                });
            });
        </script>
    </body>
    </html>
    ''')
    
    # Convert date objects to strings
    for event in events:
        if isinstance(event.get('start'), date):
            event['start'] = event['start'].isoformat()
        if isinstance(event.get('end'), date):
            event['end'] = event['end'].isoformat()

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(template.render(events=events))


def main(input_file, output_file):
    events = parse_events(input_file)
    detailed_events = [get_event_details(event) for event in events]
    generate_html(detailed_events, output_file)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <input_html_file_or_url> <output_html_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    main(input_file, output_file)
