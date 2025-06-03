#!/usr/bin/env python3
"""
Test script for Augusto Sampaio's Lattes CV
Tests the enhanced project extraction capabilities
"""

import sys
import sqlite3
from main import CNPqScraper

def test_augusto_sampaio():
    """Test with Augusto Sampaio's specific CNPq ID"""
    
    # Augusto's CNPq ID from the example
    cnpq_id = "K4787057H4"  # From the curl example provided
    
    print("🧪 Testing Enhanced CNPq Scraper with Augusto Sampaio's Profile")
    print("=" * 70)
    print(f"📋 CNPq ID: {cnpq_id}")
    print(f"🔗 Lattes URL: http://lattes.cnpq.br/{cnpq_id}")
    print()
    
    # Initialize scraper
    scraper = CNPqScraper(max_workers=1)
    
    try:
        # Test connection first
        print("🔌 Testing connection...")
        if not scraper.test_connection():
            print("❌ Connection failed!")
            return False
        
        print("✅ Connection successful!")
        print()
        
        # Get researcher details
        print("📥 Fetching researcher details...")
        details = scraper.get_researcher_details(cnpq_id)
        
        if not details:
            print("❌ Failed to fetch details!")
            return False
        
        print("✅ Details fetched successfully!")
        print()
        
        # Display extracted information
        print("📊 EXTRACTED INFORMATION:")
        print("-" * 50)
        
        print(f"1. Nome do pesquisador: {details.get('name', 'N/A')}")
        print(f"2. Data da última atualização: {details.get('last_update_date', 'N/A')}")
        print(f"   Instituição: {details.get('institution', 'N/A')}")
        print(f"   Área: {details.get('area', 'N/A')}")
        print()
        
        projects = details.get('projects', [])
        print(f"3. Projetos encontrados: {len(projects)}")
        print()
        
        if not projects:
            print("⚠️ Nenhum projeto encontrado!")
            print("   Isso pode indicar que:")
            print("   - O reCaptcha não foi quebrado corretamente")
            print("   - A estrutura HTML mudou")
            print("   - É necessário ajustar os padrões de parsing")
            print()
            
            # Debug: save the HTML content for analysis
            print("💾 Salvando HTML para análise...")
            
            # Try to get the raw HTML for debugging
            try:
                debug_details = scraper.get_researcher_details(cnpq_id)
                # This will generate debug files if captcha is encountered
                
                # Also try to get the preview page directly for analysis
                preview_url = f"{scraper.base_url}/preview.do"
                preview_params = {
                    'metodo': 'apresentar',
                    'id': cnpq_id
                }
                
                preview_response = scraper.session.get(preview_url, params=preview_params)
                
                with open('debug_preview_raw.html', 'w', encoding='utf-8') as f:
                    f.write(preview_response.text)
                print("   Arquivo salvo: debug_preview_raw.html")
                
                # Try direct Lattes URL too
                lattes_url = f"http://lattes.cnpq.br/{cnpq_id}"
                try:
                    lattes_response = scraper.session.get(lattes_url)
                    with open('debug_lattes_direct.html', 'w', encoding='utf-8') as f:
                        f.write(lattes_response.text)
                    print("   Arquivo salvo: debug_lattes_direct.html")
                except Exception as e:
                    print(f"   Erro ao acessar Lattes direto: {e}")
                
                # Check what's in the HTML
                html_preview = preview_response.text[:1000].lower()
                if 'captcha' in html_preview or 'código de segurança' in html_preview:
                    print("   ⚠️ Confirmado: página de captcha detectada")
                    print("   📝 Conteúdo HTML contém indicadores de captcha")
                    
                    # Look for captcha elements
                    if 'g-recaptcha' in html_preview:
                        print("   🤖 Google reCaptcha detectado")
                    if 'recaptcha' in html_preview:
                        print("   🔒 Sistema reCaptcha ativo")
                else:
                    print("   ❓ HTML não contém indicadores óbvios de captcha")
                    print(f"   📄 Preview do conteúdo: {html_preview[:200]}...")
                
            except Exception as debug_error:
                print(f"   ❌ Erro ao salvar debug: {debug_error}")
            
            print()
            print("🔧 POSSÍVEIS SOLUÇÕES:")
            print("   1. 🤖 Implementar quebra automática de reCaptcha (complexo)")
            print("   2. 🕰️ Aguardar e tentar novamente (captcha pode ser temporário)")
            print("   3. 🔄 Usar diferentes IPs/proxies para evitar captcha")
            print("   4. 📞 Contato com CNPq para acesso programático")
            print("   5. 👤 Resolução manual do captcha e extração do token")
            print()
            print("🧠 ANÁLISE TÉCNICA:")
            print("   - O CNPq implementou proteção reCaptcha recentemente")
            print("   - Tokens são gerados dinamicamente por JavaScript")
            print("   - Necessário resolver captcha para obter token válido")
            print("   - Possível implementar selenium + 2captcha/anti-captcha services")
            
        else:
            # Display projects in the requested format
            for i, project in enumerate(projects, 1):
                print(f"PROJETO {i}:")
                print(f"3a. Título: {project.get('title', 'N/A')}")
                print(f"3b. Período: {project.get('start_date', 'N/A')} - {project.get('end_date', 'N/A')}")
                
                description = project.get('description', 'N/A')
                if len(description) > 100:
                    description = description[:100] + "..."
                print(f"3c. Resumo: {description}")
                
                print(f"3d. Fontes de financiamento: {project.get('funding_sources', 'N/A')}")
                print(f"3e. Coordenador: {project.get('coordinator_name', 'N/A')}")
                print(f"3f. Cooperação com indústria: {project.get('industry_cooperation', '-')}")
                print(f"3g. Conceitos de Métodos Formais: {project.get('formal_methods_concepts', '-')}")
                print(f"3h. Ferramentas de Métodos Formais: {project.get('formal_methods_tools', '-')}")
                print(f"    Relacionado a Métodos Formais: {'Sim' if project.get('is_formal_methods_related') else 'Não'}")
                print()
        
        # Save to database for testing
        print("💾 Salvando no banco de dados...")
        researcher_data = {
            'cnpq_id': cnpq_id,
            'name': details.get('name'),
            'institution': details.get('institution'),
            'area': details.get('area'),
            'city': details.get('city'),
            'state': details.get('state'),
            'country': details.get('country'),
            'last_update_date': details.get('last_update_date'),
            'search_term': 'test_augusto_sampaio',
            'projects': projects
        }
        
        scraper.save_researcher(researcher_data)
        print("✅ Dados salvos no banco!")
        print()
        
        # Verify database contents
        print("🔍 Verificando banco de dados...")
        conn = sqlite3.connect('cnpq_researchers.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM researchers WHERE cnpq_id = ?", (cnpq_id,))
        researcher_row = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) FROM projects WHERE cnpq_id = ?", (cnpq_id,))
        project_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM projects WHERE cnpq_id = ? AND is_formal_methods_related = 1", (cnpq_id,))
        fm_project_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"   Pesquisador no DB: {'✅' if researcher_row else '❌'}")
        print(f"   Projetos no DB: {project_count}")
        print(f"   Projetos FM no DB: {fm_project_count}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        scraper.close()

def main():
    """Main test function"""
    print("🧪 TESTE ESPECÍFICO - AUGUSTO SAMPAIO")
    print("Verificando se o scraper consegue extrair projetos corretamente")
    print()
    
    success = test_augusto_sampaio()
    
    print("=" * 70)
    if success:
        print("🎉 TESTE CONCLUÍDO!")
        print("Verifique os resultados acima para avaliar a qualidade da extração.")
    else:
        print("❌ TESTE FALHOU!")
        print("Verifique os logs de erro acima.")
    
    print()
    print("💡 Próximos passos:")
    print("   - Se nenhum projeto foi encontrado, pode ser necessário quebrar o reCaptcha")
    print("   - Se alguns projetos foram encontrados mas estão incompletos, ajustar parsing")
    print("   - Se tudo funcionou, pode executar o scraper completo")

if __name__ == "__main__":
    main() 