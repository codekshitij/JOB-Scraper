#!/usr/bin/env python3
"""
Test script for debugging individual company configurations
Usage: python test_single_company.py Microsoft
"""

import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Import our scraper
try:
    from scraper import EnhancedJobScraper
except ImportError:
    print("❌ Error: scraper.py not found in current directory")
    print("Make sure you're running this from the same directory as scraper.py")
    sys.exit(1)

# Configure logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'test_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def print_separator(title: str):
    """Print a formatted separator"""
    print(f"\n{'='*60}")
    print(f"{title:^60}")
    print(f"{'='*60}")

def print_job_details(job: dict, index: int):
    """Print detailed job information"""
    print(f"\n{index:2d}. 🎯 {job['title']}")
    print(f"    🏢 Company: {job['company']}")
    print(f"    📍 Location: {job['location']}")
    print(f"    🛠️  Scraping Method: {job.get('scraping_method', 'unknown')}")
    print(f"    📅 Posted: {job.get('posted_date', 'unknown')}")
    print(f"    🏷️  Department: {job.get('department', 'N/A')}")
    print(f"    💼 Job Type: {job.get('job_type', 'N/A')}")
    print(f"    🔗 URL: {job['url']}")
    print(f"    🆔 Job ID: {job['job_id']}")

def analyze_company_config(company_name: str, config: dict):
    """Analyze and display company configuration"""
    print_separator(f"CONFIGURATION ANALYSIS: {company_name}")
    
    print(f"📋 Basic Configuration:")
    print(f"   • Enabled: {config.get('enabled', True)}")
    print(f"   • Scraping Method: {config.get('scraping_method', 'requests')}")
    print(f"   • Careers URL: {config.get('careers_url', 'NOT SET')}")
    
    # Search parameters
    search_params = config.get('search_params', {})
    if search_params:
        print(f"\n🔍 Search Parameters:")
        for key, value in search_params.items():
            print(f"   • {key}: {value}")
    else:
        print(f"\n⚠️  No search parameters configured")
    
    # Selectors
    selectors = config.get('selectors', {})
    if selectors:
        print(f"\n🎯 CSS Selectors:")
        for key, value in selectors.items():
            print(f"   • {key}: {value}")
    else:
        print(f"\n❌ No selectors configured!")
    
    # Selenium configuration
    selenium_config = config.get('selenium_config', {})
    if selenium_config:
        print(f"\n🚀 Selenium Configuration:")
        
        # Search steps
        search_steps = selenium_config.get('search_steps', [])
        if search_steps:
            print(f"   📝 Search Steps ({len(search_steps)} steps):")
            for i, step in enumerate(search_steps, 1):
                action = step.get('action', 'unknown')
                selector = step.get('selector', 'unknown')
                value = step.get('value', '')
                wait = step.get('wait', 0)
                print(f"      {i}. {action.upper()}: {selector}")
                if value:
                    print(f"         Value: '{value}'")
                if wait:
                    print(f"         Wait: {wait}s")
        
        # Dynamic loading
        dynamic_loading = selenium_config.get('dynamic_loading', {})
        if dynamic_loading:
            print(f"   🔄 Dynamic Loading:")
            if dynamic_loading.get('infinite_scroll'):
                print(f"      • Infinite Scroll: {dynamic_loading.get('max_scrolls', 5)} max scrolls")
            if dynamic_loading.get('load_more_button'):
                print(f"      • Load More Button: {dynamic_loading.get('button_selector', 'unknown')}")
    else:
        print(f"\n📝 No Selenium configuration (using basic scraping)")

def test_cs_filtering(scraper: EnhancedJobScraper):
    """Test the CS filtering functionality"""
    print_separator("CS FILTERING TEST")
    
    test_jobs = [
        ("Software Engineer - New Grad", True, "Perfect match"),
        ("Backend Developer - Entry Level", True, "CS role, entry level"),
        ("Data Scientist - Recent Graduate", True, "CS role, recent grad"),
        ("Machine Learning Engineer - University Hire", True, "CS role, university hire"),
        ("Frontend Developer - Junior", True, "CS role, junior level"),
        ("Marketing Manager - New Grad", False, "Non-CS role"),
        ("Senior Software Engineer", False, "Senior role (not new grad)"),
        ("Software Engineering Intern", False, "Internship (not full-time)"),
        ("Sales Representative - Entry Level", False, "Non-CS role"),
        ("Product Manager - New Grad", True, "CS-adjacent role"),
        ("Technical Writer - Recent Graduate", True, "Technical role"),
        ("Graphic Designer - Entry Level", False, "Non-CS creative role"),
        ("DevOps Engineer - Junior", True, "CS infrastructure role"),
        ("Cybersecurity Analyst - New Grad", True, "CS security role"),
        ("Business Analyst", False, "Business role (not clearly CS)"),
    ]
    
    print("🧪 Testing CS relevance detection:")
    print("   ✅ = Should be included (CS + New Grad)")
    print("   ❌ = Should be excluded")
    print()
    
    correct_predictions = 0
    total_tests = len(test_jobs)
    
    for title, expected, reason in test_jobs:
        result = scraper.is_relevant_job(title)
        is_correct = result == expected
        
        if is_correct:
            correct_predictions += 1
            status = "✅" if expected else "❌"
        else:
            status = "🔄"  # Incorrect prediction
        
        print(f"   {status} '{title}'")
        print(f"      Expected: {expected}, Got: {result} ({reason})")
        if not is_correct:
            print(f"      ⚠️  INCORRECT PREDICTION!")
        print()
    
    accuracy = (correct_predictions / total_tests) * 100
    print(f"🎯 Filtering Accuracy: {correct_predictions}/{total_tests} ({accuracy:.1f}%)")
    
    if accuracy < 80:
        print("⚠️  Warning: Low accuracy! Consider tuning the filtering logic.")
    elif accuracy >= 90:
        print("🎉 Excellent filtering accuracy!")
    else:
        print("👍 Good filtering accuracy.")

def test_company(company_name: str, verbose: bool = False, save_results: bool = False):
    """Test scraping for a single company"""
    
    print_separator(f"TESTING COMPANY: {company_name}")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize scraper
    try:
        scraper = EnhancedJobScraper()
        print(f"✅ Scraper initialized successfully")
        print(f"   • 🌐 Requests session: Ready")
        print(f"   • 🚀 Selenium driver: {'Ready' if scraper.driver else 'Not available'}")
        print(f"   • 📋 Total companies configured: {len(scraper.companies)}")
    except Exception as e:
        print(f"❌ Failed to initialize scraper: {e}")
        return False
    
    try:
        # Check if company exists
        if company_name not in scraper.companies:
            print(f"❌ Company '{company_name}' not found in configuration")
            print(f"\n📋 Available companies:")
            
            available_companies = list(scraper.companies.keys())
            for i, company in enumerate(available_companies, 1):
                enabled = scraper.companies[company].get('enabled', True)
                status = "✅" if enabled else "❌"
                print(f"   {i:2d}. {status} {company}")
                
                if i >= 20:  # Limit output
                    remaining = len(available_companies) - 20
                    if remaining > 0:
                        print(f"   ... and {remaining} more companies")
                    break
            
            return False
        
        company_config = scraper.companies[company_name]
        
        # Analyze configuration
        if verbose:
            analyze_company_config(company_name, company_config)
            
            # Test CS filtering
            test_cs_filtering(scraper)
        
        # Check if company is enabled
        if not company_config.get('enabled', True):
            print(f"⚠️  Company '{company_name}' is disabled in configuration")
            print(f"   Set 'enabled': true in companies_config.json to enable")
            return False
        
        # Run scraping test
        print_separator(f"SCRAPING TEST: {company_name}")
        print(f"🚀 Starting scrape test...")
        
        start_time = time.time()
        jobs: List[Dict[str, Any]] = scraper.scrape_company(company_name, company_config)
        end_time = time.time()
        
        scrape_duration = end_time - start_time
        
        # Display results
        print_separator("RESULTS")
        print(f"⏱️  Scraping completed in {scrape_duration:.2f} seconds")
        print(f"📊 Total jobs found: {len(jobs)}")
        
        if jobs:
            print(f"🎯 Jobs that passed CS + New Grad filters:")
            
            # Group jobs by scraping method
            method_counts = {}
            for job in jobs:
                method = job.get('scraping_method', 'unknown')  # type: ignore
                method_counts[method] = method_counts.get(method, 0) + 1
            
            print(f"📈 Jobs by method: {dict(method_counts)}")
            print()
            
            # Show detailed job information
            display_limit = 10 if verbose else 5
            for i, job in enumerate(jobs[:display_limit], 1):
                print_job_details(job, i)
            
            if len(jobs) > display_limit:
                remaining = len(jobs) - display_limit
                print(f"\n... and {remaining} more jobs")
                
                if verbose:
                    show_all = input(f"\n🔍 Show all {len(jobs)} jobs? (y/N): ").lower().strip()
                    if show_all == 'y':
                        for i, job in enumerate(jobs[display_limit:], display_limit + 1):
                            print_job_details(job, i)
            
            # Save results if requested
            if save_results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"test_results_{company_name}_{timestamp}.json"
                
                test_results = {
                    "company": company_name,
                    "test_timestamp": datetime.now().isoformat(),
                    "scraping_duration_seconds": scrape_duration,
                    "total_jobs_found": len(jobs),
                    "scraping_method_used": company_config.get('scraping_method', 'requests'),
                    "selenium_available": scraper.driver is not None,
                    "jobs": jobs
                }
                
                with open(filename, 'w') as f:
                    json.dump(test_results, f, indent=2, default=str)
                
                print(f"\n💾 Results saved to: {filename}")
        
        else:
            print(f"❌ No CS new grad jobs found")
            print(f"\n🔍 Possible issues:")
            print(f"   • Website structure may have changed")
            print(f"   • CSS selectors need updating")
            print(f"   • Search parameters not working")
            print(f"   • JavaScript content not loading properly")
            print(f"   • Rate limiting or IP blocking")
            print(f"   • Company has no current new grad openings")
            
            print(f"\n💡 Debugging suggestions:")
            print(f"   • Check the careers page manually: {company_config.get('careers_url', 'N/A')}")
            print(f"   • Run with verbose mode: python test_single_company.py {company_name} --verbose")
            print(f"   • Use selector finder: python selector_finder.py {company_config.get('careers_url', '')}")
            print(f"   • Check debug log: test_debug_*.log")
        
        return len(jobs) > 0
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Test interrupted by user")
        return False
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        logger.exception("Detailed error information:")
        return False
        
    finally:
        # Always cleanup
        try:
            scraper.cleanup()
            print(f"🧹 Cleanup completed")
        except:
            pass

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python test_single_company.py <company_name> [options]")
        print()
        print("Examples:")
        print("  python test_single_company.py Microsoft")
        print("  python test_single_company.py Google --verbose")
        print("  python test_single_company.py Amazon --save-results")
        print("  python test_single_company.py Meta --verbose --save-results")
        print()
        print("Options:")
        print("  --verbose       Show detailed configuration analysis and filtering tests")
        print("  --save-results  Save test results to JSON file")
        sys.exit(1)
    
    company_name = sys.argv[1]
    verbose = '--verbose' in sys.argv
    save_results = '--save-results' in sys.argv
    
    success = test_company(company_name, verbose=verbose, save_results=save_results)
    
    if success:
        print(f"\n🎉 Test completed successfully!")
        print(f"✅ {company_name} is working correctly")
    else:
        print(f"\n⚠️  Test completed with issues")
        print(f"❌ {company_name} needs configuration updates")
        sys.exit(1)

if __name__ == "__main__":
    main()