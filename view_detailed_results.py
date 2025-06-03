#!/usr/bin/env python3
"""
Enhanced CNPq Lattes Results Viewer with Detailed Project Information
Displays researchers and their formal methods projects with comprehensive details
"""

import sqlite3
import sys
from datetime import datetime
import json

class DetailedResultsViewer:
    def __init__(self, db_path='cnpq_researchers.db'):
        self.db_path = db_path
        try:
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"❌ Error connecting to database: {e}")
            sys.exit(1)
    
    def show_menu(self):
        """Display the main menu"""
        print("\n" + "="*80)
        print("🔬 CNPq Lattes Enhanced Results Viewer")
        print("="*80)
        print("1. 👥 View all researchers with project counts")
        print("2. 📊 Show detailed statistics")
        print("3. 🔍 Search researchers by name or institution")
        print("4. 📋 View detailed researcher profile")
        print("5. 🎯 Show formal methods projects only")
        print("6. 🏭 Show projects with industry cooperation")
        print("7. 🛠️ Show projects by formal methods tools")
        print("8. 💡 Show projects by formal methods concepts")
        print("9. 📤 Export detailed data to JSON")
        print("10. 📈 Show project timeline analysis")
        print("0. 🚪 Exit")
        print("="*80)
    
    def view_all_researchers(self):
        """View all researchers with project counts"""
        print("\n📊 All Researchers with Project Information:")
        print("-" * 100)
        
        query = '''
        SELECT r.name, r.institution, r.last_update_date, r.search_term,
               COUNT(p.id) as total_projects,
               SUM(CASE WHEN p.is_formal_methods_related = 1 THEN 1 ELSE 0 END) as fm_projects,
               r.lattes_url
        FROM researchers r
        LEFT JOIN projects p ON r.cnpq_id = p.cnpq_id
        GROUP BY r.cnpq_id
        ORDER BY fm_projects DESC, total_projects DESC
        '''
        
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        
        if not results:
            print("No researchers found in database.")
            return
        
        print(f"{'Name':<40} {'Institution':<30} {'Updated':<12} {'Total':<6} {'FM':<4} {'Search Terms'}")
        print("-" * 100)
        
        for row in results:
            name, institution, last_update, search_term, total_projects, fm_projects, lattes_url = row
            name = (name or "Unknown")[:39]
            institution = (institution or "Unknown")[:29]
            last_update = last_update or "Unknown"
            search_terms = (search_term or "")[:20] + "..." if len(search_term or "") > 20 else (search_term or "")
            
            print(f"{name:<40} {institution:<30} {last_update:<12} {total_projects:<6} {fm_projects:<4} {search_terms}")
        
        print(f"\nTotal researchers: {len(results)}")
        print(f"Researchers with formal methods projects: {sum(1 for r in results if r[5] > 0)}")
    
    def show_statistics(self):
        """Show detailed statistics"""
        print("\n📈 Detailed Statistics:")
        print("-" * 60)
        
        # Basic researcher stats
        self.cursor.execute("SELECT COUNT(*) FROM researchers")
        total_researchers = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM projects")
        total_projects = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM projects WHERE is_formal_methods_related = 1")
        fm_projects = self.cursor.fetchone()[0]
        
        print(f"📊 Basic Statistics:")
        print(f"   Total researchers: {total_researchers}")
        print(f"   Total projects: {total_projects}")
        print(f"   Formal methods projects: {fm_projects} ({fm_projects/total_projects*100:.1f}%)" if total_projects > 0 else "   Formal methods projects: 0")
        
        # Top institutions
        self.cursor.execute('''
            SELECT institution, COUNT(*) as count 
            FROM researchers 
            WHERE institution IS NOT NULL AND institution != ""
            GROUP BY institution 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        institutions = self.cursor.fetchall()
        
        print(f"\n🏛️  Top Institutions:")
        for inst, count in institutions:
            print(f"   {inst}: {count} researchers")
        
        # Projects with industry cooperation
        self.cursor.execute('''
            SELECT COUNT(*) FROM projects 
            WHERE industry_cooperation IS NOT NULL AND industry_cooperation != ""
        ''')
        industry_projects = self.cursor.fetchone()[0]
        
        print(f"\n🏭 Industry Cooperation:")
        print(f"   Projects with industry cooperation: {industry_projects}")
        
        # Most common formal methods tools
        self.cursor.execute('''
            SELECT formal_methods_tools, COUNT(*) as count
            FROM projects 
            WHERE formal_methods_tools IS NOT NULL AND formal_methods_tools != ""
            GROUP BY formal_methods_tools
            ORDER BY count DESC
            LIMIT 5
        ''')
        tools = self.cursor.fetchall()
        
        print(f"\n🛠️  Common Formal Methods Tools:")
        for tool, count in tools:
            print(f"   {tool}: {count} projects")
        
        # Project status distribution
        self.cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM projects 
            WHERE status IS NOT NULL AND status != ""
            GROUP BY status
            ORDER BY count DESC
        ''')
        statuses = self.cursor.fetchall()
        
        print(f"\n📊 Project Status Distribution:")
        for status, count in statuses:
            print(f"   {status}: {count} projects")
    
    def search_researchers(self):
        """Search researchers by name or institution"""
        search_term = input("\n🔍 Enter search term (name or institution): ").strip()
        if not search_term:
            print("No search term provided.")
            return
        
        query = '''
        SELECT r.name, r.institution, r.cnpq_id, r.last_update_date,
               COUNT(p.id) as total_projects,
               SUM(CASE WHEN p.is_formal_methods_related = 1 THEN 1 ELSE 0 END) as fm_projects
        FROM researchers r
        LEFT JOIN projects p ON r.cnpq_id = p.cnpq_id
        WHERE r.name LIKE ? OR r.institution LIKE ?
        GROUP BY r.cnpq_id
        ORDER BY fm_projects DESC, total_projects DESC
        '''
        
        search_pattern = f"%{search_term}%"
        self.cursor.execute(query, (search_pattern, search_pattern))
        results = self.cursor.fetchall()
        
        if not results:
            print(f"No researchers found matching '{search_term}'")
            return
        
        print(f"\n📋 Search results for '{search_term}':")
        print("-" * 80)
        
        for i, row in enumerate(results, 1):
            name, institution, cnpq_id, last_update, total_projects, fm_projects = row
            print(f"{i}. {name or 'Unknown'}")
            print(f"   Institution: {institution or 'Unknown'}")
            print(f"   CNPq ID: {cnpq_id}")
            print(f"   Last Update: {last_update or 'Unknown'}")
            print(f"   Projects: {total_projects} total, {fm_projects or 0} formal methods")
            print()
    
    def view_researcher_profile(self):
        """View detailed researcher profile with projects"""
        search_term = input("\n👤 Enter researcher name or CNPq ID: ").strip()
        if not search_term:
            print("No search term provided.")
            return
        
        # First find the researcher
        query = '''
        SELECT cnpq_id, name, institution, area, city, state, country, 
               last_update_date, search_term, lattes_url
        FROM researchers 
        WHERE name LIKE ? OR cnpq_id = ?
        '''
        
        search_pattern = f"%{search_term}%"
        self.cursor.execute(query, (search_pattern, search_term))
        researchers = self.cursor.fetchall()
        
        if not researchers:
            print(f"No researcher found matching '{search_term}'")
            return
        
        if len(researchers) > 1:
            print(f"\nFound {len(researchers)} researchers:")
            for i, r in enumerate(researchers, 1):
                print(f"{i}. {r[1]} ({r[0]})")
            
            try:
                choice = int(input("\nSelect researcher (number): ")) - 1
                if 0 <= choice < len(researchers):
                    researcher = researchers[choice]
                else:
                    print("Invalid selection.")
                    return
            except ValueError:
                print("Invalid input.")
                return
        else:
            researcher = researchers[0]
        
        cnpq_id, name, institution, area, city, state, country, last_update, search_term, lattes_url = researcher
        
        print(f"\n{'='*80}")
        print(f"👤 Researcher Profile: {name}")
        print(f"{'='*80}")
        print(f"CNPq ID: {cnpq_id}")
        print(f"Institution: {institution or 'Not specified'}")
        print(f"Area: {area or 'Not specified'}")
        print(f"Location: {', '.join(filter(None, [city, state, country])) or 'Not specified'}")
        print(f"Last Lattes Update: {last_update or 'Unknown'}")
        print(f"Found through search terms: {search_term or 'Unknown'}")
        print(f"Lattes URL: {lattes_url or 'Not available'}")
        
        # Get projects
        project_query = '''
        SELECT title, start_date, end_date, status, description, 
               funding_sources, coordinator_name, team_members,
               industry_cooperation, formal_methods_concepts, 
               formal_methods_tools, is_formal_methods_related
        FROM projects 
        WHERE cnpq_id = ?
        ORDER BY is_formal_methods_related DESC, start_date DESC
        '''
        
        self.cursor.execute(project_query, (cnpq_id,))
        projects = self.cursor.fetchall()
        
        if projects:
            print(f"\n📋 Projects ({len(projects)} total):")
            print("-" * 80)
            
            for i, project in enumerate(projects, 1):
                (title, start_date, end_date, status, description, funding_sources, 
                 coordinator_name, team_members, industry_cooperation, 
                 fm_concepts, fm_tools, is_fm_related) = project
                
                print(f"\n{i}. {'🎯' if is_fm_related else '📁'} {title or 'Untitled Project'}")
                
                if start_date or end_date:
                    period = f"{start_date or '?'} - {end_date or '?'}"
                    print(f"   📅 Period: {period}")
                
                if status:
                    print(f"   📊 Status: {status}")
                
                if description:
                    desc = description[:200] + "..." if len(description) > 200 else description
                    print(f"   📝 Description: {desc}")
                
                if funding_sources:
                    print(f"   💰 Funding: {funding_sources}")
                
                if coordinator_name:
                    print(f"   👑 Coordinator: {coordinator_name}")
                
                if industry_cooperation:
                    print(f"   🏭 Industry Cooperation: {industry_cooperation}")
                
                if fm_concepts:
                    print(f"   💡 FM Concepts: {fm_concepts}")
                
                if fm_tools:
                    print(f"   🛠️ FM Tools: {fm_tools}")
        else:
            print(f"\n📋 No projects found for this researcher.")
    
    def show_formal_methods_projects(self):
        """Show only formal methods related projects"""
        print("\n🎯 Formal Methods Projects:")
        print("-" * 100)
        
        query = '''
        SELECT r.name, p.title, p.start_date, p.end_date, p.status,
               p.formal_methods_concepts, p.formal_methods_tools, p.funding_sources
        FROM projects p
        JOIN researchers r ON p.cnpq_id = r.cnpq_id
        WHERE p.is_formal_methods_related = 1
        ORDER BY p.start_date DESC
        '''
        
        self.cursor.execute(query)
        projects = self.cursor.fetchall()
        
        if not projects:
            print("No formal methods projects found.")
            return
        
        for i, project in enumerate(projects, 1):
            name, title, start_date, end_date, status, concepts, tools, funding = project
            print(f"\n{i}. {title}")
            print(f"   👤 Researcher: {name}")
            print(f"   📅 Period: {start_date or '?'} - {end_date or '?'}")
            if status:
                print(f"   📊 Status: {status}")
            if concepts:
                print(f"   💡 Concepts: {concepts}")
            if tools:
                print(f"   🛠️ Tools: {tools}")
            if funding:
                print(f"   💰 Funding: {funding}")
        
        print(f"\nTotal formal methods projects: {len(projects)}")
    
    def show_industry_cooperation(self):
        """Show projects with industry cooperation"""
        print("\n🏭 Projects with Industry Cooperation:")
        print("-" * 100)
        
        query = '''
        SELECT r.name, p.title, p.industry_cooperation, p.start_date, p.end_date
        FROM projects p
        JOIN researchers r ON p.cnpq_id = r.cnpq_id
        WHERE p.industry_cooperation IS NOT NULL AND p.industry_cooperation != ""
        ORDER BY p.start_date DESC
        '''
        
        self.cursor.execute(query)
        projects = self.cursor.fetchall()
        
        if not projects:
            print("No projects with industry cooperation found.")
            return
        
        for i, project in enumerate(projects, 1):
            name, title, cooperation, start_date, end_date = project
            print(f"\n{i}. {title}")
            print(f"   👤 Researcher: {name}")
            print(f"   📅 Period: {start_date or '?'} - {end_date or '?'}")
            print(f"   🏭 Industry: {cooperation}")
        
        print(f"\nTotal projects with industry cooperation: {len(projects)}")
    
    def export_to_json(self):
        """Export detailed data to JSON"""
        print("\n📤 Exporting data to JSON...")
        
        # Get all researchers with their projects
        query = '''
        SELECT r.cnpq_id, r.name, r.institution, r.area, r.city, r.state, r.country,
               r.last_update_date, r.search_term, r.lattes_url
        FROM researchers r
        ORDER BY r.name
        '''
        
        self.cursor.execute(query)
        researchers = self.cursor.fetchall()
        
        export_data = []
        
        for researcher in researchers:
            cnpq_id, name, institution, area, city, state, country, last_update, search_term, lattes_url = researcher
            
            # Get projects for this researcher
            project_query = '''
            SELECT title, start_date, end_date, status, description, 
                   funding_sources, coordinator_name, team_members,
                   industry_cooperation, formal_methods_concepts, 
                   formal_methods_tools, is_formal_methods_related
            FROM projects 
            WHERE cnpq_id = ?
            ORDER BY start_date DESC
            '''
            
            self.cursor.execute(project_query, (cnpq_id,))
            projects = self.cursor.fetchall()
            
            project_list = []
            for project in projects:
                project_dict = {
                    'title': project[0],
                    'start_date': project[1],
                    'end_date': project[2],
                    'status': project[3],
                    'description': project[4],
                    'funding_sources': project[5],
                    'coordinator_name': project[6],
                    'team_members': project[7],
                    'industry_cooperation': project[8],
                    'formal_methods_concepts': project[9],
                    'formal_methods_tools': project[10],
                    'is_formal_methods_related': bool(project[11])
                }
                project_list.append(project_dict)
            
            researcher_dict = {
                'cnpq_id': cnpq_id,
                'name': name,
                'institution': institution,
                'area': area,
                'city': city,
                'state': state,
                'country': country,
                'last_update_date': last_update,
                'search_term': search_term,
                'lattes_url': lattes_url,
                'projects': project_list
            }
            
            export_data.append(researcher_dict)
        
        filename = f"cnpq_detailed_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Data exported to {filename}")
            print(f"📊 Exported {len(export_data)} researchers with {sum(len(r['projects']) for r in export_data)} projects")
        except Exception as e:
            print(f"❌ Error exporting data: {e}")
    
    def show_timeline_analysis(self):
        """Show project timeline analysis"""
        print("\n📈 Project Timeline Analysis:")
        print("-" * 60)
        
        # Projects by year
        query = '''
        SELECT 
            CASE 
                WHEN start_date LIKE '%-%' THEN substr(start_date, 1, 4)
                WHEN start_date LIKE '%/%' THEN substr(start_date, -4)
                ELSE start_date
            END as year,
            COUNT(*) as total_projects,
            SUM(CASE WHEN is_formal_methods_related = 1 THEN 1 ELSE 0 END) as fm_projects
        FROM projects 
        WHERE start_date IS NOT NULL AND start_date != ""
        GROUP BY year
        ORDER BY year DESC
        LIMIT 10
        '''
        
        self.cursor.execute(query)
        timeline = self.cursor.fetchall()
        
        if timeline:
            print("📅 Projects by Start Year (last 10 years):")
            print(f"{'Year':<6} {'Total':<8} {'FM':<6} {'% FM':<8}")
            print("-" * 30)
            
            for year, total, fm in timeline:
                fm_percent = (fm / total * 100) if total > 0 else 0
                print(f"{year:<6} {total:<8} {fm:<6} {fm_percent:.1f}%")
        
        # Active projects
        query = '''
        SELECT COUNT(*) FROM projects 
        WHERE status LIKE '%andamento%' OR status LIKE '%atual%' OR status LIKE '%current%'
        '''
        
        self.cursor.execute(query)
        active_projects = self.cursor.fetchone()[0]
        
        print(f"\n📊 Active Projects: {active_projects}")
    
    def run(self):
        """Main loop"""
        while True:
            self.show_menu()
            
            try:
                choice = input("\n🔢 Select an option: ").strip()
                
                if choice == '0':
                    print("\n👋 Goodbye!")
                    break
                elif choice == '1':
                    self.view_all_researchers()
                elif choice == '2':
                    self.show_statistics()
                elif choice == '3':
                    self.search_researchers()
                elif choice == '4':
                    self.view_researcher_profile()
                elif choice == '5':
                    self.show_formal_methods_projects()
                elif choice == '6':
                    self.show_industry_cooperation()
                elif choice == '7':
                    print("🛠️ Tool analysis feature - coming soon!")
                elif choice == '8':
                    print("💡 Concept analysis feature - coming soon!")
                elif choice == '9':
                    self.export_to_json()
                elif choice == '10':
                    self.show_timeline_analysis()
                else:
                    print("❌ Invalid option. Please try again.")
                
                input("\n⏸️  Press Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                input("\n⏸️  Press Enter to continue...")
    
    def __del__(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()

def main():
    """Main function"""
    viewer = DetailedResultsViewer()
    viewer.run()

if __name__ == "__main__":
    main() 