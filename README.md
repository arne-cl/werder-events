# Werder Events

This project aims to aggregate and list all events happening in Werder (Havel), Germany.
It includes web scrapers for various event sources and tools to store the collected data in a SQLite database.

## Features

- Scrapes events from multiple sources:
  - werder-havel.de
  - havelland-verteiler.de
- Stores event data in a SQLite database
- Automated daily updates using GitHub Actions

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/arne-cl/werder-events.git
   cd werder-events
   ```

2. Install the package and its dependencies:
   ```
   pip install .
   ```

## Usage

### Scraping werder-havel.de

```
python werder_events/werder_havel_de.py https://www.werder-havel.de/tourismus/veranstaltungen/veranstaltungskalender.html events.sqlite -v
```

### Scraping havelland-verteiler.de

```
python werder_events/havelland_verteiler.py --event-type-include "Single Day" "webcal://havelland-verteiler.de/?post_type=tribe_events&ical=1&eventDisplay=list" events.sqlite
```

## Database Schema

The events are stored in a SQLite database with the following schema:

```sql
CREATE TABLE events (
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
```

## Automated Updates

This project uses GitHub Actions to automatically update the events database daily. The workflow is defined in `.github/workflows/update_events_database.yml`.
