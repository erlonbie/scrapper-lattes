#!/usr/bin/env python3
"""
Test script for the enhanced generic project extraction
Tests the new generic patterns vs the old Augusto-specific patterns
"""

from main import CNPqScraper

def test_project_extraction():
    """Test the enhanced project extraction with various researcher summaries"""
    
    print("🧪 Testing Enhanced Generic Project Extraction")
    print("=" * 60)
    
    scraper = CNPqScraper()
    
    # Test cases with different types of researcher summaries
    test_summaries = [
        {
            "name": "Researcher 1 - AI/ML Focus",
            "summary": """
            Atua principalmente na área de inteligência artificial e aprendizado de máquina. 
            Coordenador do projeto de pesquisa denominado "Sistemas Inteligentes para Análise de Dados". 
            Desenvolve algoritmos de machine learning para processamento de linguagem natural. 
            Participou do projeto financiado pelo CNPq sobre redes neurais artificiais (2020-2023). 
            Em colaboração com Microsoft Research, trabalha no desenvolvimento de modelos de deep learning.
            """
        },
        {
            "name": "Researcher 2 - Software Engineering",
            "summary": """
            Professor da área de engenharia de software. Lidera projeto de desenvolvimento de 
            plataformas de software distribuído. Coordena cooperação com IBM Brasil para 
            criação de sistemas de cloud computing. Projeto financiado pela FAPESP sobre 
            metodologias ágeis de desenvolvimento (2019-2022). Pesquisa em microserviços 
            e arquiteturas orientadas a serviços.
            """
        },
        {
            "name": "Researcher 3 - Cybersecurity",
            "summary": """
            Especialista em segurança cibernética e criptografia. Participa do projeto 
            "Desenvolvimento de Protocolos Seguros para IoT" financiado pela FINEP. 
            Cooperação com Kaspersky Lab para análise de malware. Desenvolve soluções 
            de blockchain para sistemas distribuídos. Coordenador brasileiro do projeto 
            European H2020 sobre cybersecurity (2021-2024).
            """
        },
        {
            "name": "Researcher 4 - Databases & Big Data",
            "summary": """
            Atua na área de banco de dados e big data analytics. Coordenador do projeto 
            de implementação de sistemas de data mining para análise empresarial. 
            Parceria com Oracle Corporation para desenvolvimento de algoritmos de 
            otimização de consultas. Pesquisa financiada pelo CNPq sobre processamento 
            distribuído de grandes volumes de dados (desde 2018).
            """
        },
        {
            "name": "Researcher 5 - Formal Methods (like Augusto)",
            "summary": """
            Professor do Centro de Informática da UFPE. Coordenador do projeto COMPASS 
            financiado pela Comunidade Europeia (2011-2014). Cooperação com Motorola 
            Mobility desde 2002 com ênfase em geração automática de testes. Participa 
            de projeto com Embraer sobre verificação formal de sistemas críticos.
            """
        }
    ]
    
    print("\n🔍 Testing project extraction for different research areas:")
    print("-" * 60)
    
    total_projects = 0
    total_fm_projects = 0
    
    for i, test_case in enumerate(test_summaries, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        # Extract projects using the new generic method
        projects = scraper.extract_projects_from_summary(test_case['summary'])
        
        if projects:
            print(f"✅ Found {len(projects)} projects:")
            
            for j, project in enumerate(projects, 1):
                print(f"\n   {j}. {project.get('title', 'No title')}")
                print(f"      📝 Description: {project.get('description', 'No description')[:100]}...")
                
                if project.get('funding_sources'):
                    print(f"      💰 Funding: {project.get('funding_sources')}")
                
                if project.get('industry_cooperation'):
                    print(f"      🏢 Industry: {project.get('industry_cooperation')}")
                
                if project.get('start_date'):
                    end_date = project.get('end_date', 'Ongoing')
                    print(f"      📅 Period: {project.get('start_date')} - {end_date}")
                
                if project.get('is_formal_methods_related'):
                    print(f"      🎯 Formal Methods: Yes")
                    total_fm_projects += 1
                
                print(f"      🔍 Source: {project.get('source', 'unknown')}")
            
            total_projects += len(projects)
        else:
            print("❌ No projects found")
    
    # Summary
    print(f"\n📊 EXTRACTION SUMMARY")
    print("=" * 40)
    print(f"✅ Total projects extracted: {total_projects}")
    print(f"🎯 Formal methods projects: {total_fm_projects}")
    print(f"📈 Average projects per researcher: {total_projects/len(test_summaries):.1f}")
    
    # Test the validation functions
    print(f"\n🧪 Testing validation functions:")
    print("-" * 40)
    
    test_titles = [
        "Sistemas Inteligentes para Análise de Dados",  # Should be valid
        "Desenvolvimento de Protocolos Seguros",        # Should be valid  
        "Projeto muito curto",                          # Should be invalid (too short)
        "Um projeto sobre história medieval",           # Should be invalid (not tech)
        "Machine Learning para Processamento de Linguagem Natural",  # Should be valid
    ]
    
    for title in test_titles:
        is_valid = scraper.is_valid_project_title(title)
        status = "✅ Valid" if is_valid else "❌ Invalid"
        print(f"   {status}: {title}")
    
    print(f"\n🎉 Project extraction test completed!")
    print("💡 The new system can detect projects from any computing researcher's summary")
    
    scraper.close()

if __name__ == "__main__":
    test_project_extraction() 