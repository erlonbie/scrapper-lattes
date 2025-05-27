# CNPq Lattes Web Scraper

A Python web scraper for extracting researcher information from the CNPq Lattes platform (https://buscatextual.cnpq.br/).

## Features

- Search for researchers by keywords (default: "metodos formais")
- Extract basic information from search results
- Get detailed information from individual researcher CV pages
- Save all data to a SQLite database
- Respectful scraping with delays between requests
- Comprehensive logging
- Error handling and recovery

## Installation

### Using uv (Recommended)

1. Install uv if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone or download this repository
3. Install the project and dependencies:

```bash
uv sync
```

**Note:** This project requires Python 3.9 or higher.

### Using pip (Alternative)

1. Clone or download this repository
2. Install the dependencies:

```bash
pip install requests beautifulsoup4 lxml
```

## Usage

### Basic Usage

Run the scraper with default settings:

**Using uv:**

```bash
uv run cnpq-scraper
```

**Using Python directly:**

```bash
python main.py
```

**Using project scripts (with uv):**

```bash
uv run cnpq-scraper    # Run the main scraper
uv run view-results    # View scraped data
```

This will:

- Search for "metodos formais"
- Scrape up to 3 pages of results (30 researchers)
- Get detailed information for each researcher
- Save everything to `cnpq_researchers.db`

### Customization

You can modify the scraper behavior by editing the `main()` function in `main.py`:

```python
def main():
    scraper = CNPqScraper()

    try:
        researchers = scraper.scrape_all(
            search_term="your search term",  # Change search term
            max_pages=5,                     # Number of pages to scrape
            get_details=True                 # Get detailed CV info (slower)
        )
```

### Search Terms

The scraper can handle different search terms. Examples:

- "metodos formais" (formal methods)
- "inteligencia artificial" (artificial intelligence)
- "machine learning"
- "verificacao formal" (formal verification)

## Database Schema

The scraper creates a SQLite database (`cnpq_researchers.db`) with the following structure:

```sql
CREATE TABLE researchers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpq_id TEXT UNIQUE,           -- CNPq ID (e.g., K4744277P4)
    name TEXT,                     -- Researcher name
    institution TEXT,              -- Institution/University
    area TEXT,                     -- Research area
    city TEXT,                     -- City
    state TEXT,                    -- State
    country TEXT,                  -- Country
    lattes_url TEXT,               -- Lattes CV URL
    search_term TEXT,              -- Search term used to find this researcher
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Viewing Results

### Using the built-in viewer (Recommended)

The project includes a convenient script to view and analyze the scraped data:

**Using uv:**

```bash
uv run view-results
```

**Using Python directly:**

```bash
python view_results.py
```

This provides an interactive menu to:

- View all researchers
- Display statistics
- Search researchers by name or institution
- Export data to CSV

### Using Python directly

You can also view the scraped data using any SQLite browser or Python:

```python
import sqlite3

conn = sqlite3.connect('cnpq_researchers.db')
cursor = conn.cursor()

# Get all researchers
cursor.execute("SELECT * FROM researchers")
results = cursor.fetchall()

for row in results:
    print(row)

conn.close()
```

## Rate Limiting

The scraper includes built-in delays to be respectful to the CNPq servers:

- 2 seconds between search result pages
- 3 seconds between detailed CV requests

## Error Handling

The scraper includes comprehensive error handling:

- Network timeouts and connection errors
- Invalid HTML parsing
- Database errors
- Graceful handling of missing data

## Logging

The scraper provides detailed logging information:

- Search progress
- Number of researchers found per page
- Individual researcher processing
- Errors and warnings

## Legal and Ethical Considerations

- This scraper is for educational and research purposes
- Respect the CNPq terms of service
- Use reasonable delays between requests
- Don't overload the servers
- Consider the robots.txt file

## Troubleshooting

### Common Issues

1. **No researchers found**: Check if the search term is correct and exists in the CNPq database
2. **Connection errors**: Check your internet connection and try again later
3. **Empty CV details**: Some researchers may have restricted access to their CV details

### Session Issues

If you encounter session-related errors, you may need to update the cookies in the `setup_session()` method. You can get fresh cookies by:

1. Opening the CNPq website in your browser
2. Using browser developer tools to inspect the cookies
3. Updating the cookie values in the code

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is for educational purposes. Please respect the CNPq platform's terms of service.
