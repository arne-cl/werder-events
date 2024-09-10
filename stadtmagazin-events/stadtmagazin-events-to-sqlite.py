import sys
import sqlite3
import requests
import json
from datetime import datetime
import argparse
import hashlib
import re
from bs4 import BeautifulSoup

def fetch_events(url):
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data['results']

def parse_event(event):
    soup = BeautifulSoup(event['html'], 'html.parser')
    
    date_str = soup.find('p', class_='event_date').text.strip()
    start_str, end_str = date_str.split('-')
    start_date = datetime.strptime(start_str.strip(), '%d.%m.%Y %H:%M')
    end_date = datetime.strptime(f"{start_date.date()} {end_str.strip()}", '%Y-%m-%d %H:%M')
    
    title = event['title']
    location = soup.find('a', href=re.compile(r'/locations/')).text.strip() if soup.find('a', href=re.compile(r'/locations/')) else ''
    description = soup.find('p', class_='description').text.split('/')[0].strip()
    
    event_hash = hashlib.md5(f"{title}{start_date}".encode()).hexdigest()
    
    return {
        'summary': title,
        'start': start_date.date().isoformat(),
        'end': end_date.date().isoformat(),
        'location': location,
        'description': description,
        'event_type': 'Single Day' if start_date.date() == end_date.date() else 'Multi-Day',
        'source': 'stadtmagazin-events.de',
        'event_hash': event_hash
    }

def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        summary TEXT,
        start_date TEXT,
        end_date TEXT,
        location TEXT,
        description TEXT,
        event_type TEXT,
        source TEXT,
        event_hash TEXT UNIQUE
    )
    ''')
    conn.commit()
    return conn

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
            event['event_type'],
            event['source'],
            event['event_hash']
        ))
        if cursor.rowcount > 0:
            inserted_count += 1
    conn.commit()
    return inserted_count

def main(url, output_db):
    try:        
        raw_events = fetch_events(url)
        events = [parse_event(event) for event in raw_events]
        
        conn = create_database(output_db)
        inserted_count = insert_events(conn, events)
        
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM events')
        total_events = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM events WHERE source = ?', ('stadtmagazin-events.de',))
        source_events = cursor.fetchone()[0]
        
        conn.close()
        print(f"Events from stadtmagazin-events.de have been successfully imported into {output_db}")
        print(f"Total events in database: {total_events}")
        print(f"Total events from this source: {source_events}")
        print(f"New events added in this run: {inserted_count}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from URL: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON data: {e}")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract events from stadtmagazin-events.de and store in SQLite database.')
    parser.add_argument('url', help='Input URL')
    parser.add_argument('output', help='Output SQLite database file')
    args = parser.parse_args()

    main(args.url, args.output)
