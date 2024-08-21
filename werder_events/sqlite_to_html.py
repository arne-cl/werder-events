import argparse
import sqlite3
import json
import html
from datetime import datetime, date

def get_events_from_db(db_path):
    """
    Fetch all events from the given SQLite database. Exclude past events
    and events with unknown start date.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute("""
        SELECT summary, start_date, end_date, location, description, event_type, source
        FROM events
        WHERE is_visible = 1
        AND start_date != 'unknown'
        AND start_date >= ?
        ORDER BY start_date
    """, (today,))
    events = []
    for row in cursor.fetchall():
        try:
            start_date = datetime.strptime(row[1], "%Y-%m-%d").date()
            if start_date >= date.today():
                events.append({
                    "summary": row[0],
                    "start": row[1],
                    "end": row[2],
                    "location": row[3],
                    #"description": row[4], # TODO: Are event descriptions copyrighted?
                    #"type": row[5],
                    "source": row[6]
                })
        except ValueError:
            # Skip events with invalid date format
            continue
    conn.close()
    return events

def generate_html(events):
    events_json = json.dumps(events)
    page_title = "Aktuelle Termine in Werder (Havel)"
    page_url = "https://arne-cl.github.io/werder-events/"

    # Prepare preview information for the first three events
    preview_events = events[:3]
    preview_text = "\n".join([f"{html.escape(event['summary'])} - {event['start']} - {html.escape(event['location'] or '')}" for event in preview_events])

    html = f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <meta property="og:title" content="{page_title}">
    <meta property="og:description" content="Aktuelle Termine in Werder (Havel):\n{preview_text}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{page_url}">
    <style>
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        .sortable {{
            cursor: pointer;
        }}
        .sortable:hover {{
            background-color: #e6e6e6;
        }}
        .filter-input {{
            width: 100%;
            box-sizing: border-box;
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <h1>{page_title}</h1>
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
                    Source
                    <input type="text" class="filter-input" data-column="source" placeholder="Filter source...">
                </th>
            </tr>
        </thead>
        <tbody id="eventBody"></tbody>
    </table>

    <script>
        const events = {events_json};
        let filteredEvents = [...events];

        function renderEvents() {{
            const eventBody = document.getElementById('eventBody');
            eventBody.innerHTML = '';
            filteredEvents.forEach(event => {{
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${{event.summary}}</td>
                    <td>${{event.start}}</td>
                    <td>${{event.end}}</td>
                    <td>${{event.location || ''}}</td>
                    <td>${{event.source}}</td>
                `;
                eventBody.appendChild(row);
            }});
        }}

        document.getElementById('eventTable').addEventListener('click', (e) => {{
            if (e.target.classList.contains('sortable')) {{
                const sortBy = e.target.dataset.sort;
                filteredEvents.sort((a, b) => {{
                    if (a[sortBy] < b[sortBy]) return -1;
                    if (a[sortBy] > b[sortBy]) return 1;
                    return 0;
                }});
                renderEvents();
            }}
        }});

        document.querySelectorAll('.filter-input').forEach(input => {{
            input.addEventListener('input', () => {{
                const column = input.dataset.column;
                const filterValue = input.value.toLowerCase();

                filteredEvents = events.filter(event => {{
                    const value = event[column];
                    return value.toLowerCase().includes(filterValue);
                }});

                renderEvents();
            }});
        }});

        renderEvents();
    </script>
</body>
</html>
    """
    return html

def main():
    parser = argparse.ArgumentParser(description="Generate an HTML event viewer from an SQLite database.")
    parser.add_argument("db_path", help="Path to the SQLite database file")
    parser.add_argument("-o", "--output", default="event_viewer.html", help="Output HTML file name (default: event_viewer.html)")
    args = parser.parse_args()

    events = get_events_from_db(args.db_path)
    html_content = generate_html(events)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"HTML event viewer has been generated: {args.output}")

if __name__ == "__main__":
    main()
