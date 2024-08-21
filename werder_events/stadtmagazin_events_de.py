import json
import sqlite3
from datetime import datetime, date
import hashlib
import logging
from werder_events.utils import create_database, setup_logger

def parse_events(input_file, logger):
    logger.info(f"Parsing events from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    events = []
    for result in data['results']:
        event = {}
        event['title'] = result['title']
        event['link'] = f"https://www.stadtmagazin-events.de{result['html'].split('href=\"')[1].split('"')[0]}"
        event['location'] = result['html'].split('<a href="')[1].split('">')[1].split('</a>')[0]
        
        date_time = result['html'].split('<p class="event_date">')[1].split('</p>')[0].split(' ')
        event['date'] = date_time[0]
        event['start_time'] = date_time[1]
        event['end_time'] = date_time[3] if len(date_time) > 3 else None
        
        event['description'] = result['html'].split('<p class="description">')[1].split('</p>')[0].strip()
        event['type'] = result['html'].split('<p class="cats">')[1].split('</p>')[0]
        
        # Parse date and time
        event['start'] = datetime.strptime(event['date'], "%d.%m.%Y").date()
        
        events.append(event)
    
    logger.info(f"Parsed {len(events)} events")
    return events

def insert_event(conn, event, logger):
    cursor = conn.cursor()
    event_hash = hashlib.md5(f"{event['title']}{event['start']}".encode()).hexdigest()
    
    start_date = event['start'].isoformat()
    end_date = start_date
    
    cursor.execute('''
    INSERT OR IGNORE INTO events 
    (summary, start_date, end_date, location, description, event_type, source, event_hash, is_reviewed, is_visible)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        event['title'],
        start_date,
        end_date,
        event['location'],
        event['description'],
        event['type'],
        'stadtmagazin-events.de',
        event_hash,
        False,
        False
    ))
    inserted = cursor.rowcount > 0
    conn.commit()
    logger.debug(f"Event {'inserted' if inserted else 'already exists'}: {event['title']}")
    return inserted

def main(input_file, output_db, verbose):
    logger = setup_logger("stadtmagazin-events.de scraper", verbose)
    conn = None
    try:
        logger.info("Starting event extraction and database insertion")
        events = parse_events(input_file, logger)
        
        conn = create_database(output_db, logger)
        
        inserted_count = 0
        for event in events:
            if insert_event(conn, event, logger):
                inserted_count += 1

        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM events')
        total_events = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM events WHERE source = ?', ('stadtmagazin-events.de',))
        source_events = cursor.fetchone()[0]
        
        logger.info(f"Events from {input_file} have been successfully imported into {output_db}")
        logger.info(f"Total events in database: {total_events}")
        logger.info(f"Total events from this source: {source_events}")
        logger.info(f"New events added in this run: {inserted_count}")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON file: {e}")
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        logger.debug("", exc_info=True)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Extract events from stadtmagazin-events.de and add to SQLite database.')
    parser.add_argument('input', help='Input JSON file')
    parser.add_argument('output', help='Output SQLite database file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    main(args.input, args.output, args.verbose)
