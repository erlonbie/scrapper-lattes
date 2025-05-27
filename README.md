# CNPq Lattes Research Aggregator

A powerful Python web scraper for extracting and aggregating researcher information from the CNPq Lattes platform (https://buscatextual.cnpq.br/) based on customizable search terms.

## Features

- **Multi-term search**: Configurable search terms in both Portuguese and English
- **Threaded processing**: Uses multiple threads for faster data collection
- **Duplicate prevention**: Ensures no researcher is saved twice in the database
- **Comprehensive coverage**: Searches across multiple related terms in your research area
- **Smart term merging**: Tracks which search terms found each researcher
- **Extract detailed information** from individual researcher CV pages
- **SQLite database** with thread-safe operations
- **Respectful scraping** with appropriate delays between requests
- **Comprehensive logging** and error handling
- **Interactive data viewers** with statistics, search capabilities, and visual charts

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
uv run cnpq-scraper        # Run the main scraper
uv run view-results-text   # View scraped data (text interface)
uv run view-results-charts # Generate visual charts
```

This will:

- Search for configurable research terms in Portuguese and English
- Use 8 threads for faster processing
- Scrape up to 10 pages per term (100 researchers per term)
- Remove duplicates automatically
- Get detailed information for each unique researcher
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

The scraper uses configurable search terms defined in the `SEARCH_TERMS` list in `main.py`. By default, it includes research terms related to formal methods, but you can easily customize it for any research area.

**Example configuration (Portuguese & English pairs):**

```python
SEARCH_TERMS = [
    ("Your English Term", "Seu Termo em Português"),
    ("Machine Learning", "Aprendizado de Máquina"),
    ("Artificial Intelligence", "Inteligência Artificial"),
    # Add more terms as needed
]
```

**Current default terms (Formal Methods):**

- Métodos Formais / Formal Methods
- Verificação Formal / Formal Verification
- Verificação de Modelos / Model Checking
- Prova de Teoremas / Theorem Proving
- Lógica Temporal / Temporal Logic
- Análise Estática / Static Analysis
- Verificação de Programas / Program Verification
- Linguagens de Especificação / Specification Languages
- Raciocínio Automatizado / Automated Reasoning
- Semântica Formal / Formal Semantics

You can easily customize these terms for any research area by modifying the `SEARCH_TERMS` list in `main.py`.

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
uv run view-results-text   # Text-based interface
uv run view-results-charts # Generate visual charts
```

**Using Python directly:**

```bash
python view_results_text.py   # Text-based interface
python view_results_charts.py # Generate visual charts
```

**Text interface** provides an interactive menu to:

- View all researchers
- Display statistics
- Search researchers by name or institution
- Export data to CSV

**Charts interface** generates visual charts:

- Distribution by search terms
- Top institutions
- Geographic distribution
- Research trends over time

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
