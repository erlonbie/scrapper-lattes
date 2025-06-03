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

    async def search_researchers_async(self, search_term="metodos formais", max_pages=None, max_concurrent=5):
        """Async version of search_researchers with parallel page fetching"""
        self.progress.print_status(f"🚀 Async searching for: '{search_term}' (max {max_concurrent} concurrent)", "🚀")
        
        # Build the search query URL
        terms = search_term.split()
        if len(terms) >= 2:
            query = f"(+idx_assunto:({terms[0]})+idx_assunto:({terms[1]})+idx_particao:1)"
        else:
            query = f"(+idx_assunto:({terms[0]})+idx_particao:1)"
        
        # First, get the total number of pages from page 1
        first_page_data = await self.fetch_page_async(0, query, search_term)
        if not first_page_data:
            return []
        
        researchers, pagination_info = first_page_data
        total_records = pagination_info.get('total_records', 0) if pagination_info else 0
        page_size = pagination_info.get('page_size', 10) if pagination_info else 10
        total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1
        
        self.progress.print_status(f"📊 Found {total_records} total records ({total_pages} pages) for '{search_term}'", "📊")
        
        # Apply max_pages limit if specified
        if max_pages and total_pages > max_pages:
            total_pages = max_pages
            estimated_records = max_pages * page_size
            self.progress.print_status(f"⚠️ Limiting to {max_pages} pages ({estimated_records} records) as requested", "⚠️")
        else:
            self.progress.print_status(f"🎯 Will fetch ALL {total_pages} pages ({total_records} records) in parallel", "🎯")
        
        all_researchers = researchers  # Start with page 1 results
        
        if total_pages > 1:
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(max_concurrent)
            
            # Create tasks for remaining pages
            tasks = []
            for page in range(1, total_pages):  # Skip page 0 (already fetched)
                task = self.fetch_page_with_semaphore(semaphore, page, query, search_term)
                tasks.append(task)
            
            # Execute all tasks in parallel with progress tracking
            self.progress.print_status(f"🧵 Fetching {len(tasks)} pages in parallel (max {max_concurrent} concurrent)", "🧵")
            
            completed = 0
            async for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    if result:
                        page_researchers, _ = result
                        all_researchers.extend(page_researchers)
                    
                    completed += 1
                    # Show progress every 10 completions or at key intervals
                    if completed % 10 == 0 or completed == len(tasks) or completed <= 5:
                        percentage = (completed / len(tasks)) * 100
                        self.progress.print_status(f"📄 Progress: {completed}/{len(tasks)} pages ({percentage:.1f}%) - Total researchers: {len(all_researchers)}", "📄")
                
                except Exception as e:
                    logger.error(f"Error fetching page: {e}")
                    completed += 1
        
        if total_records:
            percentage = (len(all_researchers) / total_records) * 100
            self.progress.print_status(f"✅ Collected {len(all_researchers)} researchers out of {total_records} total available ({percentage:.1f}%) for '{search_term}'", "✅")
        
        return all_researchers
    
    async def fetch_page_with_semaphore(self, semaphore, page, query, search_term):
        """Fetch a single page with semaphore limiting"""
        async with semaphore:
            return await self.fetch_page_async(page, query, search_term)
    
    async def fetch_page_async(self, page, query, search_term):
        """Fetch a single page asynchronously"""
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
            # Create SSL context similar to sync version
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create aiohttp connector with custom SSL
            connector = aiohttp.TCPConnector(
                ssl=ssl_context,
                limit=100,
                limit_per_host=20
            )
            
            # Create aiohttp session with proper headers and SSL config
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=self.session.headers,
                cookies=self.session.cookies,
                connector=connector
            ) as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    html_content = await response.text()
                    
                    # Parse results
                    researchers = self.parse_search_results(html_content, search_term)
                    pagination_info = self.extract_pagination_info(html_content)
                    
                    return researchers, pagination_info
        
        except Exception as e:
            logger.error(f"Error fetching page {page + 1}: {e}")
            return None
    
    def search_researchers(self, search_term="metodos formais", max_pages=None):
        """Enhanced search with async support - wrapper for backward compatibility"""
        # Try async version first for better performance
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, use the sync version
                return self.search_researchers_sync(search_term, max_pages)
            else:
                # Use async version for better performance
                return loop.run_until_complete(
                    self.search_researchers_async(search_term, max_pages, max_concurrent=8)
                )
        except RuntimeError:
            # Fallback to sync version if async fails
            return self.search_researchers_sync(search_term, max_pages)
    
    def search_researchers_sync(self, search_term="metodos formais", max_pages=None):
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
        total_pages = None
        spinner_count = 0
        page = 0
        
        while True:
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
                progress_msg = f"Fetching page {page + 1}"
                if total_pages:
                    progress_msg += f"/{total_pages}"
                progress_msg += f" for '{search_term}'"
                self.progress.show_spinner(progress_msg, spinner_count)
                spinner_count += 1
                
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                # Extract pagination info from the first page
                if page == 0:
                    pagination_info = self.extract_pagination_info(response.text)
                    if pagination_info:
                        total_records = pagination_info['total_records']
                        page_size = pagination_info['page_size']
                        total_pages = (total_records + page_size - 1) // page_size  # Round up
                        
                        self.progress.print_status(f"📊 Found {total_records} total records ({total_pages} pages) for '{search_term}'", "📊")
                        
                        # Apply max_pages limit only if specified by user
                        if max_pages and total_pages > max_pages:
                            total_pages = max_pages
                            estimated_records = max_pages * page_size
                            self.progress.print_status(f"⚠️ Limiting to {max_pages} pages ({estimated_records} records) as requested", "⚠️")
                        else:
                            self.progress.print_status(f"🎯 Will fetch ALL {total_pages} pages ({total_records} records)", "🎯")
                
                researchers = self.parse_search_results(response.text, search_term)
                
                # Check if we have pagination info to make better decisions
                pagination_info = self.extract_pagination_info(response.text)
                
                if not researchers:
                    # If we have pagination info, check if there should be more pages
                    if pagination_info and pagination_info['has_more']:
                        self.progress.print_status(f"⚠️ Expected more results but found none on page {page + 1}. Continuing...", "⚠️")
                        time.sleep(2)
                        page += 1
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
                
                # Check if we've reached the user-specified max_pages limit
                if max_pages and page + 1 >= max_pages:
                    self.progress.print_status(f"🛑 Reached user-specified limit of {max_pages} pages", "🛑")
                    break
                
                # Check if we've reached the total pages available
                if total_pages and page + 1 >= total_pages:
                    self.progress.print_status(f"🏁 Reached all available pages ({total_pages})", "🏁")
                    break
                
                # Be respectful to the server
                time.sleep(2)
                page += 1
                
            except requests.RequestException as e:
                self.progress.print_status(f"❌ Error fetching page {page + 1}: {e}", "❌")
                break
        
        if total_records:
            percentage = (len(all_researchers) / total_records) * 100
            self.progress.print_status(f"✅ Collected {len(all_researchers)} researchers out of {total_records} total available ({percentage:.1f}%) for '{search_term}'", "✅")
        
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
        """Get detailed information from the researcher's CV page using multiple approaches"""
        try:
            # First approach: Try the preview page which already has all the info we need
            # This bypasses the reCaptcha issue completely
            logger.info(f"Trying preview-based extraction for {cnpq_id}")
            preview_details = self.get_researcher_details_from_preview(cnpq_id)
            
            if preview_details and preview_details.get('name'):
                logger.info(f"Successfully extracted details from preview for {cnpq_id}")
                return preview_details
            
            # If preview extraction fails, fall back to the complex reCaptcha approach
            logger.info(f"Preview extraction failed, trying reCaptcha approach for {cnpq_id}")
            return self.get_researcher_details_with_captcha(cnpq_id)
            
        except Exception as e:
            logger.error(f"Error in get_researcher_details for {cnpq_id}: {e}")
            return {}
    
    def get_researcher_details_with_captcha(self, cnpq_id):
        """Original method that deals with reCaptcha - kept as fallback"""
        try:
            # First, try to access the CV directly using the simple GET method (sometimes works)
            logger.info(f"Attempting direct CV access for {cnpq_id}")
            direct_cv_url = f"{self.base_url}/visualizacv.do"
            direct_params = {
                'metodo': 'apresentar',
                'id': cnpq_id
            }
            
            try:
                direct_response = self.session.get(direct_cv_url, params=direct_params, timeout=15)
                direct_response.raise_for_status()
                
                # Check if this is a valid CV page (not a captcha page)
                if self.is_valid_cv_page(direct_response.text):
                    logger.info(f"Direct access successful for {cnpq_id}")
                    return self.parse_cv_details(direct_response.text)
                else:
                    logger.info(f"Direct access returned captcha page for {cnpq_id}")
            except Exception as e:
                logger.warning(f"Direct access failed for {cnpq_id}: {e}")
            
            # If direct access fails, try the preview + token approach
            logger.info(f"Trying preview + token approach for {cnpq_id}")
            preview_url = f"{self.base_url}/preview.do"
            preview_params = {
                'metodo': 'apresentar',
                'id': cnpq_id
            }
            
            preview_response = self.session.get(preview_url, params=preview_params, timeout=15)
            preview_response.raise_for_status()
            
            # Check if preview page is also showing captcha
            if not self.is_valid_cv_page(preview_response.text):
                logger.warning(f"Preview page also shows captcha for {cnpq_id}")
                # Save the HTML for debugging
                self.save_debug_html(preview_response.text, f"debug_preview_{cnpq_id}.html")
            
            # Try multiple token extraction patterns
            token = self.extract_token_from_html(preview_response.text)
            
            if not token:
                logger.warning(f"No token found for {cnpq_id}, attempting without token")
                token = ""
            
            # Now make the POST request to get the full CV using multipart form-data
            cv_url = f"{self.base_url}/visualizacv.do"
            
            # Prepare the multipart form data based on the curl example
            form_data = {
                'metodo': 'apresentar',
                'id': cnpq_id,
                'idiomaExibicao': '',
                'tipo': '',
                'tokenCaptchar': token,
                'nomeCaptchar': 'V2',
                'mostrarNroCitacoesScielo': '',
                'mostrarNroCitacoesScopus': '',
                'mostrarNroCitacoesISI': '',
                # Add all the filter fields with default values
                'filtros.paisAtividade': '0',
                'filtros.regiaoAtividade': '0',
                'filtros.ufAtividade': '0',
                'filtros.siglaInstAtividade': '',
                'filtros.nomeInstAtividade': '',
                'filtros.naturezaAtividade': '0',
                'filtros.atividadeAtual': 'false',
                'filtros.paisFormacao': '0',
                'filtros.regiaoFormacao': '0',
                'filtros.ufFormacao': '0',
                'filtros.siglaInstFormacao': '',
                'filtros.nomeInstFormacao': '',
                'filtros.nivelFormacao': '0',
                'filtros.grdAreaFormacao': '0',
                'filtros.areaFormacao': '0',
                'filtros.idioma': '0',
                'filtros.proeficienciaLeitura': '',
                'filtros.proeficienciaEscrita': '',
                'filtros.proeficienciaFala': '',
                'filtros.proeficienciaCompreensao': '',
                'filtros.grandeAreaAtuacao': '0',
                'filtros.areaAtuacao': '0',
                'filtros.subareaAtuacao': '0',
                'filtros.especialidadeAtuacao': '0',
                'filtros.codigoGrandeAreaAtuacao': '0',
                'filtros.codigoAreaAtuacao': '0',
                'filtros.codigoSubareaAtuacao': '0',
                'filtros.codigoEspecialidadeAtuacao': '0',
                'filtros.grandeAreaProducao': '0',
                'filtros.areaProducao': '0',
                'filtros.setorProducao': '0',
                'filtros.subSetorProducao': '0',
                'filtros.tipoRelacao': 'AND',
                'filtros.categoriaNivelBolsa': '',
                'filtros.orientadorCNPq': '',
                'filtros.conceitoCurso': '',
                'filtros.participaDGP': 'false',
                'filtros.modalidadeBolsa': '0',
                'filtros.buscaNome': 'false',
                'filtros.buscaAssunto': 'false',
                'filtros.buscaCPF': 'false',
                'filtros.buscaAtuacao': 'false',
                'filtros.tipoOrdenacao': 'SCR',
                'filtros.atualizacaoCurriculo': '48',
                'filtros.quantidadeRegistros': '25',
                'filtros.registroInicial': '1',
                'filtros.registroFinal': '25',
                'textoBuscaTodas': '',
                'textoBuscaFrase': '',
                'textoBuscaQualquer': '',
                'textoBuscaNenhuma': '',
                'textoExpressao': '',
                'particaoProcura': '',
                'buscarDoutores': 'false',
                'buscarDemais': 'false',
                'buscarDoutoresAvancada': 'false',
                'buscarDemaisAvancada': 'false',
                'textoBuscaAssunto': '',
                'tipoConector': 'AND',
                'resumoFormacao': '',
                'resumoAtividade': '',
                'resumoAtuacao': '',
                'resumoProducao': '',
                'resumoPesquisador': '',
                'resumoIdioma': '',
                'resumoPresencaDGP': '',
                'resumoModalidade': '',
                'intCPaginaAtual': '1',
                'parametrosBusca': '',
                'strCNavegador': '',
                'strCSistemaOperacional': '',
                'strCIP': '',
                'buscaAvancada': '0',
                'moduloIndicacaoAdhoc': 'false',
                'query': '',
                'modoIndAdhoc': '',
                'tipoFuncaoIndicacaoAdHoc': '',
                'buscarBrasileirosAvancada': 'false',
                'buscarEstrangeirosAvancada': 'false',
                'buscarBrasileiros': 'false',
                'buscarEstrangeiros': 'false',
                'g-recaptcha-response': token  # Use the same token for reCaptcha
            }
            
            # Set the correct content-type for multipart form-data
            cv_response = self.session.post(cv_url, data=form_data, timeout=30)
            cv_response.raise_for_status()
            
            # Check if the response is valid
            if self.is_valid_cv_page(cv_response.text):
                logger.info(f"Successfully fetched CV for {cnpq_id} using POST method")
                return self.parse_cv_details(cv_response.text)
            else:
                logger.warning(f"POST method returned captcha page for {cnpq_id}")
                # Save the HTML for debugging
                self.save_debug_html(cv_response.text, f"debug_post_{cnpq_id}.html")
                
                # Try alternative approach: use the Lattes direct URL
                return self.try_alternative_access(cnpq_id)
            
        except requests.RequestException as e:
            logger.error(f"Error fetching details for {cnpq_id}: {e}")
            return self.try_alternative_access(cnpq_id)
        
        return {}
    
    def is_valid_cv_page(self, html_content):
        """Check if the HTML content is a valid CV page (not a captcha page)"""
        # Signs that this is a captcha page
        captcha_indicators = [
            'código de segurança',
            'security code',
            'recaptcha',
            'g-recaptcha',
            'captcha',
            'verificação de segurança',
            'security verification'
        ]
        
        html_lower = html_content.lower()
        
        # If it contains captcha indicators, it's not a valid CV
        if any(indicator in html_lower for indicator in captcha_indicators):
            return False
        
        # Signs that this is a valid CV page
        cv_indicators = [
            'curriculum lattes',
            'dados pessoais',
            'personal data',
            'formação acadêmica',
            'academic background',
            'projetos de pesquisa',
            'research projects',
            'última atualização',
            'last update'
        ]
        
        # If it contains CV indicators, it's probably valid
        return any(indicator in html_lower for indicator in cv_indicators)
    
    def extract_token_from_html(self, html_content):
        """Extract token from HTML using multiple patterns"""
        token_patterns = [
            r'tokenCaptchar["\s]*[:=]["\s]*([^"&\s]+)',
            r'token["\s]*[:=]["\s]*["\']([^"\']+)["\']',
            r'name=["\']tokenCaptchar["\'][^>]*value=["\']([^"\']+)["\']',
            r'<input[^>]*name=["\']tokenCaptchar["\'][^>]*value=["\']([^"\']+)["\']',
            r'g-recaptcha-response["\'][^>]*value=["\']([^"\']+)["\']',
            # Try to find any long alphanumeric string that might be a token
            r'([A-Za-z0-9_-]{50,})',
        ]
        
        for pattern in token_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                token = match.group(1)
                if len(token) > 10:  # Only consider tokens that are long enough
                    logger.info(f"Found token using pattern: {pattern[:30]}...")
                    logger.info(f"Token preview: {token[:50]}...")
                    return token
        
        return None
    
    def save_debug_html(self, html_content, filename):
        """Save HTML content for debugging purposes"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Debug HTML saved to {filename}")
        except Exception as e:
            logger.warning(f"Failed to save debug HTML: {e}")
    
    def try_alternative_access(self, cnpq_id):
        """Try alternative methods to access the CV"""
        logger.info(f"Trying alternative access methods for {cnpq_id}")
        
        # Method 1: Try direct Lattes URL
        try:
            lattes_url = f"http://lattes.cnpq.br/{cnpq_id}"
            logger.info(f"Trying direct Lattes URL: {lattes_url}")
            
            response = self.session.get(lattes_url, timeout=15)
            response.raise_for_status()
            
            if self.is_valid_cv_page(response.text):
                logger.info(f"Direct Lattes access successful for {cnpq_id}")
                return self.parse_cv_details(response.text)
            else:
                logger.warning(f"Direct Lattes also shows captcha for {cnpq_id}")
                self.save_debug_html(response.text, f"debug_lattes_{cnpq_id}.html")
                
        except Exception as e:
            logger.error(f"Direct Lattes access failed for {cnpq_id}: {e}")
        
        # Method 2: Try different user agent
        try:
            logger.info(f"Trying with different user agent for {cnpq_id}")
            old_user_agent = self.session.headers.get('User-Agent')
            
            # Use a simpler user agent
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            cv_url = f"{self.base_url}/visualizacv.do"
            params = {
                'metodo': 'apresentar',
                'id': cnpq_id
            }
            
            response = self.session.get(cv_url, params=params, timeout=15)
            response.raise_for_status()
            
            # Restore original user agent
            if old_user_agent:
                self.session.headers.update({'User-Agent': old_user_agent})
            
            if self.is_valid_cv_page(response.text):
                logger.info(f"Alternative user agent successful for {cnpq_id}")
                return self.parse_cv_details(response.text)
                
        except Exception as e:
            logger.error(f"Alternative user agent failed for {cnpq_id}: {e}")
            # Restore original user agent
            if old_user_agent:
                self.session.headers.update({'User-Agent': old_user_agent})
        
        logger.error(f"All access methods failed for {cnpq_id}")
        return {}
    
    def parse_cv_details(self, html_content):
        """Parse the CV page to extract detailed information including projects"""
        soup = BeautifulSoup(html_content, 'html.parser')
        details = {'projects': []}
        
        try:
            # Extract researcher name - try multiple patterns
            name_patterns = [
                soup.find('div', class_='nome'),
                soup.find('h1'),
                soup.find('h2'),
                soup.find('div', string=re.compile(r'Nome', re.I)),
                soup.find('td', string=re.compile(r'Nome', re.I)),
                # Try to find name in spans or other elements
                soup.find('span', class_='nome'),
                soup.find('b', string=re.compile(r'^[A-Z][a-z]+ [A-Z]', re.I))
            ]
            
            for name_elem in name_patterns:
                if name_elem:
                    name_text = name_elem.get_text(strip=True)
                    if name_text and len(name_text) > 5 and not any(x in name_text.lower() for x in ['curriculum', 'lattes', 'cnpq']):
                        details['name'] = name_text
                        logger.info(f"Found researcher name: {details['name']}")
                        break
            
            # Extract last update date - enhanced patterns
            update_patterns = [
                r'última\s+atualização.*?(\d{1,2}/\d{1,2}/\d{4})',
                r'last\s+update.*?(\d{1,2}/\d{1,2}/\d{4})',
                r'atualizado\s+em.*?(\d{1,2}/\d{1,2}/\d{4})',
                r'updated\s+on.*?(\d{1,2}/\d{1,2}/\d{4})',
                r'atualização\s+do\s+cv\s*:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',  # Just find any date pattern
            ]
            
            for pattern in update_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    details['last_update_date'] = match.group(1)
                    logger.info(f"Found last update date: {details['last_update_date']}")
                    break
            
            # Extract institution - try multiple approaches
            institution_selectors = [
                ('div', {'class': 'instituicao'}),
                ('div', {'class': 'inst'}),
                ('span', {'class': 'instituicao'}),
                ('td', {'string': re.compile(r'Instituição', re.I)}),
                ('div', {'string': re.compile(r'Instituição', re.I)}),
            ]
            
            for tag, attrs in institution_selectors:
                if 'string' in attrs:
                    elem = soup.find(tag, string=attrs['string'])
                else:
                    elem = soup.find(tag, attrs)
                
                if elem:
                    if elem.name == 'td':
                        next_td = elem.find_next_sibling('td')
                        if next_td:
                            details['institution'] = next_td.get_text(strip=True)
                    else:
                        details['institution'] = elem.get_text(strip=True)
                    break
            
            # Enhanced project extraction - try multiple approaches
            logger.info("Starting project extraction...")
            
            # Approach 1: Look for specific project section headers
            project_section_patterns = [
                r'Projetos?\s+de\s+pesquisa',
                r'Projetos?\s+de\s+desenvolvimento',
                r'Research\s+projects?',
                r'Development\s+projects?',
                r'Projetos?',
                r'Pesquisa',
                r'Research'
            ]
            
            projects_found = False
            for pattern in project_section_patterns:
                # Find section headers
                section_headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'td', 'div', 'span'], 
                                                string=re.compile(pattern, re.I))
                
                for header in section_headers:
                    logger.info(f"Found potential project section: {header.get_text()}")
                    projects = self.extract_projects_from_section(header)
                    if projects:
                        details['projects'].extend(projects)
                        projects_found = True
                        logger.info(f"Extracted {len(projects)} projects from section: {header.get_text()}")
            
            # Approach 2: If no projects found in sections, try table-based extraction
            if not projects_found:
                logger.info("No projects found in sections, trying table extraction...")
                tables = soup.find_all('table')
                for i, table in enumerate(tables):
                    projects = self.extract_projects_from_table(table)
                    if projects:
                        details['projects'].extend(projects)
                        logger.info(f"Extracted {len(projects)} projects from table {i+1}")
            
            # Approach 3: Try to find project information in general text blocks
            if not details['projects']:
                logger.info("No projects found in tables, trying text block extraction...")
                # Look for div or p elements that might contain project information
                potential_project_blocks = soup.find_all(['div', 'p'], 
                    string=re.compile(r'(projeto|project|pesquisa|research)', re.I))
                
                for block in potential_project_blocks:
                    parent = block.find_parent(['div', 'td', 'li'])
                    if parent:
                        project = self.parse_project_element(parent)
                        if project and project.get('title'):
                            details['projects'].append(project)
            
            # Extract other fields (area, location, etc.)
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
            
            logger.info(f"Extracted {len(details['projects'])} total projects for researcher")
        
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
    
    def scrape_all(self, search_terms=None, max_pages_per_term=None, get_details=True, use_threading=True, batch_size=100):
        """Main method to scrape all researchers with enhanced performance optimizations"""
        print("\n🚀 Starting CNPq Lattes Enhanced Research Aggregator v3.0 (TURBO)")
        print("=" * 70)
        
        if search_terms is None:
            search_terms = SEARCH_TERMS
        
        self.progress.print_status(f"🎯 Will process {len(search_terms)} search term pairs", "🎯")
        
        if max_pages_per_term:
            self.progress.print_status(f"📄 Limited to max {max_pages_per_term} pages per term", "📄")
        else:
            self.progress.print_status(f"🌐 Will fetch ALL available pages per term (ASYNC PARALLEL)", "🌐")
            
        if use_threading:
            self.progress.print_status(f"🧵 Using {self.max_workers} threads with batch processing (batch size: {batch_size})", "🧵")
        else:
            self.progress.print_status(f"🔄 Sequential processing with batch saves", "🔄")
        
        all_researchers = []
        
        # Phase 1: Search for researchers (OPTIMIZED WITH ASYNC)
        print(f"\n📍 PHASE 1: Searching for Researchers (TURBO MODE)")
        print("-" * 50)
        
        term_progress = 0
        for english_term, portuguese_term in search_terms:
            term_progress += 1
            
            print(f"\n🔍 [{term_progress}/{len(search_terms)}] Processing: '{english_term}' / '{portuguese_term}'")
            
            # Try Portuguese term first, then English if no results
            for term_lang, term in [("PT", portuguese_term.lower()), ("EN", english_term.lower())]:
                self.progress.print_status(f"🌐 Trying {term_lang}: '{term}' (ASYNC)", "🌐")
                researchers = self.search_researchers(term, max_pages_per_term)
                
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
            # Just save basic info without details using batch save
            self.save_researchers_batch(researchers_list)
            self.progress.print_status("💾 Basic information saved to database (BATCH)", "💾")
            return researchers_list
        
        # Phase 2: Extract detailed information (OPTIMIZED WITH BATCHING)
        print(f"\n📍 PHASE 2: Extracting Detailed Project Information (BATCH MODE)")
        print("-" * 50)
        
        self.progress.print_status(f"🔄 Processing {len(researchers_list)} researchers in batches of {batch_size}", "🔄")
        
        # Use the optimized batch processing
        all_results = self.process_researchers_batch(researchers_list, batch_size)
        
        # Calculate final statistics
        completed_count = len(all_results)
        successful_results = [r for r in all_results if r['success']]
        total_projects = sum(r['project_count'] for r in successful_results)
        total_fm_projects = sum(r['fm_projects'] for r in successful_results)
        errors = len(all_results) - len(successful_results)
        
        # Final summary
        print(f"\n📍 COMPLETION SUMMARY (TURBO MODE)")
        print("-" * 50)
        elapsed_total = time.time() - self.progress.start_time
        
        self.progress.print_status(f"✅ Processing completed!", "✅")
        self.progress.print_status(f"👥 Researchers: {len(successful_results)}/{completed_count} processed successfully", "👥")
        self.progress.print_status(f"📋 Projects: {total_projects} extracted", "📋")
        self.progress.print_status(f"🎯 FM Projects: {total_fm_projects} identified", "🎯")
        self.progress.print_status(f"❌ Errors: {errors}", "❌" if errors > 0 else "✅")
        self.progress.print_status(f"⏱️ Total time: {int(elapsed_total//60)}:{int(elapsed_total%60):02d}", "⏱️")
        self.progress.print_status(f"🚀 Speed: {len(researchers_list)/(elapsed_total/60):.1f} researchers/minute", "🚀")
        self.progress.print_status(f"💾 Data saved to 'cnpq_researchers.db' (BATCH MODE)", "💾")
        
        return researchers_list
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def get_researcher_details_from_preview(self, cnpq_id):
        """Extract researcher details from the preview page which has all the info we need"""
        try:
            logger.info(f"Extracting details from preview page for {cnpq_id}")
            
            preview_url = f"{self.base_url}/preview.do"
            preview_params = {
                'metodo': 'apresentar',
                'id': cnpq_id
            }
            
            response = self.session.get(preview_url, params=preview_params, timeout=15)
            response.raise_for_status()
            
            return self.parse_preview_details(response.text, cnpq_id)
            
        except Exception as e:
            logger.error(f"Error fetching preview details for {cnpq_id}: {e}")
            return {}
    
    def parse_preview_details(self, html_content, cnpq_id):
        """Parse the preview page to extract researcher information"""
        soup = BeautifulSoup(html_content, 'html.parser')
        details = {'projects': []}
        
        try:
            # Extract researcher name from h1.name
            name_elem = soup.find('h1', class_='name')
            if name_elem:
                details['name'] = name_elem.get_text(strip=True)
                logger.info(f"Found researcher name: {details['name']}")
            
            # Extract last update date - look for "Certificado pelo autor em XX/XX/XXXX"
            update_patterns = [
                r'Certificado pelo autor em\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'última\s+atualização.*?(\d{1,2}/\d{1,2}/\d{4})',
                r'last\s+update.*?(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
            ]
            
            for pattern in update_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    details['last_update_date'] = match.group(1)
                    logger.info(f"Found last update date: {details['last_update_date']}")
                    break
            
            # Extract the researcher's summary/bio
            resumo_elem = soup.find('p', class_='resumo')
            if resumo_elem:
                resumo_text = resumo_elem.get_text(strip=True)
                details['summary'] = resumo_text
                
                # Extract institution from bio (usually mentions UFPE, USP, etc.)
                institution_patterns = [
                    r'(?:do|da|na)\s+(Centro de Informática.*?(?:UFPE|da UFPE))',
                    r'(?:do|da|na)\s+(Universidade[^.]*)',
                    r'(?:do|da|na)\s+(Instituto[^.]*)',
                    r'(?:do|da|na)\s+(Faculdade[^.]*)',
                    r'(UFPE|USP|UNICAMP|UFRJ|UFRGS|UFMG|UnB)',
                ]
                
                for pattern in institution_patterns:
                    match = re.search(pattern, resumo_text, re.IGNORECASE)
                    if match:
                        details['institution'] = match.group(1)
                        logger.info(f"Found institution: {details['institution']}")
                        break
                
                # Extract area from bio 
                if 'engenharia de software' in resumo_text.lower():
                    details['area'] = 'Engenharia de Software'
                elif 'ciência da computação' in resumo_text.lower():
                    details['area'] = 'Ciência da Computação'
                elif 'métodos formais' in resumo_text.lower():
                    details['area'] = 'Métodos Formais'
                elif 'inteligência artificial' in resumo_text.lower():
                    details['area'] = 'Inteligência Artificial'
                
                # Try to extract projects from the summary text
                projects = self.extract_projects_from_summary(resumo_text)
                if projects:
                    details['projects'] = projects
                    logger.info(f"Extracted {len(projects)} projects from summary")
            
            # Set some default location info (Brazil)
            details['country'] = 'Brasil'
            
            # Extract state from institution if possible
            if details.get('institution'):
                inst = details['institution'].lower()
                if 'ufpe' in inst or 'pernambuco' in inst:
                    details['state'] = 'PE'
                    details['city'] = 'Recife'
                elif 'usp' in inst or 'são paulo' in inst:
                    details['state'] = 'SP'
                    details['city'] = 'São Paulo'
                elif 'ufrj' in inst or 'rio de janeiro' in inst:
                    details['state'] = 'RJ'
                    details['city'] = 'Rio de Janeiro'
            
            logger.info(f"Successfully extracted preview details for {cnpq_id}")
            
        except Exception as e:
            logger.error(f"Error parsing preview details: {e}")
        
        return details
    
    def extract_projects_from_summary(self, summary_text):
        """Extract project information from researcher's summary using generic patterns for technology/computing"""
        projects = []
        
        try:
            # Enhanced patterns for detecting projects in technology/computing domain
            project_patterns = [
                # Direct project mentions - improved to avoid fragments
                r'(?i)(?:coordenador|coordena|lidera|participa).*?(?:do\s+|da\s+)?projeto\s+(?:de\s+)?(?:pesquisa\s+)?(?:denominado\s+)?["\']?([^"\'.,;]+(?:projeto|project|pesquisa|research|sistema|system|desenvolvimento|development)[^"\'.,;]*)["\']?',
                r'(?i)projeto\s+(?:de\s+)?(?:pesquisa\s+)?(?:denominado\s+)?["\']?([^"\'.,;]{20,150})["\']?',
                r'(?i)(?:participa|atua|desenvolve).*?projeto\s+(?:de\s+)?["\']?([^"\'.,;]{15,100})["\']?',
                
                # Cooperation patterns - more specific
                r'(?i)(?:cooperação|parceria|colaboração)\s+(?:com\s+)?(?:a\s+)?([A-Z][A-Za-z\s]{10,80}?)(?:\s+(?:para|sobre|em|no|na|do|da))',
                r'(?i)(?:em\s+)?colaboração\s+com\s+([A-Z][^.,;]{10,80}?)(?:\s+(?:para|sobre|em|trabalha|desenvolve))',
                
                # Development/implementation projects - more specific
                r'(?i)(?:desenvolvimento|implementação|criação|construção)\s+(?:de\s+|do\s+)?([^.,;]{20,100}?)(?:[.,;]|$)',
                r'(?i)(?:developing|implementation|creating|building)\s+([^.,;]{20,100}?)(?:[.,;]|$)',
                
                # Research themes/topics - more focused
                r'(?i)(?:pesquisa|research)\s+(?:em\s+|in\s+|sobre\s+|on\s+)?([^.,;]{15,80}(?:software|system|algorithm|network|data|artificial|machine|computer|computing|programming|development|technology|digital|information|cyber|security|database|web|mobile|cloud|sistemas|algoritmo|dados|inteligência|computação|tecnologia|segurança)[^.,;]{0,40})',
            ]
            
            # Technology companies and institutions (for cooperation detection)
            tech_companies = [
                'Microsoft', 'Google', 'IBM', 'Oracle', 'SAP', 'Amazon', 'Facebook', 'Meta',
                'Apple', 'Intel', 'NVIDIA', 'Samsung', 'Huawei', 'Siemens', 'Bosch',
                'Motorola', 'Nokia', 'Ericsson', 'Cisco', 'VMware', 'Adobe', 'Salesforce',
                'Embraer', 'Petrobras', 'Vale', 'Itaú', 'Bradesco', 'Banco do Brasil',
                'TIM', 'Vivo', 'Claro', 'NET', 'Porto Seguro', 'Globo', 'Record'
            ]
            
            # Funding agencies (Brazilian and international)
            funding_agencies = [
                'CNPq', 'CAPES', 'FAPESP', 'FAPERJ', 'FAPEMIG', 'FINEP', 'BNDES',
                'European Commission', 'European Union', 'Comunidade Europeia', 'FP7', 'H2020',
                'NSF', 'NIH', 'DARPA', 'NASA', 'IEEE', 'ACM'
            ]
            
            # Extract projects using patterns
            extracted_titles = set()  # Avoid duplicates
            
            for pattern in project_patterns:
                matches = re.finditer(pattern, summary_text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    project_title = match.group(1).strip()
                    
                    # Clean and validate the extracted title
                    project_title = self.clean_project_title(project_title)
                    
                    if self.is_valid_project_title(project_title) and project_title not in extracted_titles:
                        extracted_titles.add(project_title)
                        
                        # Create project object
                        project = self.create_project_from_title(project_title, summary_text)
                        projects.append(project)
            
            # Look for company cooperations
            for company in tech_companies:
                if re.search(rf'\b{re.escape(company)}\b', summary_text, re.IGNORECASE):
                    # Try to extract more context about this cooperation
                    cooperation_project = self.extract_company_cooperation(company, summary_text)
                    if cooperation_project:
                        projects.append(cooperation_project)
            
            # Look for funded projects
            for agency in funding_agencies:
                if re.search(rf'\b{re.escape(agency)}\b', summary_text, re.IGNORECASE):
                    funded_project = self.extract_funded_project(agency, summary_text)
                    if funded_project:
                        projects.append(funded_project)
            
            # Extract dates and periods for all projects
            for project in projects:
                self.extract_project_dates(project, summary_text)
            
            # Remove duplicates based on title similarity
            projects = self.deduplicate_projects(projects)
            
        except Exception as e:
            logger.error(f"Error extracting projects from summary: {e}")
        
        return projects
    
    def clean_project_title(self, title):
        """Clean and normalize project title"""
        if not title:
            return ""
        
        # Remove common prefixes/suffixes
        title = re.sub(r'^(?:do\s+|da\s+|de\s+|em\s+|no\s+|na\s+)', '', title, flags=re.IGNORECASE)
        title = re.sub(r'(?:\s+do\s+|\s+da\s+|\s+de\s+)$', '', title, flags=re.IGNORECASE)
        
        # Remove quotes and extra whitespace
        title = re.sub(r'^["\']|["\']$', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def is_valid_project_title(self, title):
        """Check if extracted title is likely a valid project title"""
        if not title or len(title) < 8 or len(title) > 200:  # Reduced minimum length
            return False
        
        # Must contain at least one technology/computing related term OR formal methods term
        tech_terms = [
            'software', 'system', 'algorithm', 'network', 'data', 'artificial', 'machine',
            'computer', 'computing', 'programming', 'development', 'technology', 'digital',
            'information', 'cyber', 'security', 'database', 'web', 'mobile', 'cloud',
            'internet', 'application', 'platform', 'framework', 'model', 'analysis',
            'optimization', 'simulation', 'visualization', 'interface', 'processing',
            'mining', 'learning', 'intelligence', 'automation', 'robotics', 'sensor',
            'embedded', 'distributed', 'parallel', 'concurrent', 'real-time', 'IoT',
            'blockchain', 'cryptocurrency', 'AR', 'VR', 'AI', 'ML', 'NLP', 'CV',
            # Portuguese terms
            'sistemas', 'algoritmo', 'redes', 'dados', 'inteligência', 'máquina',
            'computação', 'programação', 'desenvolvimento', 'tecnologia', 'digital',
            'informação', 'segurança', 'aplicação', 'plataforma', 'modelo', 'análise',
            'otimização', 'simulação', 'visualização', 'processamento', 'mineração',
            'aprendizado', 'automação', 'robótica', 'distribuído', 'paralelo', 'tempo real',
            'protocolo', 'protocolos', 'protocol', 'protocols', 'criptografia', 'cryptography',
            'malware', 'firewall', 'antivirus', 'blockchain', 'IoT', 'internet das coisas',
            'cyber', 'cibernética', 'rede', 'redes', 'wireless', 'sem fio',
            # Project-related terms
            'projeto', 'project', 'pesquisa', 'research', 'desenvolvimento', 'cooperação',
            'collaboration', 'sistema', 'protocolo', 'protocol', 'método', 'method'
        ]
        
        return any(term.lower() in title.lower() for term in tech_terms)
    
    def create_project_from_title(self, title, summary_text):
        """Create a project object from extracted title and context"""
        project = {
            'title': title,
            'description': f"Projeto identificado no resumo do pesquisador: {title}",
            'source': 'summary_generic',
            'coordinator_name': "Identificado no resumo (possivelmente o próprio pesquisador)"
        }
        
        # Analyze if it's formal methods related
        project['is_formal_methods_related'] = self.is_formal_methods_related(title, title)
        
        # Extract concepts and tools
        concepts = self.identify_formal_methods_concepts(title)
        tools = self.identify_formal_methods_tools(title)
        industry = self.identify_industry_cooperation(title)
        
        if concepts:
            project['formal_methods_concepts'] = ', '.join(concepts)
        if tools:
            project['formal_methods_tools'] = ', '.join(tools)
        if industry:
            project['industry_cooperation'] = '; '.join(industry)
        
        return project
    
    def extract_company_cooperation(self, company, summary_text):
        """Extract cooperation project with a specific company"""
        # Look for context around the company mention
        pattern = rf'([^.]*\b{re.escape(company)}\b[^.]*)'
        match = re.search(pattern, summary_text, re.IGNORECASE)
        
        if match:
            context = match.group(1).strip()
            if len(context) > 20 and any(keyword in context.lower() for keyword in 
                                       ['cooperação', 'colaboração', 'parceria', 'projeto', 'cooperation', 'collaboration']):
                return {
                    'title': f'Cooperação com {company}',
                    'description': context,
                    'industry_cooperation': company,
                    'source': 'summary_cooperation',
                    'coordinator_name': "Identificado no resumo"
                }
        return None
    
    def extract_funded_project(self, agency, summary_text):
        """Extract project funded by a specific agency"""
        # Look for context around the funding agency mention
        pattern = rf'([^.]*\b{re.escape(agency)}\b[^.]*)'
        match = re.search(pattern, summary_text, re.IGNORECASE)
        
        if match:
            context = match.group(1).strip()
            if len(context) > 20 and any(keyword in context.lower() for keyword in 
                                       ['financiado', 'apoiado', 'projeto', 'pesquisa', 'funded', 'grant']):
                return {
                    'title': f'Projeto financiado pela {agency}',
                    'description': context,
                    'funding_sources': agency,
                    'source': 'summary_funding',
                    'coordinator_name': "Identificado no resumo"
                }
        return None
    
    def extract_project_dates(self, project, summary_text):
        """Try to extract dates for a project from the summary"""
        # Look for date patterns near the project title
        title = project.get('title', '')
        
        # Find the project mention in the text
        title_pos = summary_text.lower().find(title.lower())
        if title_pos != -1:
            # Look in a window around the title for dates
            window_start = max(0, title_pos - 100)
            window_end = min(len(summary_text), title_pos + len(title) + 100)
            window = summary_text[window_start:window_end]
            
            # Date patterns
            date_patterns = [
                r'(\d{4})\s*[-–]\s*(\d{4})',  # 2020-2023
                r'(\d{4})\s*[-–]\s*(?:atual|current|presente)',  # 2020-atual
                r'(?:desde|from|starting)\s+(\d{4})',  # desde 2020
                r'(\d{1,2})/(\d{4})\s*[-–]\s*(\d{1,2})/(\d{4})',  # MM/YYYY - MM/YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, window, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        if 'atual' in match.group().lower() or 'current' in match.group().lower():
                            project['start_date'] = groups[0]
                            project['end_date'] = 'Atual'
                            project['status'] = 'Em andamento'
                        else:
                            project['start_date'] = groups[0]
                            project['end_date'] = groups[1] if len(groups) > 1 else None
                            project['status'] = 'Concluído' if project.get('end_date') and project['end_date'] != 'Atual' else 'Em andamento'
                    break
    
    def deduplicate_projects(self, projects):
        """Remove duplicate projects based on title similarity and content"""
        if not projects:
            return projects
        
        unique_projects = []
        
        for project in projects:
            title = project.get('title', '').strip()
            if not title:
                continue
                
            # Check if this project is too similar to any existing project
            is_duplicate = False
            
            for existing_project in unique_projects:
                existing_title = existing_project.get('title', '').strip()
                
                # Check for exact duplicates
                if title.lower() == existing_title.lower():
                    is_duplicate = True
                    break
                
                # Check for substantial overlap (considering one title contained in another)
                if len(title) >= 15 and len(existing_title) >= 15:
                    # If one title is completely contained in the other, it's likely a duplicate
                    if title.lower() in existing_title.lower() or existing_title.lower() in title.lower():
                        # Keep the longer, more descriptive title
                        if len(title) > len(existing_title):
                            unique_projects.remove(existing_project)
                            break  # Will add the current (longer) title
                        else:
                            is_duplicate = True
                            break
                
                # Check for high word overlap
                similarity = self.title_similarity(title, existing_title)
                if similarity > 0.7:  # 70% similarity threshold
                    # Keep the more descriptive title (longer or with more specific terms)
                    if self.is_more_descriptive(title, existing_title):
                        unique_projects.remove(existing_project)
                        break  # Will add the current (more descriptive) title
                    else:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_projects.append(project)
        
        return unique_projects
    
    def is_more_descriptive(self, title1, title2):
        """Check if title1 is more descriptive than title2"""
        # Longer titles are generally more descriptive
        if len(title1) > len(title2) + 10:  # Significantly longer
            return True
        elif len(title2) > len(title1) + 10:
            return False
        
        # Count technical terms
        tech_terms = ['software', 'system', 'algorithm', 'network', 'data', 'artificial', 
                     'machine', 'computer', 'computing', 'programming', 'development', 
                     'technology', 'digital', 'information', 'cyber', 'security', 'database',
                     'sistemas', 'algoritmo', 'dados', 'inteligência', 'computação', 'tecnologia']
        
        title1_tech_count = sum(1 for term in tech_terms if term in title1.lower())
        title2_tech_count = sum(1 for term in tech_terms if term in title2.lower())
        
        return title1_tech_count > title2_tech_count
    
    def title_similarity(self, title1, title2):
        """Calculate similarity between two titles (simple word overlap)"""
        if not title1 or not title2:
            return 0
        
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return 0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0

    def save_researchers_batch(self, researchers_data_list):
        """Save multiple researchers and their projects in a single transaction (much faster)"""
        if not researchers_data_list:
            return
        
        with self.db_lock:  # Ensure thread-safe database operations
            try:
                # Create a new connection for thread safety
                conn = sqlite3.connect('cnpq_researchers.db')
                cursor = conn.cursor()
                
                # Begin transaction
                cursor.execute('BEGIN TRANSACTION')
                
                saved_count = 0
                updated_count = 0
                projects_count = 0
                
                for researcher_data in researchers_data_list:
                    try:
                        # Check if researcher already exists
                        cursor.execute('SELECT id, cnpq_id FROM researchers WHERE cnpq_id = ?', 
                                      (researcher_data.get('cnpq_id'),))
                        existing = cursor.fetchone()
                        
                        researcher_id = None
                        
                        if existing:
                            researcher_id = existing[0]
                            # Update existing record
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
                            updated_count += 1
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
                            saved_count += 1
                        
                        # Save projects if they exist
                        projects = researcher_data.get('projects', [])
                        if projects and researcher_id:
                            # Delete existing projects for this researcher to avoid duplicates
                            cursor.execute('DELETE FROM projects WHERE cnpq_id = ?', (researcher_data.get('cnpq_id'),))
                            
                            # Prepare batch insert for projects
                            project_data = []
                            for project in projects:
                                project_data.append((
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
                            
                            # Batch insert projects
                            cursor.executemany('''
                                INSERT INTO projects 
                                (researcher_id, cnpq_id, title, start_date, end_date, status, description, 
                                 funding_sources, coordinator_name, team_members, industry_cooperation, 
                                 formal_methods_concepts, formal_methods_tools, is_formal_methods_related)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', project_data)
                            
                            projects_count += len(projects)
                    
                    except Exception as e:
                        logger.error(f"Error saving researcher {researcher_data.get('name', 'Unknown')}: {e}")
                        continue
                
                # Commit the transaction
                conn.commit()
                conn.close()
                
                logger.info(f"Batch saved: {saved_count} new researchers, {updated_count} updated, {projects_count} total projects")
                
            except sqlite3.Error as e:
                logger.error(f"Database batch error: {e}")
                if conn:
                    conn.rollback()
                    conn.close()

    def process_researchers_batch(self, researchers_list, batch_size=50):
        """Process researchers in batches for better performance"""
        if not researchers_list:
            return []
        
        all_results = []
        total_batches = (len(researchers_list) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(researchers_list), batch_size):
            batch = researchers_list[batch_idx:batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1
            
            self.progress.print_status(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} researchers)", "🔄")
            
            # Process this batch with threading
            batch_results = []
            
            if len(batch) > 1:
                # Use threading for the batch
                with ThreadPoolExecutor(max_workers=min(self.max_workers, len(batch))) as executor:
                    future_to_researcher = {
                        executor.submit(self.process_researcher_with_details, researcher): researcher 
                        for researcher in batch
                    }
                    
                    for future in as_completed(future_to_researcher):
                        result = future.result()
                        batch_results.append(result)
            else:
                # Single researcher
                result = self.process_researcher_with_details(batch[0])
                batch_results.append(result)
            
            # Collect successful researchers for batch save
            successful_researchers = [
                result['researcher'] for result in batch_results 
                if result['success'] and result['researcher']
            ]
            
            # Batch save to database
            if successful_researchers:
                self.save_researchers_batch(successful_researchers)
            
            # Collect all results
            all_results.extend(batch_results)
            
            # Show progress
            success_count = sum(1 for r in batch_results if r['success'])
            self.progress.print_status(f"✅ Batch {batch_num} completed: {success_count}/{len(batch)} successful", "✅")
            
            # Be respectful to the server between batches
            if batch_num < total_batches:
                time.sleep(1)
        
        return all_results

def main():
    scraper = CNPqScraper(max_workers=8)  # Increased workers for better performance
    
    try:
        print("🔬 CNPq Lattes Enhanced Research Aggregator v2.0")
        print("   Comprehensive Formal Methods Research Intelligence")
        print("=" * 70)
        
        # Use the new comprehensive scraping approach
        researchers = scraper.scrape_all(
            search_terms=SEARCH_TERMS,  # Use all formal methods terms
            max_pages_per_term=None,  # Fetch ALL available pages (no limit)
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
