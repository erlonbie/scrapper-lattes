#!/usr/bin/env python3
"""
CNPq Researcher Database Chart Generator

Generates visual charts from the scraped researcher data and saves them to the charts/ directory.
"""

import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from collections import Counter
import os
from datetime import datetime

# Set style for better-looking charts
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def connect_database():
    """Connect to the SQLite database"""
    try:
        conn = sqlite3.connect('cnpq_researchers.db')
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def create_charts_directory():
    """Create charts directory if it doesn't exist"""
    if not os.path.exists('charts'):
        os.makedirs('charts')
        print("📁 Created charts/ directory")

def generate_search_terms_chart(conn):
    """Generate chart showing distribution of researchers by search terms"""
    print("📊 Generating search terms distribution chart...")
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT search_term, COUNT(*) as count 
        FROM researchers 
        GROUP BY search_term 
        ORDER BY count DESC
        LIMIT 15
    ''')
    
    data = cursor.fetchall()
    terms = [row[0][:30] + '...' if len(row[0]) > 30 else row[0] for row in data]  # Truncate long terms
    counts = [row[1] for row in data]
    
    plt.figure(figsize=(14, 8))
    bars = plt.bar(range(len(terms)), counts, color=sns.color_palette("viridis", len(terms)))
    
    plt.title('Distribution of Researchers by Search Terms', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Search Terms', fontsize=12)
    plt.ylabel('Number of Researchers', fontsize=12)
    plt.xticks(range(len(terms)), terms, rotation=45, ha='right')
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('charts/search_terms_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✅ Saved: charts/search_terms_distribution.png")

def generate_institutions_chart(conn):
    """Generate chart showing top institutions"""
    print("🏛️  Generating top institutions chart...")
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT institution, COUNT(*) as count 
        FROM researchers 
        WHERE institution != "" AND institution IS NOT NULL
        GROUP BY institution 
        ORDER BY count DESC 
        LIMIT 15
    ''')
    
    data = cursor.fetchall()
    institutions = [row[0][:40] + '...' if len(row[0]) > 40 else row[0] for row in data]
    counts = [row[1] for row in data]
    
    plt.figure(figsize=(12, 10))
    bars = plt.barh(range(len(institutions)), counts, color=sns.color_palette("plasma", len(institutions)))
    
    plt.title('Top 15 Institutions by Number of Researchers', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Number of Researchers', fontsize=12)
    plt.ylabel('Institutions', fontsize=12)
    plt.yticks(range(len(institutions)), institutions)
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        width = bar.get_width()
        plt.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                f'{int(width)}', ha='left', va='center', fontweight='bold')
    
    plt.gca().invert_yaxis()  # Highest values at top
    plt.tight_layout()
    plt.savefig('charts/top_institutions.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✅ Saved: charts/top_institutions.png")

def generate_geographic_distribution_chart(conn):
    """Generate chart showing geographic distribution"""
    print("🌍 Generating geographic distribution chart...")
    
    cursor = conn.cursor()
    
    # Countries distribution
    cursor.execute('''
        SELECT country, COUNT(*) as count 
        FROM researchers 
        WHERE country IS NOT NULL AND country != ""
        GROUP BY country 
        ORDER BY count DESC
    ''')
    
    country_data = cursor.fetchall()
    
    if country_data:
        countries = [row[0] for row in country_data]
        counts = [row[1] for row in country_data]
        
        plt.figure(figsize=(10, 8))
        colors = sns.color_palette("Set3", len(countries))
        wedges, texts, autotexts = plt.pie(counts, labels=countries, autopct='%1.1f%%', 
                                          colors=colors, startangle=90)
        
        plt.title('Geographic Distribution of Researchers by Country', 
                 fontsize=16, fontweight='bold', pad=20)
        
        # Make percentage text bold
        for autotext in autotexts:
            autotext.set_fontweight('bold')
        
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig('charts/geographic_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("   ✅ Saved: charts/geographic_distribution.png")
    
    # Brazilian states distribution (if applicable)
    cursor.execute('''
        SELECT state, COUNT(*) as count 
        FROM researchers 
        WHERE state IS NOT NULL AND state != "" AND country = "Brasil"
        GROUP BY state 
        ORDER BY count DESC
        LIMIT 10
    ''')
    
    state_data = cursor.fetchall()
    
    if state_data:
        states = [row[0] for row in state_data]
        counts = [row[1] for row in state_data]
        
        plt.figure(figsize=(12, 8))
        bars = plt.bar(states, counts, color=sns.color_palette("coolwarm", len(states)))
        
        plt.title('Distribution of Brazilian Researchers by State (Top 10)', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('States', fontsize=12)
        plt.ylabel('Number of Researchers', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{int(height)}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('charts/brazilian_states_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("   ✅ Saved: charts/brazilian_states_distribution.png")

def generate_research_overview_chart(conn):
    """Generate overview chart with key statistics"""
    print("📈 Generating research overview chart...")
    
    cursor = conn.cursor()
    
    # Get key statistics
    cursor.execute('SELECT COUNT(*) FROM researchers')
    total_researchers = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT search_term) FROM researchers')
    total_terms = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT institution) FROM researchers WHERE institution != ""')
    total_institutions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT country) FROM researchers WHERE country != ""')
    total_countries = cursor.fetchone()[0]
    
    # Create overview chart
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('CNPq Research Database Overview', fontsize=20, fontweight='bold', y=0.98)
    
    # Chart 1: Total researchers (big number)
    ax1.text(0.5, 0.5, f'{total_researchers}', ha='center', va='center', 
             fontsize=60, fontweight='bold', color='#2E86AB')
    ax1.text(0.5, 0.2, 'Total Researchers', ha='center', va='center', 
             fontsize=16, fontweight='bold')
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    # Chart 2: Search terms pie chart (top 8)
    cursor.execute('''
        SELECT search_term, COUNT(*) as count 
        FROM researchers 
        GROUP BY search_term 
        ORDER BY count DESC 
        LIMIT 8
    ''')
    term_data = cursor.fetchall()
    
    if term_data:
        labels = [term[:20] + '...' if len(term) > 20 else term for term, _ in term_data]
        sizes = [count for _, count in term_data]
        
        ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax2.set_title('Top Search Terms', fontweight='bold', fontsize=14)
    
    # Chart 3: Key statistics
    stats_labels = ['Search Terms', 'Institutions', 'Countries']
    stats_values = [total_terms, total_institutions, total_countries]
    
    bars = ax3.bar(stats_labels, stats_values, color=['#F18F01', '#C73E1D', '#2E86AB'])
    ax3.set_title('Database Statistics', fontweight='bold', fontsize=14)
    ax3.set_ylabel('Count')
    
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    # Chart 4: Top institutions (top 5)
    cursor.execute('''
        SELECT institution, COUNT(*) as count 
        FROM researchers 
        WHERE institution != "" AND institution IS NOT NULL
        GROUP BY institution 
        ORDER BY count DESC 
        LIMIT 5
    ''')
    inst_data = cursor.fetchall()
    
    if inst_data:
        inst_names = [inst[:25] + '...' if len(inst) > 25 else inst for inst, _ in inst_data]
        inst_counts = [count for _, count in inst_data]
        
        ax4.barh(inst_names, inst_counts, color=sns.color_palette("viridis", len(inst_names)))
        ax4.set_title('Top 5 Institutions', fontweight='bold', fontsize=14)
        ax4.set_xlabel('Researchers')
        
        for i, count in enumerate(inst_counts):
            ax4.text(count + 0.5, i, f'{count}', va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('charts/research_overview.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✅ Saved: charts/research_overview.png")

def generate_term_correlation_heatmap(conn):
    """Generate heatmap showing correlation between search terms"""
    print("🔥 Generating search term correlation heatmap...")
    
    cursor = conn.cursor()
    cursor.execute('SELECT cnpq_id, search_term FROM researchers')
    data = cursor.fetchall()
    
    # Create a matrix of researchers vs terms
    researcher_terms = {}
    all_terms = set()
    
    for cnpq_id, search_term in data:
        if cnpq_id not in researcher_terms:
            researcher_terms[cnpq_id] = set()
        
        # Split multiple terms
        terms = [term.strip() for term in search_term.split(',')]
        for term in terms:
            researcher_terms[cnpq_id].add(term)
            all_terms.add(term)
    
    # Get top terms only (to make heatmap readable)
    cursor.execute('''
        SELECT search_term, COUNT(*) as count 
        FROM researchers 
        GROUP BY search_term 
        ORDER BY count DESC 
        LIMIT 10
    ''')
    
    top_terms = [row[0] for row in cursor.fetchall()]
    
    # Create correlation matrix
    correlation_matrix = np.zeros((len(top_terms), len(top_terms)))
    
    for i, term1 in enumerate(top_terms):
        for j, term2 in enumerate(top_terms):
            if i == j:
                correlation_matrix[i][j] = 1.0
            else:
                # Count researchers that have both terms
                common_researchers = 0
                term1_researchers = 0
                
                for cnpq_id, terms in researcher_terms.items():
                    has_term1 = any(term1 in term for term in terms)
                    has_term2 = any(term2 in term for term in terms)
                    
                    if has_term1:
                        term1_researchers += 1
                        if has_term2:
                            common_researchers += 1
                
                if term1_researchers > 0:
                    correlation_matrix[i][j] = common_researchers / term1_researchers
                else:
                    correlation_matrix[i][j] = 0
    
    # Create heatmap
    plt.figure(figsize=(12, 10))
    
    # Truncate term names for display
    display_terms = [term[:25] + '...' if len(term) > 25 else term for term in top_terms]
    
    sns.heatmap(correlation_matrix, 
                xticklabels=display_terms,
                yticklabels=display_terms,
                annot=True, 
                fmt='.2f', 
                cmap='YlOrRd',
                square=True,
                cbar_kws={'label': 'Co-occurrence Rate'})
    
    plt.title('Search Term Co-occurrence Heatmap', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Search Terms', fontsize=12)
    plt.ylabel('Search Terms', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    
    plt.tight_layout()
    plt.savefig('charts/term_correlation_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✅ Saved: charts/term_correlation_heatmap.png")

def generate_summary_report(conn):
    """Generate a text summary report"""
    print("📝 Generating summary report...")
    
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM researchers')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT search_term) FROM researchers')
    unique_terms = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT institution) FROM researchers WHERE institution != ""')
    unique_institutions = cursor.fetchone()[0]
    
    cursor.execute('SELECT search_term, COUNT(*) FROM researchers GROUP BY search_term ORDER BY COUNT(*) DESC LIMIT 1')
    top_term_data = cursor.fetchone()
    
    cursor.execute('SELECT institution, COUNT(*) FROM researchers WHERE institution != "" GROUP BY institution ORDER BY COUNT(*) DESC LIMIT 1')
    top_institution_data = cursor.fetchone()
    
    # Create summary report
    report = f"""
# CNPq Research Database Summary Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
- **Total Researchers**: {total:,}
- **Unique Search Terms**: {unique_terms}
- **Unique Institutions**: {unique_institutions}

## Top Results
- **Most Productive Search Term**: {top_term_data[0]} ({top_term_data[1]} researchers)
- **Top Institution**: {top_institution_data[0]} ({top_institution_data[1]} researchers)

## Charts Generated
1. `search_terms_distribution.png` - Distribution of researchers by search terms
2. `top_institutions.png` - Top 15 institutions by researcher count
3. `geographic_distribution.png` - Geographic distribution by country
4. `brazilian_states_distribution.png` - Brazilian states distribution (if applicable)
5. `research_overview.png` - Comprehensive overview dashboard
6. `term_correlation_heatmap.png` - Search term co-occurrence analysis

## Usage
All charts have been saved to the `charts/` directory in high resolution (300 DPI) 
and are ready for use in presentations, reports, or publications.
"""
    
    with open('charts/summary_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("   ✅ Saved: charts/summary_report.md")

def main():
    """Main function to generate all charts"""
    print("🎨 CNPq Research Database Chart Generator")
    print("=" * 50)
    
    # Check if required libraries are available
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        import pandas as pd
    except ImportError as e:
        print(f"❌ Missing required library: {e}")
        print("Please install required packages:")
        print("uv add matplotlib seaborn pandas")
        return
    
    # Connect to database
    conn = connect_database()
    if not conn:
        return
    
    # Check if database has data
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM researchers")
    total_researchers = cursor.fetchone()[0]
    
    if total_researchers == 0:
        print("❌ No data found in database. Please run the scraper first.")
        conn.close()
        return
    
    print(f"📊 Found {total_researchers} researchers in database")
    
    # Create charts directory
    create_charts_directory()
    
    try:
        # Generate all charts
        generate_search_terms_chart(conn)
        generate_institutions_chart(conn)
        generate_geographic_distribution_chart(conn)
        generate_research_overview_chart(conn)
        generate_term_correlation_heatmap(conn)
        generate_summary_report(conn)
        
        print("\n" + "=" * 50)
        print("✅ All charts generated successfully!")
        print("📁 Charts saved in: charts/")
        print("📝 Summary report: charts/summary_report.md")
        print("\n💡 You can now use these charts in presentations or reports.")
        
    except Exception as e:
        print(f"❌ Error generating charts: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 