import requests
import sqlite3
import re
import time
import asyncio
import aiohttp
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
import logging
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import ssl
from urllib3.util.ssl_ import create_urllib3_context
from datetime import datetime
import json
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global search terms - Portuguese and English pairs
SEARCH_TERMS = [
    ("Formal Methods", "Métodos Formais"),
    ("Formal Verification", "Verificação Formal"),
    ("Model Checking", "Verificação de Modelos"),
    ("Theorem Proving", "Prova de Teoremas"),
    ("Temporal Logic", "Lógica Temporal"),
    ("Static Analysis", "Análise Estática"),
    ("Program Verification", "Verificação de Programas"),
    ("Specification Languages", "Linguagens de Especificação"),
    ("Automated Reasoning", "Raciocínio Automatizado"),
    ("Formal Semantics", "Semântica Formal"),
]

# Formal Methods concepts and tools for extraction
FORMAL_METHODS_CONCEPTS = [
    'formal specification', 'especificação formal', 'model checking', 'verificação de modelos',
    'process algebra', 'álgebra de processos', 'software verification', 'verificação de software',
    'formal verification', 'verificação formal', 'theorem proving', 'prova de teoremas',
    'temporal logic', 'lógica temporal', 'static analysis', 'análise estática',
    'formal semantics', 'semântica formal', 'automated reasoning', 'raciocínio automatizado',
    'model-based testing', 'teste baseado em modelos', 'model-oriented', 'orientado a modelos',
    'compositional analysis', 'análise composicional', 'reactive systems', 'sistemas reativos',
    'concurrent systems', 'sistemas concorrentes', 'real-time systems', 'sistemas de tempo real',
    'safety critical', 'crítico de segurança', 'refinement', 'refinamento',
    'specification languages', 'linguagens de especificação', 'formal languages', 'linguagens formais'
]

FORMAL_METHODS_TOOLS = [
    'alloy', 'spin', 'promela', 'uppaal', 'fdr', 'csp', 'tla+', 'nusmv', 'smv',
    'java pathfinder', 'jpf', 'cbmc', 'slam', 'blast', 'cpachecker', 'esbmc',
    'why3', 'dafny', 'coq', 'isabelle', 'lean', 'agda', 'pvs', 'event-b',
    'b-method', 'z notation', 'vdm', 'raise', 'rsl', 'lotos', 'estelle',
    'petri nets', 'redes de petri', 'timed automata', 'autômatos temporizados',
    'model finder', 'sat solver', 'smt solver', 'theorem prover',
    'bounded model checker', 'symbolic model checker'
]

INDUSTRY_KEYWORDS = [
    'industry', 'company', 'enterprise', 'corporation', 'cooperation', 'collaboration',
    'partnership', 'commercial', 'business', 'industrial', 'private sector',
    'indústria', 'empresa', 'corporação', 'cooperação', 'colaboração',
    'parceria', 'comercial', 'negócio', 'industrial', 'setor privado',
    'embraer', 'petrobras', 'vale', 'banco', 'microsoft', 'google', 'ibm',
    'siemens', 'bosch', 'volkswagen', 'ford', 'general motors'
]

class ProgressIndicator:
    """Enhanced progress indicator for better user feedback"""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_update = time.time()
    
    def show_progress_bar(self, current, total, prefix="Progress", bar_length=40):
        """Show a progress bar with percentage and ETA"""
        if total == 0:
            return
        
        percent = float(current) * 100 / total
        filled_length = int(bar_length * current // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # Calculate ETA
        elapsed = time.time() - self.start_time
        if current > 0:
            eta = (elapsed * total / current) - elapsed
            eta_str = f"ETA: {int(eta//60)}:{int(eta%60):02d}"
        else:
            eta_str = "ETA: --:--"
        
        # Show progress
        sys.stdout.write(f'\r{prefix}: |{bar}| {percent:.1f}% ({current}/{total}) {eta_str}')
        sys.stdout.flush()
        
        if current == total:
            print()  # New line when complete
    
    def show_spinner(self, message, count=0):
        """Show a spinning indicator for ongoing processes"""
        spinner_chars = "|/-\\"
        char = spinner_chars[count % len(spinner_chars)]
        elapsed = time.time() - self.start_time
        sys.stdout.write(f'\r{char} {message} ({int(elapsed)}s)')
        sys.stdout.flush()
    
    def print_status(self, message, emoji="ℹ️"):
        """Print a status message with timestamp"""
        elapsed = time.time() - self.start_time
        print(f"\n{emoji} [{int(elapsed//60)}:{int(elapsed%60):02d}] {message}")

class CNPqScraper:
    def __init__(self, max_workers=5):
        self.session = requests.Session()
        self.base_url = "https://buscatextual.cnpq.br/buscatextual"
        self.max_workers = max_workers
        self.db_lock = threading.Lock()  # Thread-safe database operations
        self.progress = ProgressIndicator()
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
        """Create SQLite database and tables for detailed researcher and project information"""
        self.conn = sqlite3.connect('cnpq_researchers.db')
        self.cursor = self.conn.cursor()
        
        # Main researchers table with additional fields
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
                last_update_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Projects table for detailed project information
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                researcher_id INTEGER,
                cnpq_id TEXT,
                title TEXT,
                start_date TEXT,
                end_date TEXT,
                status TEXT,
                description TEXT,
                funding_sources TEXT,
                coordinator_name TEXT,
                team_members TEXT,
                industry_cooperation TEXT,
                formal_methods_concepts TEXT,
                formal_methods_tools TEXT,
                is_formal_methods_related BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (researcher_id) REFERENCES researchers (id),
                FOREIGN KEY (cnpq_id) REFERENCES researchers (cnpq_id)
            )
        ''')
        
        # Index for better performance
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_researcher_cnpq_id 
            ON researchers (cnpq_id)
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_projects_cnpq_id 
            ON projects (cnpq_id)
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_projects_formal_methods 
            ON projects (is_formal_methods_related)
        ''')
        
        self.conn.commit()
    
    def test_connection(self):
        """Test connection to CNPq website"""
        try:
            logger.info("Testing connection to CNPq...")
            response = self.session.get("https://buscatextual.cnpq.br/", timeout=10)
            response.raise_for_status()
            logger.info("Connection test successful!")
            
            logger.info("Connection test successful!")
            
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def extract_pagination_info(self, html_content):
        """Extract pagination information from the HTML"""
        try:
            # Look for the JavaScript variables that contain pagination info
            total_match = re.search(r'var intLTotReg = (\d+);', html_content)
            current_start_match = re.search(r'var intLRegInicio = (\d+);', html_content)
            page_size_match = re.search(r'var intLRegPagina = (\d+);', html_content)
            
            if total_match and current_start_match and page_size_match:
                total_records = int(total_match.group(1))
                current_start = int(current_start_match.group(1))
                page_size = int(page_size_match.group(1))
                
                return {
                    'total_records': total_records,
                    'current_start': current_start,
                    'page_size': page_size,
                    'has_more': current_start + page_size < total_records
                }
        except Exception as e:
            logger.error(f"Error extracting pagination info: {e}")
        
        return None

    def identify_formal_methods_concepts(self, text):
        """Identify formal methods concepts in text"""
        if not text:
            return []
        
        text_lower = text.lower()
        found_concepts = []
        
        for concept in FORMAL_METHODS_CONCEPTS:
            if concept.lower() in text_lower:
                found_concepts.append(concept)
        
        return list(set(found_concepts))  # Remove duplicates
    
    def identify_formal_methods_tools(self, text):
        """Identify formal methods tools in text"""
        if not text:
            return []
        
        text_lower = text.lower()
        found_tools = []
        
        for tool in FORMAL_METHODS_TOOLS:
            if tool.lower() in text_lower:
                found_tools.append(tool)
        
        return list(set(found_tools))  # Remove duplicates
    
    def identify_industry_cooperation(self, text):
        """Identify industry cooperation mentions in text"""
        if not text:
            return []
        
        text_lower = text.lower()
        industry_mentions = []
        
        for keyword in INDUSTRY_KEYWORDS:
            if keyword.lower() in text_lower:
                # Try to extract the specific company/organization name around the keyword
                # This is a simple approach - could be improved with NLP
                sentences = re.split(r'[.!?]+', text)
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        industry_mentions.append(sentence.strip())
                        break
        
        return list(set(industry_mentions))  # Remove duplicates
    
    def is_formal_methods_related(self, title, description):
        """Check if a project is related to formal methods"""
        if not title and not description:
            return False
        
        text = f"{title or ''} {description or ''}".lower()
        
        # Check for formal methods keywords
        formal_keywords = [
            'formal', 'verificação', 'verification', 'model checking',
            'theorem proving', 'static analysis', 'temporal logic',
            'specification', 'especificação', 'métodos formais',
            'formal methods', 'prova', 'proving', 'análise estática'
        ]
        
        return any(keyword in text for keyword in formal_keywords)
    
    def parse_date_string(self, date_str):
        """Parse various date formats from Lattes"""
        if not date_str:
            return None
        
        # Remove extra whitespace and common words
        date_str = re.sub(r'\s+', ' ', date_str.strip())
        date_str = re.sub(r'(desde|from|até|to|atual|current)', '', date_str, flags=re.IGNORECASE)
        date_str = date_str.strip(' -')
        
        # Try different date formats
        date_patterns = [
            r'(\d{4})',  # Just year
            r'(\d{1,2})/(\d{4})',  # MM/YYYY
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                groups = match.groups()
                if len(groups) == 1:  # Just year
                    return groups[0]
                elif len(groups) == 2:  # MM/YYYY
                    return f"{groups[1]}-{groups[0].zfill(2)}"
                elif len(groups) == 3:  # Full date
                    if len(groups[0]) == 4:  # YYYY-MM-DD
                        return f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                    else:  # DD/MM/YYYY
                        return f"{groups[2]}-{groups[1].zfill(2)}-{groups[0].zfill(2)}"
        
        return date_str  # Return as-is if no pattern matches

    def search_researchers(self, search_term="metodos formais", max_pages=5):
        """Search for researchers based on the search term"""
        self.progress.print_status(f"🔍 Searching for: '{search_term}'", "🔍")
        
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
        total_records = None
        spinner_count = 0
        
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
                # Show progress while fetching
                self.progress.show_spinner(f"Fetching page {page + 1}/{max_pages} for '{search_term}'", spinner_count)
                spinner_count += 1
                
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                # Extract pagination info from the first page
                if page == 0:
                    pagination_info = self.extract_pagination_info(response.text)
                    if pagination_info:
                        total_records = pagination_info['total_records']
                        self.progress.print_status(f"📊 Found {total_records} total records for '{search_term}'", "📊")
                        
                        # Adjust max_pages based on actual data available
                        max_possible_pages = (total_records + 9) // 10  # Round up
                        if max_pages > max_possible_pages:
                            max_pages = max_possible_pages
                            self.progress.print_status(f"📄 Adjusted to {max_pages} pages based on available data", "📄")
                
                researchers = self.parse_search_results(response.text, search_term)
                
                # Check if we have pagination info to make better decisions
                pagination_info = self.extract_pagination_info(response.text)
                
                if not researchers:
                    # If we have pagination info, check if there should be more pages
                    if pagination_info and pagination_info['has_more']:
                        self.progress.print_status(f"⚠️ Expected more results but found none on page {page + 1}. Continuing...", "⚠️")
                        time.sleep(2)
                        continue
                    else:
                        self.progress.print_status(f"✅ Reached end of results on page {page + 1}", "✅")
                        break
                
                all_researchers.extend(researchers)
                self.progress.print_status(f"📋 Found {len(researchers)} researchers on page {page + 1} (Total: {len(all_researchers)})", "📋")
                
                # Check if we should continue based on pagination info
                if pagination_info and not pagination_info['has_more']:
                    self.progress.print_status(f"🏁 Reached last page ({page + 1}) based on pagination info", "🏁")
                    break
                
                # Be respectful to the server
                time.sleep(2)
                
            except requests.RequestException as e:
                self.progress.print_status(f"❌ Error fetching page {page + 1}: {e}", "❌")
                break
        
        if total_records:
            self.progress.print_status(f"✅ Collected {len(all_researchers)} researchers out of {total_records} total available for '{search_term}'", "✅")
        
        return all_researchers
    
    def parse_search_results(self, html_content, search_term):
        """Parse the search results HTML to extract researcher IDs and basic info"""
        soup = BeautifulSoup(html_content, 'html.parser')
        researchers = []
        
        # Look for researcher links with the correct pattern
        # Pattern: javascript:abreDetalhe('K4219769E2','Alexandre_Filgueiras',14714388,)
        researcher_links = soup.find_all('a', href=re.compile(r'javascript:abreDetalhe\('))
        
        logger.info(f"Found {len(researcher_links)} potential researcher links")
        
        # Also check for any parsing issues by looking at the HTML structure
        if len(researcher_links) == 0:
            # Debug: check if there are any results at all
            result_list = soup.find('ol')
            if result_list:
                list_items = result_list.find_all('li')
                logger.info(f"Found {len(list_items)} list items but no researcher links")
                
                # Try alternative parsing methods
                for li in list_items:
                    # Look for any links that might be researchers
                    all_links = li.find_all('a')
                    for link in all_links:
                        href = link.get('href', '')
                        if 'abreDetalhe' in href:
                            logger.info(f"Found alternative link pattern: {href}")
            else:
                logger.info("No result list found in HTML")
                # Check if there's an error message or no results message
                if 'nenhum resultado' in html_content.lower() or 'no results' in html_content.lower():
                    logger.info("Page indicates no results found")
                else:
                    logger.warning("Unexpected HTML structure - may need to update parsing logic")
        
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
        """Parse the CV page to extract detailed information including projects"""
        soup = BeautifulSoup(html_content, 'html.parser')
        details = {'projects': []}
        
        try:
            # Extract researcher name
            name_elem = soup.find('div', class_='nome') or soup.find('h1') or soup.find('div', string=re.compile(r'Nome', re.I))
            if name_elem:
                details['name'] = name_elem.get_text(strip=True)
                logger.info(f"Found researcher name: {details['name']}")
            
            # Extract last update date from Lattes
            # Look for patterns like "Última atualização em 26/02/2025" or similar
            update_patterns = [
                r'última\s+atualização.*?(\d{1,2}/\d{1,2}/\d{4})',
                r'last\s+update.*?(\d{1,2}/\d{1,2}/\d{4})',
                r'atualizado\s+em.*?(\d{1,2}/\d{1,2}/\d{4})',
                r'updated\s+on.*?(\d{1,2}/\d{1,2}/\d{4})'
            ]
            
            for pattern in update_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    details['last_update_date'] = match.group(1)
                    logger.info(f"Found last update date: {details['last_update_date']}")
                    break
            
            # Extract institution
            institution_patterns = [
                soup.find('div', class_='instituicao'),
                soup.find('div', string=re.compile(r'Instituição', re.I)),
                soup.find('td', string=re.compile(r'Instituição', re.I))
            ]
            
            for elem in institution_patterns:
                if elem:
                    if elem.name == 'td':
                        # If it's a table cell, get the next cell
                        next_td = elem.find_next_sibling('td')
                        if next_td:
                            details['institution'] = next_td.get_text(strip=True)
                    else:
                        details['institution'] = elem.get_text(strip=True)
                    break
            
            # Extract location information
            location_elem = soup.find('div', class_='endereco')
            if location_elem:
                location_text = location_elem.get_text(strip=True)
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
            
            # Extract projects information
            # Look for project sections in the CV
            project_sections = [
                'Projetos de pesquisa',
                'Projetos de desenvolvimento',
                'Research projects',
                'Development projects',
                'Projetos'
            ]
            
            for section_name in project_sections:
                section = soup.find('div', string=re.compile(section_name, re.I))
                if not section:
                    section = soup.find('td', string=re.compile(section_name, re.I))
                if not section:
                    section = soup.find('h2', string=re.compile(section_name, re.I))
                if not section:
                    section = soup.find('h3', string=re.compile(section_name, re.I))
                
                if section:
                    logger.info(f"Found project section: {section_name}")
                    projects = self.extract_projects_from_section(section)
                    details['projects'].extend(projects)
                    break
            
            # If no projects found through sections, try alternative approaches
            if not details['projects']:
                logger.info("No projects found in sections, trying alternative extraction...")
                # Look for table rows that might contain project information
                tables = soup.find_all('table')
                for table in tables:
                    projects = self.extract_projects_from_table(table)
                    if projects:
                        details['projects'].extend(projects)
                        break
            
            # Extract research area
            area_patterns = [
                soup.find('div', class_='area-atuacao'),
                soup.find('div', string=re.compile(r'Área.*atuação', re.I)),
                soup.find('td', string=re.compile(r'Área.*atuação', re.I))
            ]
            
            for elem in area_patterns:
                if elem:
                    if elem.name == 'td':
                        next_td = elem.find_next_sibling('td')
                        if next_td:
                            details['area'] = next_td.get_text(strip=True)
                    else:
                        details['area'] = elem.get_text(strip=True)
                    break
            
            logger.info(f"Extracted {len(details['projects'])} projects for researcher")
        
        except Exception as e:
            logger.error(f"Error parsing CV details: {e}")
        
        return details
    
    def extract_projects_from_section(self, section_element):
        """Extract projects from a specific section of the CV"""
        projects = []
        
        try:
            # Get the container that holds the projects
            # This could be the parent table, div, or the section itself
            container = section_element.find_parent('table')
            if not container:
                container = section_element.find_parent('div')
            if not container:
                container = section_element
            
            # Look for patterns that indicate project entries
            # Projects are usually in table rows or divs following the section
            project_rows = []
            
            # Try to find table rows with project information
            if container.name == 'table':
                project_rows = container.find_all('tr')[1:]  # Skip header row
            else:
                # Look for divs or other elements that might contain projects
                project_rows = container.find_all('div', class_=re.compile(r'projeto|project', re.I))
                if not project_rows:
                    # Try to find any child elements that might be projects
                    project_rows = container.find_all(['div', 'p', 'li'])
            
            for row in project_rows:
                project = self.parse_project_element(row)
                if project and project.get('title'):
                    projects.append(project)
        
        except Exception as e:
            logger.error(f"Error extracting projects from section: {e}")
        
        return projects
    
    def extract_projects_from_table(self, table):
        """Extract projects from a table structure"""
        projects = []
        
        try:
            rows = table.find_all('tr')
            current_project = {}
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    # Map common field labels to our project structure
                    if any(keyword in label for keyword in ['título', 'title', 'projeto']):
                        if current_project:  # Save previous project
                            if current_project.get('title'):
                                projects.append(current_project)
                        current_project = {'title': value}
                    
                    elif any(keyword in label for keyword in ['período', 'period', 'duração']):
                        current_project['period'] = value
                    
                    elif any(keyword in label for keyword in ['descrição', 'description', 'resumo']):
                        current_project['description'] = value
                    
                    elif any(keyword in label for keyword in ['financiador', 'funding', 'financiamento']):
                        current_project['funding_sources'] = value
                    
                    elif any(keyword in label for keyword in ['coordenador', 'coordinator', 'responsável']):
                        current_project['coordinator_name'] = value
                    
                    elif any(keyword in label for keyword in ['integrantes', 'members', 'equipe', 'team']):
                        current_project['team_members'] = value
            
            # Don't forget the last project
            if current_project and current_project.get('title'):
                projects.append(current_project)
        
        except Exception as e:
            logger.error(f"Error extracting projects from table: {e}")
        
        return projects
    
    def parse_project_element(self, element):
        """Parse a single project element to extract all relevant information"""
        project = {}
        
        try:
            text_content = element.get_text()
            
            # Extract title (usually the first line or in bold)
            title_elem = element.find('b') or element.find('strong')
            if title_elem:
                project['title'] = title_elem.get_text(strip=True)
            else:
                # Try to extract title from the first line
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                if lines:
                    project['title'] = lines[0]
            
            # Extract period/dates
            period_patterns = [
                r'(\d{4})\s*[-–]\s*(\d{4})',  # 2020 - 2023
                r'(\d{4})\s*[-–]\s*(atual|current)',  # 2020 - atual
                r'desde\s+(\d{4})',  # desde 2020
                r'from\s+(\d{4})',  # from 2020
                r'(\d{1,2}/\d{4})\s*[-–]\s*(\d{1,2}/\d{4})',  # MM/YYYY - MM/YYYY
            ]
            
            for pattern in period_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    if 'atual' in match.group().lower() or 'current' in match.group().lower():
                        project['start_date'] = self.parse_date_string(match.group(1))
                        project['end_date'] = 'Atual'
                        project['status'] = 'Em andamento'
                    else:
                        project['start_date'] = self.parse_date_string(match.group(1))
                        project['end_date'] = self.parse_date_string(match.group(2))
                        project['status'] = 'Concluído'
                    break
            
            # Extract description (usually the largest text block)
            # Remove title and period from the description
            description = text_content
            if project.get('title'):
                description = description.replace(project['title'], '', 1)
            
            # Remove date patterns
            for pattern in period_patterns:
                description = re.sub(pattern, '', description, flags=re.IGNORECASE)
            
            project['description'] = description.strip()
            
            # Extract specific fields using patterns
            funding_patterns = [
                r'financiador[^:]*:([^.]+)',
                r'funding[^:]*:([^.]+)',
                r'financiamento[^:]*:([^.]+)',
                r'apoio[^:]*:([^.]+)',
                r'cnpq|capes|fapesp|faperj|fapemig|finep',  # Common funding agencies
            ]
            
            for pattern in funding_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    if match.groups():
                        project['funding_sources'] = match.group(1).strip()
                    else:
                        project['funding_sources'] = match.group().strip()
                    break
            
            # Extract coordinator
            coordinator_patterns = [
                r'coordenador[^:]*:([^.]+)',
                r'coordinator[^:]*:([^.]+)',
                r'responsável[^:]*:([^.]+)',
            ]
            
            for pattern in coordinator_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    project['coordinator_name'] = match.group(1).strip()
                    break
            
            # Extract team members
            team_patterns = [
                r'integrantes[^:]*:([^.]+)',
                r'members[^:]*:([^.]+)',
                r'equipe[^:]*:([^.]+)',
                r'team[^:]*:([^.]+)',
            ]
            
            for pattern in team_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    project['team_members'] = match.group(1).strip()
                    break
            
            # Identify industry cooperation
            industry_mentions = self.identify_industry_cooperation(text_content)
            if industry_mentions:
                project['industry_cooperation'] = '; '.join(industry_mentions)
            
            # Identify formal methods concepts and tools
            concepts = self.identify_formal_methods_concepts(text_content)
            tools = self.identify_formal_methods_tools(text_content)
            
            if concepts:
                project['formal_methods_concepts'] = ', '.join(concepts)
            
            if tools:
                project['formal_methods_tools'] = ', '.join(tools)
            
            # Check if project is formal methods related
            project['is_formal_methods_related'] = self.is_formal_methods_related(
                project.get('title', ''), 
                project.get('description', '')
            )
        
        except Exception as e:
            logger.error(f"Error parsing project element: {e}")
        
        return project
    
    def process_researcher_with_details(self, researcher):
        """Process a single researcher with details (for threading)"""
        try:
            # Get detailed information
            details = self.get_researcher_details(researcher['cnpq_id'])
            researcher.update(details)
            
            # Save to database (including projects)
            self.save_researcher(researcher)
            
            project_count = len(details.get('projects', []))
            fm_projects = sum(1 for p in details.get('projects', []) if p.get('is_formal_methods_related'))
            
            return {
                'researcher': researcher,
                'project_count': project_count,
                'fm_projects': fm_projects,
                'success': True
            }
        except Exception as e:
            logger.error(f"Error processing researcher {researcher.get('name', 'Unknown')}: {e}")
            return {
                'researcher': researcher,
                'project_count': 0,
                'fm_projects': 0,
                'success': False,
                'error': str(e)
            }
    
    def save_researcher(self, researcher_data):
        """Save researcher data and projects to the database (thread-safe)"""
        with self.db_lock:  # Ensure thread-safe database operations
            try:
                # Create a new connection for thread safety
                conn = sqlite3.connect('cnpq_researchers.db')
                cursor = conn.cursor()
                
                # Check if researcher already exists
                cursor.execute('SELECT id, cnpq_id FROM researchers WHERE cnpq_id = ?', 
                                  (researcher_data.get('cnpq_id'),))
                existing = cursor.fetchone()
                
                researcher_id = None
                
                if existing:
                    researcher_id = existing[0]
                    # Update existing record with new search term if different
                    cursor.execute('''
                        UPDATE researchers 
                        SET search_term = CASE 
                            WHEN search_term LIKE '%' || ? || '%' THEN search_term
                            ELSE search_term || ', ' || ?
                        END,
                        name = COALESCE(?, name),
                        institution = COALESCE(?, institution),
                        area = COALESCE(?, area),
                        city = COALESCE(?, city),
                        state = COALESCE(?, state),
                        country = COALESCE(?, country),
                        last_update_date = COALESCE(?, last_update_date),
                        updated_at = CURRENT_TIMESTAMP
                        WHERE cnpq_id = ?
                    ''', (
                        researcher_data.get('search_term'),
                        researcher_data.get('search_term'),
                        researcher_data.get('name'),
                        researcher_data.get('institution'),
                        researcher_data.get('area'),
                        researcher_data.get('city'),
                        researcher_data.get('state'),
                        researcher_data.get('country'),
                        researcher_data.get('last_update_date'),
                        researcher_data.get('cnpq_id')
                    ))
                    logger.info(f"Updated researcher: {researcher_data.get('name')} ({researcher_data.get('cnpq_id')})")
                else:
                    # Insert new researcher
                    cursor.execute('''
                        INSERT INTO researchers 
                        (cnpq_id, name, institution, area, city, state, country, lattes_url, search_term, last_update_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        researcher_data.get('cnpq_id'),
                        researcher_data.get('name'),
                        researcher_data.get('institution'),
                        researcher_data.get('area'),
                        researcher_data.get('city'),
                        researcher_data.get('state'),
                        researcher_data.get('country'),
                        f"http://lattes.cnpq.br/{researcher_data.get('cnpq_id')}" if researcher_data.get('cnpq_id') else None,
                        researcher_data.get('search_term'),
                        researcher_data.get('last_update_date')
                    ))
                    researcher_id = cursor.lastrowid
                    logger.info(f"Saved new researcher: {researcher_data.get('name')} ({researcher_data.get('cnpq_id')})")
                
                # Save projects if they exist
                projects = researcher_data.get('projects', [])
                if projects and researcher_id:
                    # First, delete existing projects for this researcher to avoid duplicates
                    cursor.execute('DELETE FROM projects WHERE cnpq_id = ?', (researcher_data.get('cnpq_id'),))
                    
                    # Insert new projects
                    for project in projects:
                        cursor.execute('''
                            INSERT INTO projects 
                            (researcher_id, cnpq_id, title, start_date, end_date, status, description, 
                             funding_sources, coordinator_name, team_members, industry_cooperation, 
                             formal_methods_concepts, formal_methods_tools, is_formal_methods_related)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            researcher_id,
                            researcher_data.get('cnpq_id'),
                            project.get('title'),
                            project.get('start_date'),
                            project.get('end_date'),
                            project.get('status'),
                            project.get('description'),
                            project.get('funding_sources'),
                            project.get('coordinator_name'),
                            project.get('team_members'),
                            project.get('industry_cooperation'),
                            project.get('formal_methods_concepts'),
                            project.get('formal_methods_tools'),
                            project.get('is_formal_methods_related', False)
                        ))
                    
                    formal_methods_projects = sum(1 for p in projects if p.get('is_formal_methods_related'))
                    logger.info(f"Saved {len(projects)} projects for {researcher_data.get('name')} ({formal_methods_projects} formal methods related)")
                
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                logger.error(f"Database error: {e}")
                if conn:
                    conn.close()
    
    def scrape_all(self, search_terms=None, max_pages=3, get_details=True, use_threading=True):
        """Main method to scrape all researchers with enhanced progress tracking"""
        print("\n🚀 Starting CNPq Lattes Enhanced Research Aggregator")
        print("=" * 70)
        
        if search_terms is None:
            search_terms = SEARCH_TERMS
        
        self.progress.print_status(f"🎯 Will process {len(search_terms)} search term pairs", "🎯")
        self.progress.print_status(f"📄 Max {max_pages} pages per term", "📄")
        self.progress.print_status(f"🧵 Using {self.max_workers} threads" if use_threading else "🔄 Sequential processing", "🧵" if use_threading else "🔄")
        
        all_researchers = []
        
        # Phase 1: Search for researchers
        print(f"\n📍 PHASE 1: Searching for Researchers")
        print("-" * 50)
        
        term_progress = 0
        for english_term, portuguese_term in search_terms:
            term_progress += 1
            
            print(f"\n🔍 [{term_progress}/{len(search_terms)}] Processing: '{english_term}' / '{portuguese_term}'")
            
            # Try Portuguese term first, then English if no results
            for term_lang, term in [("PT", portuguese_term.lower()), ("EN", english_term.lower())]:
                self.progress.print_status(f"🌐 Trying {term_lang}: '{term}'", "🌐")
                researchers = self.search_researchers(term, max_pages)
                
                if researchers:
                    self.progress.print_status(f"✅ Found {len(researchers)} researchers for '{term}' ({term_lang})", "✅")
                    all_researchers.extend(researchers)
                    break  # Found results, no need to try the other language
                else:
                    self.progress.print_status(f"❌ No results for '{term}' ({term_lang})", "❌")
        
        # Remove duplicates
        print(f"\n🔄 Removing duplicates...")
        unique_researchers = {}
        for researcher in all_researchers:
            cnpq_id = researcher['cnpq_id']
            if cnpq_id not in unique_researchers:
                unique_researchers[cnpq_id] = researcher
            else:
                # Merge search terms
                existing_terms = unique_researchers[cnpq_id]['search_term']
                new_term = researcher['search_term']
                if new_term not in existing_terms:
                    unique_researchers[cnpq_id]['search_term'] = f"{existing_terms}, {new_term}"
        
        researchers_list = list(unique_researchers.values())
        self.progress.print_status(f"📊 Found {len(researchers_list)} unique researchers total (removed {len(all_researchers) - len(researchers_list)} duplicates)", "📊")
        
        if not get_details:
            # Just save basic info without details
            for researcher in researchers_list:
                self.save_researcher(researcher)
            self.progress.print_status("💾 Basic information saved to database", "💾")
            return researchers_list
        
        # Phase 2: Extract detailed information
        print(f"\n📍 PHASE 2: Extracting Detailed Project Information")
        print("-" * 50)
        
        completed_count = 0
        total_projects = 0
        total_fm_projects = 0
        errors = 0
        
        if use_threading and len(researchers_list) > 1:
            self.progress.print_status(f"🧵 Starting parallel processing with {self.max_workers} threads", "🧵")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_researcher = {
                    executor.submit(self.process_researcher_with_details, researcher): researcher 
                    for researcher in researchers_list
                }
                
                # Process completed tasks with progress tracking
                for future in as_completed(future_to_researcher):
                    completed_count += 1
                    result = future.result()
                    
                    if result['success']:
                        total_projects += result['project_count']
                        total_fm_projects += result['fm_projects']
                        
                        # Show progress bar
                        self.progress.show_progress_bar(
                            completed_count, 
                            len(researchers_list), 
                            "Processing researchers"
                        )
                        
                        # Show detailed info every 10 completions or at end
                        if completed_count % 10 == 0 or completed_count == len(researchers_list):
                            print(f"\n✅ Completed: {result['researcher']['name']} ({result['project_count']} projects, {result['fm_projects']} FM)")
                            print(f"📊 Running totals: {total_projects} projects, {total_fm_projects} FM projects, {errors} errors")
                    else:
                        errors += 1
                        print(f"\n❌ Failed: {result['researcher']['name']} - {result.get('error', 'Unknown error')}")
        else:
            # Sequential processing with progress
            self.progress.print_status("🔄 Processing researchers sequentially", "🔄")
            
            for i, researcher in enumerate(researchers_list, 1):
                self.progress.show_progress_bar(i, len(researchers_list), "Processing researchers")
                
                result = self.process_researcher_with_details(researcher)
                
                if result['success']:
                    total_projects += result['project_count']
                    total_fm_projects += result['fm_projects']
                    print(f"\n✅ [{i}/{len(researchers_list)}] {result['researcher']['name']} ({result['project_count']} projects, {result['fm_projects']} FM)")
                else:
                    errors += 1
                    print(f"\n❌ [{i}/{len(researchers_list)}] Failed: {result['researcher']['name']}")
                
                # Be respectful to the server
                time.sleep(2)
        
        # Final summary
        print(f"\n📍 COMPLETION SUMMARY")
        print("-" * 50)
        elapsed_total = time.time() - self.progress.start_time
        
        self.progress.print_status(f"✅ Processing completed!", "✅")
        self.progress.print_status(f"👥 Researchers: {len(researchers_list)} processed", "👥")
        self.progress.print_status(f"📋 Projects: {total_projects} extracted", "📋")
        self.progress.print_status(f"🎯 FM Projects: {total_fm_projects} identified", "🎯")
        self.progress.print_status(f"❌ Errors: {errors}", "❌" if errors > 0 else "✅")
        self.progress.print_status(f"⏱️ Total time: {int(elapsed_total//60)}:{int(elapsed_total%60):02d}", "⏱️")
        self.progress.print_status(f"💾 Data saved to 'cnpq_researchers.db'", "💾")
        
        return researchers_list
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def main():
    scraper = CNPqScraper(max_workers=8)  # Increased workers for better performance
    
    try:
        print("🔬 CNPq Lattes Enhanced Research Aggregator v2.0")
        print("   Comprehensive Formal Methods Research Intelligence")
        print("=" * 70)
        
        # Use the new comprehensive scraping approach
        researchers = scraper.scrape_all(
            search_terms=SEARCH_TERMS,  # Use all formal methods terms
            max_pages=10,  # Increased to get more comprehensive results
            get_details=True,
            use_threading=True
        )
        
        print("\n" + "=" * 70)
        print("🎉 SCRAPING COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        
        # Quick final statistics
        total_researchers = len(researchers)
        
        # Get database statistics
        conn = sqlite3.connect('cnpq_researchers.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM projects")
        total_projects = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM projects WHERE is_formal_methods_related = 1")
        fm_projects = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT institution, COUNT(*) as count 
            FROM researchers 
            WHERE institution IS NOT NULL AND institution != ""
            GROUP BY institution 
            ORDER BY count DESC 
            LIMIT 3
        """)
        top_institutions = cursor.fetchall()
        
        conn.close()
        
        print(f"📊 FINAL STATISTICS:")
        print(f"   👥 Unique researchers: {total_researchers}")
        print(f"   📋 Total projects: {total_projects}")
        print(f"   🎯 Formal methods projects: {fm_projects} ({fm_projects/total_projects*100:.1f}%)" if total_projects > 0 else "   🎯 Formal methods projects: 0")
        
        if top_institutions:
            print(f"   🏛️ Top institutions:")
            for inst, count in top_institutions:
                print(f"      • {inst}: {count} researchers")
        
        print(f"\n💡 Next steps:")
        print(f"   🔍 Run: python view_detailed_results.py")
        print(f"   📊 Explore your comprehensive formal methods research database!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ SCRAPING INTERRUPTED")
        print("Partial data may have been saved to the database.")
        logger.info("Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ ERROR OCCURRED: {e}")
        logger.error(f"Unexpected error: {e}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
