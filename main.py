import requests
import sqlite3
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
import logging
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import ssl
from urllib3.util.ssl_ import create_urllib3_context

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CNPqScraper:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://buscatextual.cnpq.br/buscatextual"
        self.setup_session()
        self.setup_database()
    
    def setup_session(self):
        """Setup session with headers and cookies"""
        # Disable SSL warnings for problematic sites
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Create a custom SSL context that's more permissive
        class CustomHTTPSAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = create_urllib3_context()
                ctx.set_ciphers('DEFAULT@SECLEVEL=1')
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                kwargs['ssl_context'] = ctx
                return super().init_poolmanager(*args, **kwargs)
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # Setup adapter with retry strategy and custom SSL
        adapter = CustomHTTPSAdapter(max_retries=retry_strategy)
        self.session.mount("http://", HTTPAdapter(max_retries=retry_strategy))
        self.session.mount("https://", adapter)
        
        # Set session timeout
        self.session.timeout = 30
        
        # Configure SSL settings
        self.session.verify = False
        
        self.session.cookies.update({
            'JSESSIONID': '9796D8BC1349A10F8BABBFA4CCAB997F.buscatextual_0',
            'fontSize': '10',
            'imp': 'cnpqrestritos',
            'idioma': 'PT',
            'BIGipServerpool_buscatextual.cnpq.br': '84541450.36895.0000',
            '__utma': '259604505.635986498.1748306865.1748306865.1748306865.1',
            '__utmc': '259604505',
            '__utmz': '259604505.1748306865.1.1.utmcsr=memoria.cnpq.br|utmccn=(referral)|utmcmd=referral|utmcct=/',
            '__utmb': '259604505.30.10.1748306865',
        })
        
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
        })
    
    def setup_database(self):
        """Create SQLite database and table"""
        self.conn = sqlite3.connect('cnpq_researchers.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS researchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpq_id TEXT UNIQUE,
                name TEXT,
                institution TEXT,
                area TEXT,
                city TEXT,
                state TEXT,
                country TEXT,
                lattes_url TEXT,
                search_term TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def test_connection(self):
        """Test connection to CNPq website"""
        try:
            logger.info("Testing connection to CNPq...")
            response = self.session.get("https://buscatextual.cnpq.br/", timeout=10)
            response.raise_for_status()
            logger.info("Connection test successful!")
            
            # Try a simple search to see if we can get any results
            logger.info("Testing simple search...")
            simple_search_url = "https://buscatextual.cnpq.br/buscatextual/busca.do"
            simple_params = {
                'metodo': 'forwardPaginaResultados',
                'registros': '0;10',
                'query': '(+idx_assunto:(computacao)+idx_particao:1)',
                'analise': 'cv',
                'tipoOrdenacao': 'null',
                'paginaOrigem': 'index.do',
                'mostrarScore': 'true',
                'mostrarBandeira': 'true',
                'modoIndAdhoc': 'null'
            }
            
            test_response = self.session.get(simple_search_url, params=simple_params)
            test_response.raise_for_status()
            
            # Save test response
            with open('test_search.html', 'w', encoding='utf-8') as f:
                f.write(test_response.text)
            logger.info("Saved test search to test_search.html")
            
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def search_researchers(self, search_term="metodos formais", max_pages=5):
        """Search for researchers based on the search term"""
        logger.info(f"Starting search for: {search_term}")
        
        # Test connection first
        if not self.test_connection():
            logger.error("Cannot connect to CNPq website. Please check your internet connection.")
            return []
        
        # Build the search query URL - use simpler format that works
        terms = search_term.split()
        if len(terms) >= 2:
            # For multiple terms, search for both
            query = f"(+idx_assunto:({terms[0]})+idx_assunto:({terms[1]})+idx_particao:1)"
        else:
            # For single term
            query = f"(+idx_assunto:({terms[0]})+idx_particao:1)"
        
        all_researchers = []
        
        for page in range(max_pages):
            start_record = page * 10
            url = f"{self.base_url}/busca.do"
            
            params = {
                'metodo': 'forwardPaginaResultados',
                'registros': f'{start_record};10',
                'query': query,
                'analise': 'cv',
                'tipoOrdenacao': 'null',
                'paginaOrigem': 'index.do',
                'mostrarScore': 'true',
                'mostrarBandeira': 'true',
                'modoIndAdhoc': 'null'
            }
            
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                # Debug: save the response to see what we're getting
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response URL: {response.url}")
                
                # Save response for debugging
                with open(f'debug_page_{page + 1}.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info(f"Saved response to debug_page_{page + 1}.html")
                
                researchers = self.parse_search_results(response.text, search_term)
                if not researchers:
                    logger.info(f"No more researchers found on page {page + 1}")
                    break
                
                all_researchers.extend(researchers)
                logger.info(f"Found {len(researchers)} researchers on page {page + 1}")
                
                # Be respectful to the server
                time.sleep(2)
                
            except requests.RequestException as e:
                logger.error(f"Error fetching page {page + 1}: {e}")
                break
        
        return all_researchers
    
    def parse_search_results(self, html_content, search_term):
        """Parse the search results HTML to extract researcher IDs and basic info"""
        soup = BeautifulSoup(html_content, 'html.parser')
        researchers = []
        
        # Look for researcher links with the correct pattern
        # Pattern: javascript:abreDetalhe('K4219769E2','Alexandre_Filgueiras',14714388,)
        researcher_links = soup.find_all('a', href=re.compile(r'javascript:abreDetalhe\('))
        
        logger.info(f"Found {len(researcher_links)} potential researcher links")
        
        for link in researcher_links:
            # Extract ID from the javascript function
            href = link.get('href')
            # Updated regex to match the actual pattern
            id_match = re.search(r'abreDetalhe\(\'([^\']+)\',\'([^\']+)\'', href)
            
            if id_match:
                cnpq_id = id_match.group(1)
                name_param = id_match.group(2)
                name = link.get_text(strip=True)
                
                logger.info(f"Found researcher: {name} (ID: {cnpq_id})")
                
                # Try to get additional info from the same list item
                li_parent = link.find_parent('li')
                institution = ""
                area = ""
                location = ""
                
                if li_parent:
                    # Extract institution and other details from the list item
                    text_content = li_parent.get_text()
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    
                    # Look for patterns like "Doutorado em..." or "MBA em..."
                    for line in lines:
                        if any(keyword in line.lower() for keyword in ['doutorado', 'mestrado', 'mba', 'graduação']):
                            if 'pela' in line.lower():
                                parts = line.split('pela')
                                if len(parts) > 1:
                                    institution = parts[1].split(',')[0].strip()
                        elif any(keyword in line.lower() for keyword in ['professor', 'trabalha', 'analista']):
                            if 'do ' in line or 'da ' in line or 'na ' in line:
                                # Extract institution from work description
                                for prep in [' do ', ' da ', ' na ']:
                                    if prep in line:
                                        institution = line.split(prep)[1].split(',')[0].strip()
                                        break
                
                researcher = {
                    'cnpq_id': cnpq_id,
                    'name': name,
                    'institution': institution,
                    'area': area,
                    'location': location,
                    'search_term': search_term
                }
                
                researchers.append(researcher)
        
        return researchers
    
    def get_researcher_details(self, cnpq_id):
        """Get detailed information from the researcher's CV page"""
        try:
            # First, get the preview page to extract the token
            preview_url = f"{self.base_url}/preview.do"
            preview_params = {
                'metodo': 'apresentar',
                'id': cnpq_id
            }
            
            preview_response = self.session.get(preview_url, params=preview_params)
            preview_response.raise_for_status()
            
            # Extract token from the preview page
            token_match = re.search(r'tokenCaptchar=([^&"\']+)', preview_response.text)
            
            if token_match:
                token = token_match.group(1)
                
                # Now get the full CV
                cv_url = f"{self.base_url}/visualizacv.do"
                cv_params = {
                    'id': cnpq_id,
                    'tokenCaptchar': token
                }
                
                cv_response = self.session.get(cv_url, params=cv_params)
                cv_response.raise_for_status()
                
                return self.parse_cv_details(cv_response.text)
            
        except requests.RequestException as e:
            logger.error(f"Error fetching details for {cnpq_id}: {e}")
        
        return {}
    
    def parse_cv_details(self, html_content):
        """Parse the CV page to extract detailed information"""
        soup = BeautifulSoup(html_content, 'html.parser')
        details = {}
        
        try:
            # Extract name
            name_elem = soup.find('div', class_='nome') or soup.find('h1')
            if name_elem:
                details['name'] = name_elem.get_text(strip=True)
            
            # Extract institution
            institution_elem = soup.find('div', class_='instituicao')
            if institution_elem:
                details['institution'] = institution_elem.get_text(strip=True)
            
            # Extract location information
            location_elem = soup.find('div', class_='endereco')
            if location_elem:
                location_text = location_elem.get_text(strip=True)
                # Try to parse city, state, country
                location_parts = location_text.split(',')
                if len(location_parts) >= 3:
                    details['city'] = location_parts[-3].strip()
                    details['state'] = location_parts[-2].strip()
                    details['country'] = location_parts[-1].strip()
                elif len(location_parts) >= 2:
                    details['state'] = location_parts[-2].strip()
                    details['country'] = location_parts[-1].strip()
                elif len(location_parts) >= 1:
                    details['country'] = location_parts[-1].strip()
            
            # Extract research area
            area_elem = soup.find('div', class_='area-atuacao') or soup.find('div', string=re.compile(r'Área.*atuação', re.I))
            if area_elem:
                details['area'] = area_elem.get_text(strip=True)
        
        except Exception as e:
            logger.error(f"Error parsing CV details: {e}")
        
        return details
    
    def save_researcher(self, researcher_data):
        """Save researcher data to the database"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO researchers 
                (cnpq_id, name, institution, area, city, state, country, lattes_url, search_term)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                researcher_data.get('cnpq_id'),
                researcher_data.get('name'),
                researcher_data.get('institution'),
                researcher_data.get('area'),
                researcher_data.get('city'),
                researcher_data.get('state'),
                researcher_data.get('country'),
                f"http://lattes.cnpq.br/{researcher_data.get('cnpq_id')}" if researcher_data.get('cnpq_id') else None,
                researcher_data.get('search_term')
            ))
            self.conn.commit()
            logger.info(f"Saved researcher: {researcher_data.get('name')} ({researcher_data.get('cnpq_id')})")
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
    
    def scrape_all(self, search_term="metodos formais", max_pages=5, get_details=True):
        """Main method to scrape all researchers"""
        logger.info("Starting CNPq scraping process...")
        
        # Search for researchers
        researchers = self.search_researchers(search_term, max_pages)
        logger.info(f"Found {len(researchers)} researchers total")
        
        # Get detailed information for each researcher
        for i, researcher in enumerate(researchers, 1):
            logger.info(f"Processing researcher {i}/{len(researchers)}: {researcher['name']}")
            
            if get_details:
                details = self.get_researcher_details(researcher['cnpq_id'])
                researcher.update(details)
                
                # Be respectful to the server
                time.sleep(3)
            
            self.save_researcher(researcher)
        
        logger.info("Scraping completed!")
        return researchers
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def main():
    scraper = CNPqScraper()
    
    try:
        # Try different search terms to see what works
        search_terms = [
            "computacao",  # This should work based on test search
            "inteligencia", 
            "metodos",
            "formal"
        ]
        
        for term in search_terms:
            print(f"\n=== Trying search term: '{term}' ===")
            researchers = scraper.search_researchers(term, max_pages=1)
            if researchers:
                print(f"Found {len(researchers)} researchers for '{term}'")
                # If we find results, use this term for full scraping
                researchers = scraper.scrape_all(
                    search_term=term,
                    max_pages=3,
                    get_details=True
                )
                break
            else:
                print(f"No results for '{term}'")
        
        if not researchers:
            print("No researchers found with any search term. Trying a basic search...")
            # Try the original approach with "metodos formais"
            researchers = scraper.scrape_all(
                search_term="metodos formais",
                max_pages=3,
                get_details=True
            )
        
        print(f"\nScraping completed! Found and saved {len(researchers)} researchers.")
        print("Data saved to 'cnpq_researchers.db' SQLite database.")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
