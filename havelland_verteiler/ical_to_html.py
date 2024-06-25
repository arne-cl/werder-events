import sys
from datetime import datetime
from icalendar import Calendar
from jinja2 import Template

def parse_ical(file_path):
    with open(file_path, 'rb') as file:
        cal = Calendar.from_ical(file.read())
    
    events = []
    for component in cal.walk():
        if component.name == "VEVENT":
            start = component.get('dtstart').dt
            end = component.get('dtend').dt
            
            if isinstance(start, datetime):
                start = start.date()
            if isinstance(end, datetime):
                end = end.date()
            
            event_type = "Single Day"
            if start != end:
                event_type = "Multi-Day"
            if component.get('rrule'):
                event_type = "Recurring"
            
            events.append({
                'summary': str(component.get('summary')),
                'start': start.isoformat(),
                'end': end.isoformat(),
                'location': str(component.get('location', '')),
                'description': str(component.get('description', '')),
                'type': event_type
            })
    
    return events

def generate_html(events, output_file):
    template = Template('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>iCal Event Viewer</title>
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
        <h1>iCal Event Viewer</h1>
        <table id="eventTable">
            <thead>
                <tr>
                    <th class="sortable" data-sort="summary">
                        Summary
                        <input type="text" class="filter-input" data-column="summary" placeholder="Filter summary...">
                    </th>
                    <th class="sortable" data-sort="start">
                        Start Date
                        <input type="text" class="filter-input" data-column="start" placeholder="Filter start date...">
                    </th>
                    <th class="sortable" data-sort="end">
                        End Date
                        <input type="text" class="filter-input" data-column="end" placeholder="Filter end date...">
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
                    <td>{{ event.summary }}</td>
                    <td>{{ event.start }}</td>
                    <td>{{ event.end }}</td>
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
                        <td>${event.summary}</td>
                        <td>${event.start}</td>
                        <td>${event.end}</td>
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
                        return value.toLowerCase().includes(filterValue);
                    });

                    renderEvents();
                });
            });
        </script>
    </body>
    </html>
    ''')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(template.render(events=events))

def main(input_file, output_file):
    events = parse_ical(input_file)
    generate_html(events, output_file)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <input_ical_file> <output_html_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    main(input_file, output_file)
