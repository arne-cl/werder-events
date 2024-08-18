import sys
import sqlite3
from datetime import datetime, date
import re
import argparse
import logging
import hashlib
from bs4 import BeautifulSoup
import requests

from werder_events.utils import create_database, setup_logger



def parse_events(input_file, logger):
    logger.info(f"Parsing events from {input_file}")
    if input_file.startswith('http'):
        logger.debug("Fetching data from URL")
        response = requests.get(input_file)
        soup = BeautifulSoup(response.text, 'html.parser')
    else:
        logger.debug("Reading data from local file")
        with open(input_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

    events = []
    event_boxes = soup.find_all('div', class_='event__wrapper')
    logger.info(f"Found {len(event_boxes)} event boxes")

    for i, box in enumerate(event_boxes, 1):
        logger.debug(f"Parsing event {i}/{len(event_boxes)}")
        event = {}
        event['link'] = box.find('a', class_='openerBild')['href']
        event['title'] = box.find('h4', class_='event__title').text.strip()
        event['location'] = box.find('div', class_='event-ort').text.strip()
        event['address'] = box.find('div', class_='event-stele').text.strip()
        
        date_time = box.find('p', class_='subhead').text.strip().split('|')
        event['date'] = date_time[0].strip()
        event['time'] = date_time[1].strip() if len(date_time) > 1 else ''

        # Parse date and time
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', event['date'])
        if date_match:
            event['start'] = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
        else:
            logger.warning(f"Could not parse date for event: {event['title']}")
            event['start'] = None

        time_match = re.search(r'(\d{2}:\d{2})', event['time'])
        if time_match:
            event['start_time'] = time_match.group(1)
        else:
            event['start_time'] = None

        event['type'] = "Single Day"
        events.append(event)

    logger.info(f"Parsed {len(events)} events")
    return events


def insert_event(conn, event, logger):
    cursor = conn.cursor()
    event_hash = hashlib.md5(f"{event['title']}{event.get('start', 'unknown_date')}".encode()).hexdigest()
    
    start_date = event['start'].isoformat() if isinstance(event.get('start'), date) else 'unknown'
    end_date = event.get('end', start_date)
    if isinstance(end_date, date):
        end_date = end_date.isoformat()
    
    cursor.execute('''
    INSERT OR IGNORE INTO events 
    (summary, start_date, end_date, location, description, event_type, source, event_hash)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        event['title'],
        start_date,
        end_date,
        event['location'],
        event.get('description', ''),
        event['type'],
        'werder-havel.de',
        event_hash
    ))
    inserted = cursor.rowcount > 0
    conn.commit()
    logger.debug(f"Event {'inserted' if inserted else 'already exists'}: {event['title']}")
    return inserted


def main(input_file, output_db, verbose):
    logger = setup_logger("werder-havel.de scraper", verbose)
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
        cursor.execute('SELECT COUNT(*) FROM events WHERE source = ?', ('werder-havel.de',))
        source_events = cursor.fetchone()[0]
        
        logger.info(f"Events from {input_file} have been successfully imported into {output_db}")
        logger.info(f"Total events in database: {total_events}")
        logger.info(f"Total events from this source: {source_events}")
        logger.info(f"New events added in this run: {inserted_count}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from URL: {e}")
    except IOError as e:
        logger.error(f"Error reading local file: {e}")
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        logger.debug("", exc_info=True)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract events from werder-havel.de and add to SQLite database.')
    parser.add_argument('input', help='Input HTML file or URL')
    parser.add_argument('output', help='Output SQLite database file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    main(args.input, args.output, args.verbose)
