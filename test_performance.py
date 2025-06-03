#!/usr/bin/env python3
"""
Performance test script for the optimized CNPq scraper
Tests async pagination vs sync and batch operations vs individual saves
"""

import time
import asyncio
from main import CNPqScraper

def test_performance():
    """Test the performance improvements"""
    
    print("🏁 CNPq Scraper Performance Test")
    print("=" * 50)
    
    scraper = CNPqScraper(max_workers=8)
    
    try:
        # Test parameters
        test_term = "software"
        max_pages_test = 5  # Test with 5 pages (should be ~50 researchers)
        
        print(f"\n🧪 Testing with: '{test_term}' (limited to {max_pages_test} pages)")
        print("This will compare sync vs async page fetching performance")
        print()
        
        # Test 1: Sync version (old method)
        print("📋 TEST 1: Sync Page Fetching")
        print("-" * 30)
        start_time = time.time()
        researchers_sync = scraper.search_researchers_sync(test_term, max_pages_test)
        sync_time = time.time() - start_time
        print(f"✅ Sync: {len(researchers_sync)} researchers in {sync_time:.2f}s")
        
        # Small delay to be respectful
        time.sleep(2)
        
        # Test 2: Async version (new method)
        print("\n📋 TEST 2: Async Page Fetching")
        print("-" * 30)
        start_time = time.time()
        try:
            researchers_async = asyncio.run(
                scraper.search_researchers_async(test_term, max_pages_test, max_concurrent=8)
            )
            async_time = time.time() - start_time
            print(f"✅ Async: {len(researchers_async)} researchers in {async_time:.2f}s")
        except Exception as e:
            print(f"❌ Async test failed: {e}")
            researchers_async = researchers_sync  # Fallback
            async_time = sync_time
        
        # Performance comparison
        print("\n📊 PERFORMANCE COMPARISON:")
        print(f"   Sync time:  {sync_time:.2f}s")
        print(f"   Async time: {async_time:.2f}s")
        
        if async_time < sync_time:
            speedup = sync_time / async_time
            time_saved = sync_time - async_time
            print(f"   🚀 Speedup: {speedup:.2f}x faster ({time_saved:.2f}s saved)")
        else:
            print(f"   ⚠️ Sync was faster (async overhead for small datasets)")
        
        # Test 3: Database batch operations
        print("\n📋 TEST 3: Database Performance")
        print("-" * 30)
        
        if researchers_async:
            # Test individual saves
            print("Testing individual saves...")
            start_time = time.time()
            for i, researcher in enumerate(researchers_async[:10]):  # Test with 10 researchers
                scraper.save_researcher(researcher)
                if i == 4:  # Show progress
                    print(f"  • Saved {i+1}/10 researchers...")
            individual_time = time.time() - start_time
            
            # Test batch save
            print("Testing batch save...")
            start_time = time.time()
            scraper.save_researchers_batch(researchers_async[:10])
            batch_time = time.time() - start_time
            
            print(f"\n📊 DATABASE COMPARISON:")
            print(f"   Individual saves: {individual_time:.2f}s")
            print(f"   Batch save:       {batch_time:.2f}s")
            
            if batch_time < individual_time:
                db_speedup = individual_time / batch_time
                print(f"   🚀 Database speedup: {db_speedup:.2f}x faster")
            else:
                print(f"   ⚠️ Individual saves were faster (small dataset)")
        
        # Test 4: Projected performance for large datasets
        print("\n📋 TEST 4: Projected Performance")
        print("-" * 30)
        
        if len(researchers_async) > 0:
            # Calculate projections
            researchers_per_page = len(researchers_async) / max_pages_test
            sync_pages_per_second = max_pages_test / sync_time
            async_pages_per_second = max_pages_test / async_time
            
            # Project for 1000 pages (typical large search)
            large_pages = 1000
            sync_projection = large_pages / sync_pages_per_second
            async_projection = large_pages / async_pages_per_second
            
            print(f"📊 PROJECTIONS FOR {large_pages} PAGES:")
            print(f"   Sync projected:  {int(sync_projection//60)}:{int(sync_projection%60):02d}")
            print(f"   Async projected: {int(async_projection//60)}:{int(async_projection%60):02d}")
            
            if async_projection < sync_projection:
                time_saved_minutes = (sync_projection - async_projection) / 60
                print(f"   🚀 Time saved: {time_saved_minutes:.1f} minutes")
                print(f"   📈 Estimated {large_pages * researchers_per_page:.0f} researchers in {int(async_projection//60)}:{int(async_projection%60):02d}")
        
        print("\n🎉 Performance test completed!")
        print("💡 The async version should show significant improvements with large datasets")
        
    except Exception as e:
        print(f"❌ Error during performance test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == "__main__":
    test_performance() 