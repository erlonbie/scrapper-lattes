# CNPq Lattes Enhanced Research Aggregator

A powerful Python web scraper for extracting comprehensive researcher information and **detailed project data** from the CNPq Lattes platform (https://buscatextual.cnpq.br/) with advanced analysis of **Formal Methods** research.

## ✨ Enhanced Features

### 🔍 **Comprehensive Data Extraction**

- **Researcher Information**: Name, institution, location, research areas, and last Lattes update date
- **Detailed Project Analysis**: Complete project information with formal methods focus
- **Formal Methods Intelligence**: Automatic identification of concepts and tools
- **Industry Cooperation Detection**: Smart recognition of industry partnerships
- **Multi-term search**: Configurable search terms in both Portuguese and English
- **Threaded processing**: Uses multiple threads for faster data collection
- **Duplicate prevention**: Ensures no researcher is saved twice in the database

### 📊 **Project Information Extracted**

For each researcher's project, the system extracts:

1. **📋 Basic Project Data**

   - Project title
   - Start and end dates (period)
   - Project status (ongoing/completed)
   - Project description/summary

2. **💰 Funding & Team Information**

   - Funding sources (CNPq, CAPES, FAPESP, etc.)
   - Project coordinator name
   - Team members and collaborators

3. **🏭 Industry Cooperation Analysis**

   - Automatic detection of industry partnerships
   - Company names and collaboration types
   - Commercial cooperation indicators

4. **🎯 Formal Methods Intelligence**
   - **Concepts**: Formal specification, model checking, process algebra, software verification, etc.
   - **Tools**: Alloy, SPIN, UPPAAL, FDR, Coq, Isabelle, TLA+, NuSMV, etc.
   - **Classification**: Automatic identification of formal methods-related projects

### 📈 **Enhanced Database Schema**

- **researchers table**: Extended with last update date and additional metadata
- **projects table**: Comprehensive project information with formal methods analysis
- **Advanced indexing**: Optimized for complex queries and analysis

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

Run the enhanced scraper with detailed project extraction:

**Using uv:**

```bash
uv run cnpq-scraper
```

**Using Python directly:**

```bash
python main.py
```

This will:

- Search for configurable research terms in Portuguese and English
- Extract **detailed project information** for each researcher
- Analyze **formal methods concepts and tools**
- Identify **industry cooperation**
- Get **last Lattes update dates**
- Use 8 threads for faster processing
- Save everything to `cnpq_researchers.db` with enhanced schema

### 🔬 **Enhanced Data Viewing**

Use the new detailed results viewer:

```bash
# Enhanced viewer with project analysis
python view_detailed_results.py

# Original simple viewer (still available)
uv run view-results-text
```

The enhanced viewer provides:

- **Detailed researcher profiles** with all projects
- **Formal methods project filtering**
- **Industry cooperation analysis**
- **Timeline and trend analysis**
- **Advanced search and filtering**
- **JSON export** with complete data

### Search Terms

The scraper uses configurable search terms defined in the `SEARCH_TERMS` list in `main.py`. By default, it includes comprehensive formal methods terms:

**Current default terms (Formal Methods Research):**

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

## 🗄️ Enhanced Database Schema

The enhanced scraper creates a SQLite database (`cnpq_researchers.db`) with detailed information:

### Researchers Table

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
    search_term TEXT,              -- Search terms used to find researcher
    last_update_date TEXT,         -- Last Lattes update date
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Projects Table

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    researcher_id INTEGER,         -- FK to researchers table
    cnpq_id TEXT,                 -- Researcher CNPq ID
    title TEXT,                   -- Project title
    start_date TEXT,              -- Project start date
    end_date TEXT,                -- Project end date
    status TEXT,                  -- Project status (ongoing/completed)
    description TEXT,             -- Project description
    funding_sources TEXT,         -- Funding agencies (CNPq, CAPES, etc.)
    coordinator_name TEXT,        -- Project coordinator
    team_members TEXT,            -- Team members
    industry_cooperation TEXT,    -- Industry partnerships
    formal_methods_concepts TEXT, -- Identified FM concepts
    formal_methods_tools TEXT,    -- Identified FM tools
    is_formal_methods_related BOOLEAN, -- FM classification
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 📊 Example Output

Using the example of Augusto Cezar Alves Sampaio's Lattes (http://lattes.cnpq.br/3977760354511853):

```
1. Augusto Cezar Alves Sampaio
2. 26/02/2025

3a. Síntese e verificação de simulação de sistemas robóticos
3b. 2022 - Atual
3c. Trata-se do Projeto PQ 1A do pesquisador. O contexto geral deste projeto é o desenvolvimento rigoroso de sistemas robóticos...
3d. Conselho Nacional de Desenvolvimento Científico e Tecnológico
3e. Augusto Cezar Alves Sampaio
3f. -
3g. Formal Specification, Model Checking, Process Algebra, Software Verification
3h. FDR, UPPAAL

3a. Um Framework Baseado em Modelos para Análise e Teste Composicionais de Sistemas Reativos
3b. 2017 - Atual
3c. Este projeto propõe um framework integrado para análise (via verificação de modelos) e teste de sistemas reativos...
3d. -
3e. Augusto Cezar Alves Sampaio
3f. Embraer
3g. Modelling, Model Checking, Model-Based Testing, Model-Oriented
3h. -
```

## 🚀 **Performance & Intelligence**

- **Smart Extraction**: Advanced parsing algorithms for complex CV structures
- **Automatic Classification**: AI-powered identification of formal methods content
- **Industry Detection**: Intelligent recognition of industry partnerships
- **Threaded Processing**: Up to 8 concurrent threads for faster data collection
- **Respectful Scraping**: Built-in delays and error handling
- **Comprehensive Logging**: Detailed progress tracking and error reporting

## 🔧 **Advanced Features**

### Formal Methods Intelligence

The system automatically identifies:

- **30+ Formal Methods Concepts**: Specification, verification, model checking, etc.
- **25+ Tools**: Alloy, SPIN, Coq, Isabelle, TLA+, NuSMV, etc.
- **Industry Keywords**: Multi-language detection of commercial partnerships

### Data Analysis

- **Timeline Analysis**: Project trends over time
- **Institution Ranking**: Top institutions by formal methods research
- **Tool Usage Patterns**: Most commonly used formal methods tools
- **Concept Mapping**: Research focus areas and trends

## 📤 **Data Export & Integration**

- **JSON Export**: Complete data export with all project details
- **CSV Export**: Tabular data for analysis tools
- **Direct Database Access**: SQLite for custom queries and analysis
- **API-Ready**: Structured data for integration with other tools

## Rate Limiting & Ethics

The scraper includes built-in protections:

- 2 seconds between search result pages
- 3 seconds between detailed CV requests
- Comprehensive error handling and retry logic
- Respectful server load management

## Legal and Ethical Considerations

- This scraper is for educational and research purposes
- Respect the CNPq terms of service
- Use reasonable delays between requests
- Don't overload the servers
- Consider the robots.txt file

## 🔍 **Troubleshooting**

### Common Issues

1. **No researchers found**: Check if the search terms exist in the CNPq database
2. **Connection errors**: Check your internet connection and try again later
3. **Empty project details**: Some researchers may have restricted CV access
4. **Missing formal methods data**: The system may need training on new concepts/tools

### Advanced Configuration

You can customize the formal methods detection by modifying:

- `FORMAL_METHODS_CONCEPTS` list in `main.py`
- `FORMAL_METHODS_TOOLS` list in `main.py`
- `INDUSTRY_KEYWORDS` list in `main.py`

## 🤝 **Contributing**

We welcome contributions! Areas for improvement:

- Additional formal methods concepts and tools
- Better industry cooperation detection
- Enhanced parsing algorithms
- New analysis features

## 📝 **License**

This project is for educational purposes. Please respect the CNPq platform's terms of service.

---

**🔬 Enhanced CNPq Lattes Research Aggregator - Comprehensive Formal Methods Research Intelligence**
