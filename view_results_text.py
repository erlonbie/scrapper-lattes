#!/usr/bin/env python3
"""
Script to view and analyze the scraped CNPq researcher data.
"""

import sqlite3
import sys
from datetime import datetime

def connect_database():
    """Connect to the SQLite database"""
    try:
        conn = sqlite3.connect('cnpq_researchers.db')
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def view_all_researchers(conn):
    """Display all researchers in the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM researchers")
    total = cursor.fetchone()[0]
    
    print(f"\n=== Total Researchers: {total} ===\n")
    
    cursor.execute("""
        SELECT cnpq_id, name, institution, area, city, state, country, search_term 
        FROM researchers 
        ORDER BY name
    """)
    
    results = cursor.fetchall()
    
    for i, row in enumerate(results, 1):
        cnpq_id, name, institution, area, city, state, country, search_term = row
        print(f"{i}. {name}")
        print(f"   CNPq ID: {cnpq_id}")
        print(f"   Institution: {institution or 'N/A'}")
        print(f"   Area: {area or 'N/A'}")
        print(f"   Location: {', '.join(filter(None, [city, state, country])) or 'N/A'}")
        print(f"   Search Term: {search_term}")
        print(f"   Lattes URL: http://lattes.cnpq.br/{cnpq_id}")
        print("-" * 80)

def view_statistics(conn):
    """Display statistics about the scraped data"""
    cursor = conn.cursor()
    
    print("\n=== Database Statistics ===\n")
    
    # Total researchers
    cursor.execute("SELECT COUNT(*) FROM researchers")
    total = cursor.fetchone()[0]
    print(f"Total Researchers: {total}")
    
    # By search term
    cursor.execute("SELECT search_term, COUNT(*) FROM researchers GROUP BY search_term")
    search_terms = cursor.fetchall()
    print("\nBy Search Term:")
    for term, count in search_terms:
        print(f"  {term}: {count}")
    
    # By country
    cursor.execute("SELECT country, COUNT(*) FROM researchers WHERE country IS NOT NULL GROUP BY country ORDER BY COUNT(*) DESC")
    countries = cursor.fetchall()
    print("\nBy Country:")
    for country, count in countries:
        print(f"  {country}: {count}")
    
    # By state (for Brazil)
    cursor.execute("SELECT state, COUNT(*) FROM researchers WHERE state IS NOT NULL AND country = 'Brasil' GROUP BY state ORDER BY COUNT(*) DESC")
    states = cursor.fetchall()
    if states:
        print("\nBy State (Brazil):")
        for state, count in states:
            print(f"  {state}: {count}")
    
    # Top institutions
    cursor.execute("SELECT institution, COUNT(*) FROM researchers WHERE institution IS NOT NULL GROUP BY institution ORDER BY COUNT(*) DESC LIMIT 10")
    institutions = cursor.fetchall()
    print("\nTop Institutions:")
    for institution, count in institutions:
        print(f"  {institution}: {count}")

def search_researchers(conn, search_query):
    """Search for researchers by name or institution"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cnpq_id, name, institution, area, city, state, country 
        FROM researchers 
        WHERE name LIKE ? OR institution LIKE ?
        ORDER BY name
    """, (f"%{search_query}%", f"%{search_query}%"))
    
    results = cursor.fetchall()
    
    if not results:
        print(f"No researchers found matching '{search_query}'")
        return
    
    print(f"\n=== Search Results for '{search_query}' ({len(results)} found) ===\n")
    
    for i, row in enumerate(results, 1):
        cnpq_id, name, institution, area, city, state, country = row
        print(f"{i}. {name}")
        print(f"   CNPq ID: {cnpq_id}")
        print(f"   Institution: {institution or 'N/A'}")
        print(f"   Area: {area or 'N/A'}")
        print(f"   Location: {', '.join(filter(None, [city, state, country])) or 'N/A'}")
        print(f"   Lattes URL: http://lattes.cnpq.br/{cnpq_id}")
        print("-" * 60)

def export_to_csv(conn, filename="researchers.csv"):
    """Export all data to CSV file"""
    import csv
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cnpq_id, name, institution, area, city, state, country, lattes_url, search_term, created_at
        FROM researchers 
        ORDER BY name
    """)
    
    results = cursor.fetchall()
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['CNPq_ID', 'Name', 'Institution', 'Area', 'City', 'State', 'Country', 'Lattes_URL', 'Search_Term', 'Created_At'])
        writer.writerows(results)
    
    print(f"Data exported to {filename} ({len(results)} records)")

def main():
    """Main function with interactive menu"""
    conn = connect_database()
    if not conn:
        return
    
    while True:
        print("\n" + "="*50)
        print("CNPq Researcher Database Viewer")
        print("="*50)
        print("1. View all researchers")
        print("2. View statistics")
        print("3. Search researchers")
        print("4. Export to CSV")
        print("5. Exit")
        print("-"*50)
        
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == '1':
            view_all_researchers(conn)
        elif choice == '2':
            view_statistics(conn)
        elif choice == '3':
            query = input("Enter search term (name or institution): ").strip()
            if query:
                search_researchers(conn, query)
        elif choice == '4':
            filename = input("Enter CSV filename (default: researchers.csv): ").strip()
            if not filename:
                filename = "researchers.csv"
            export_to_csv(conn, filename)
        elif choice == '5':
            break
        else:
            print("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")
    
    conn.close()
    print("Goodbye!")

if __name__ == "__main__":
    main() 