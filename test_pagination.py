#!/usr/bin/env python3
"""
Test script for the new pagination system
Tests that we can find ALL available researchers for a search term
"""

from main import CNPqScraper

def test_pagination():
    """Test the new pagination system"""
    
    print("🧪 Testing Enhanced Pagination System")
    print("=" * 50)
    
    scraper = CNPqScraper(max_workers=1)
    
    try:
        # Test with a common term that should have many results
        search_term = "métodos formais"
        
        print(f"\n🔍 Testing search term: '{search_term}'")
        print("This will show the difference between limited and unlimited pagination")
        print()
        
        # Test 1: Limited to 3 pages
        print("📋 TEST 1: Limited to 3 pages")
        print("-" * 30)
        researchers_limited = scraper.search_researchers(search_term, max_pages=3)
        print(f"✅ Found {len(researchers_limited)} researchers (limited to 3 pages)")
        print()
        
        # Test 2: No limit (fetch all pages)
        print("📋 TEST 2: No limit (fetch ALL pages)")
        print("-" * 30)
        researchers_unlimited = scraper.search_researchers(search_term, max_pages=None)
        print(f"✅ Found {len(researchers_unlimited)} researchers (no limit)")
        print()
        
        # Show the difference
        difference = len(researchers_unlimited) - len(researchers_limited)
        print("📊 COMPARISON:")
        print(f"   Limited (3 pages): {len(researchers_limited)} researchers")
        print(f"   Unlimited (all):   {len(researchers_unlimited)} researchers")
        if len(researchers_limited) > 0:
            print(f"   Difference:        +{difference} researchers ({difference/len(researchers_limited)*100:.1f}% more)")
        else:
            print(f"   Difference:        +{difference} researchers")
        print()
        
        if difference > 0:
            print("🎉 SUCCESS: The pagination fix is working!")
            print(f"   We found {difference} additional researchers that would have been missed!")
        elif len(researchers_unlimited) == 0:
            print("❓ No researchers found - this might indicate a parsing issue")
            print("   Let's try a different search term...")
            
            # Try a simpler, more common term
            backup_term = "software"
            print(f"\n🔄 Trying backup term: '{backup_term}'")
            backup_researchers = scraper.search_researchers(backup_term, max_pages=2)
            print(f"✅ Found {len(backup_researchers)} researchers with '{backup_term}'")
            
            if len(backup_researchers) > 0:
                print("✅ Parsing works - the original term might be too specific")
                researchers_unlimited = backup_researchers  # Use for database test
            else:
                print("⚠️ Still no results - there might be a parsing issue to investigate")
        else:
            print("⚠️ No difference found - either there are only 3 pages or something went wrong")
        
        print()
        print("💾 Saving a sample to the database to test the full pipeline...")
        
        # Save the first few researchers to test the database functionality
        sample_researchers = researchers_unlimited[:5] if researchers_unlimited else []
        for researcher in sample_researchers:
            scraper.save_researcher(researcher)
        
        print(f"✅ Saved {len(sample_researchers)} sample researchers to database")
        
    except Exception as e:
        print(f"❌ Error during pagination test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == "__main__":
    test_pagination() 