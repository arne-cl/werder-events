import sys
import sqlite3
from datetime import datetime
from icalendar import Calendar
import requests
from urllib.parse import urlparse, urlunparse
import argparse
import hashlib
import re

from werder_events.utils import create_database


def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

def parse_ical(source, location_pattern=None, event_type_pattern=None):
    parsed_url = urlparse(source)
    if parsed_url.scheme:
        # It's a URL
        if parsed_url.scheme == 'webcal':
            # Convert webcal to https
            parts = list(parsed_url)
            parts[0] = 'https'
            source = urlunparse(parts)
        
        response = requests.get(source)
        response.raise_for_status()  # Raise an exception for bad status codes
        cal = Calendar.from_ical(response.content)
        source_domain = get_domain(source)
    else:
        # It's a local file
        with open(source, 'rb') as file:
            cal = Calendar.from_ical(file.read())
        source_domain = 'local_file'
    
    events = []
    for component in cal.walk():
        if component.name == "VEVENT":
            location = str(component.get('location', ''))
            
            # Apply location filter if pattern is provided
            if location_pattern and not re.search(location_pattern, location, re.IGNORECASE):
                continue

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
            
            # Apply event type filter if pattern is provided
            if event_type_pattern and not re.search(event_type_pattern, event_type, re.IGNORECASE):
                continue
            
            summary = str(component.get('summary'))
            event_hash = hashlib.md5(f"{summary}{start}".encode()).hexdigest()
            
            events.append({
                'summary': summary,
                'start': start.isoformat(),
                'end': end.isoformat(),
                'location': location,
                'description': str(component.get('description', '')),
                'type': event_type,
                'source': source_domain,
                'event_hash': event_hash
            })
    
    return events


def insert_events(conn, events):
    cursor = conn.cursor()
    inserted_count = 0
    for event in events:
        cursor.execute('''
        INSERT OR IGNORE INTO events 
        (summary, start_date, end_date, location, description, event_type, source, event_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event['summary'],
            event['start'],
            event['end'],
            event['location'],
            event['description'],
            event['type'],
            event['source'],
            event['event_hash']
        ))
        if cursor.rowcount > 0:
            inserted_count += 1
    conn.commit()
    return inserted_count

def main(input_source, output_db, location_include, event_type_include):
    try:
        # If no location filter is provided, use the Werder-specific regex
        if not location_include:
            location_include = r"\b(Werder|Bliesendorf|Resau|Derwitz|Glindow|Elisabethhöhe|Kemnitz|Kolonie Zern|Petzow|Löcknitz|Riegelberg|Phöben|Plötzin|Neu Plötzin|Plessow|Töplitz|Eichholz|Göttin|Leest|Neu Töplitz|Alt Töplitz)\b"
        
        events = parse_ical(input_source, location_include, event_type_include)
        conn = create_database(output_db)
        inserted_count = insert_events(conn, events)
        
        source_domain = get_domain(input_source) if urlparse(input_source).scheme else 'local_file'
        
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM events')
        total_events = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM events WHERE source = ?', (source_domain,))
        source_events = cursor.fetchone()[0]
        
        conn.close()
        print(f"Events from {input_source} have been successfully imported into {output_db}")
        print(f"Total events in database: {total_events}")
        print(f"Total events from this source: {source_events}")
        print(f"New events added in this run: {inserted_count}")
        print(f"Location filter applied: {location_include}")
        if event_type_include:
            print(f"Event type filter applied: {event_type_include}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching iCal data from URL: {e}")
    except IOError as e:
        print(f"Error reading local file: {e}")
    except re.error as e:
        print(f"Invalid regular expression: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert iCal to SQLite database.')
    parser.add_argument('input', help='Input iCal file or URL')
    parser.add_argument('output', help='Output SQLite database file')
    parser.add_argument('--location-include', help='Regex pattern to filter events by location')
    parser.add_argument('--event-type-include', help='Regex pattern to filter events by type (Single Day, Multi-Day, Recurring)')
    args = parser.parse_args()

    main(args.input, args.output, args.location_include, args.event_type_include)
