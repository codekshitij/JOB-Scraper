#!/usr/bin/env python3
"""
Selector Finder - Helper script to analyze career pages and find CSS selectors
Usage: python selector_finder.py https://careers.company.com
"""

import sys
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from urllib.parse import urljoin, urlparse
from collections import Counter
from typing import Optional
import json

def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"{title:^80}")
    print(f"{'='*80}")

def print_section(title: str):
    """Print formatted section"""
    print(f"\n{'-'*60}")
    print(f"🔍 {title}")
    print(f"{'-'*60}")

def analyze_with_requests(url: str):
    """Analyze webpage using requests + BeautifulSoup"""
    print_section("REQUESTS + BEAUTIFULSOUP ANALYSIS")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"📡 Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        print(f"✅ Response: {response.status_code}")
        print(f"📄 Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"📏 Content Length: {len(response.content):,} bytes")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Analyze page structure
        print(f"\n📊 Page Structure:")
        print(f"   • Title: {soup.title.string if soup.title else 'No title'}")
        print(f"   • Total elements: {len(soup.find_all())}")
        print(f"   • Links: {len(soup.find_all('a'))}")
        print(f"   • Forms: {len(soup.find_all('form'))}")
        print(f"   • Tables: {len(soup.find_all('table'))}")
        print(f"   • Lists: {len(soup.find_all(['ul', 'ol']))}")
        
        # Look for job containers
        job_containers = find_job_containers_requests(soup)
        
        if job_containers:
            print(f"\n🎯 POTENTIAL JOB CONTAINERS FOUND:")
            for selector, count, confidence in job_containers[:8]:
                confidence_emoji = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🔴"
                print(f"   {confidence_emoji} {selector}: {count} elements (confidence: {confidence:.2f})")
            
            # Analyze best container
            best_selector = job_containers[0][0]
            analyze_job_container_requests(soup, best_selector)
        else:
            print(f"\n❌ No obvious job containers found")
            print(f"💡 This might be a JavaScript-heavy site - try Selenium analysis")
            
        # Look for search functionality
        find_search_elements_requests(soup)
        
        return job_containers
        
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return []
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return []

def find_job_containers_requests(soup: BeautifulSoup):
    """Find potential job container selectors using requests"""
    
    # Common job container patterns
    container_patterns = [
        # Class-based selectors
        '.job', '.job-item', '.job-card', '.job-posting', '.job-result', '.job-listing',
        '.position', '.opening', '.career-item', '.listing', '.vacancy',
        '.search-result', '.result-item', '.posting', '.opportunity',
        
        # Data attribute selectors
        '[data-job-id]', '[data-testid*="job"]', '[data-automation-id*="job"]',
        '[data-position-id]', '[data-listing-id]',
        
        # Generic containers that might contain jobs
        '.row', '.item', '.card', '.entry', '.record',
        'tr', 'li', '.tile', '.box',
        
        # Framework-specific
        '.react-job-item', '.vue-job-card', '.angular-position'
    ]
    
    potential_containers = []
    
    for pattern in container_patterns:
        try:
            elements = soup.select(pattern)
            count = len(elements)
            
            # Skip if too few or too many elements
            if count < 2 or count > 100:
                continue
            
            # Calculate confidence score
            confidence = calculate_confidence_requests(elements, pattern)
            
            if confidence > 0.3:  # Only include if some confidence
                potential_containers.append((pattern, count, confidence))
                
        except Exception:
            continue
    
    # Sort by confidence score
    return sorted(potential_containers, key=lambda x: x[2], reverse=True)

def calculate_confidence_requests(elements, selector):
    """Calculate confidence that these elements are job containers"""
    if not elements:
        return 0.0
    
    confidence = 0.0
    sample_size = min(5, len(elements))
    
    for element in elements[:sample_size]:
        element_confidence = 0.0
        text = element.get_text().lower()
        
        # Check for job-related keywords in text
        job_keywords = [
            'engineer', 'developer', 'analyst', 'manager', 'coordinator',
            'specialist', 'associate', 'director', 'lead', 'senior',
            'junior', 'intern', 'new grad', 'entry level', 'remote',
            'full-time', 'part-time', 'contract', 'temporary'
        ]
        
        keyword_count = sum(1 for keyword in job_keywords if keyword in text)
        element_confidence += keyword_count * 0.1
        
        # Check for links (job titles are usually links)
        links = element.find_all('a')
        if links:
            element_confidence += 0.3
        
        # Check for location indicators
        location_indicators = ['location', 'city', 'state', 'country', 'remote']
        if any(indicator in text for indicator in location_indicators):
            element_confidence += 0.2
        
        # Check for date indicators
        date_patterns = [r'\d{1,2}/\d{1,2}/\d{4}', r'\d{1,2}-\d{1,2}-\d{4}', 
                        r'posted', r'updated', r'days ago', r'weeks ago']
        if any(re.search(pattern, text) for pattern in date_patterns):
            element_confidence += 0.2
        
        # Bonus for job-specific selectors
        if 'job' in selector.lower():
            element_confidence += 0.3
        
        confidence += element_confidence
    
    return min(confidence / sample_size, 1.0)

def analyze_job_container_requests(soup: BeautifulSoup, container_selector: str):
    """Analyze the best job container to find sub-selectors"""
    print_section(f"ANALYZING CONTAINER: {container_selector}")
    
    containers = soup.select(container_selector)
    if not containers:
        return
    
    print(f"📦 Found {len(containers)} containers")
    
    # Analyze first few containers
    sample_containers = containers[:3]
    
    for i, container in enumerate(sample_containers, 1):
        print(f"\n🔍 Container {i} Analysis:")
        
        # Find potential title selectors
        title_selectors = find_title_selectors(container)
        if title_selectors:
            print(f"   📝 Title selectors:")
            for selector, text in title_selectors[:3]:
                print(f"      • {selector}: '{text[:50]}...'")
        
        # Find potential location selectors
        location_selectors = find_location_selectors(container)
        if location_selectors:
            print(f"   📍 Location selectors:")
            for selector, text in location_selectors[:3]:
                print(f"      • {selector}: '{text[:30]}...'")
        
        # Find links (potential job URLs)
        links = container.find_all('a', href=True)
        if links:
            print(f"   🔗 Found {len(links)} links:")
            for link in links[:2]:
                href = link.get('href', '')
                text = link.get_text(strip=True)[:40]
                print(f"      • a: '{text}...' -> {href[:50]}...")

def find_title_selectors(container):
    """Find potential job title selectors in a container"""
    title_candidates = []
    
    # Check various elements that could be titles
    title_elements = [
        ('a', container.find_all('a')),
        ('h1', container.find_all('h1')),
        ('h2', container.find_all('h2')),
        ('h3', container.find_all('h3')),
        ('h4', container.find_all('h4')),
        ('.title', container.select('.title')),
        ('.job-title', container.select('.job-title')),
        ('.position-title', container.select('.position-title')),
        ('[data-testid*="title"]', container.select('[data-testid*="title"]')),
        ('[data-automation-id*="title"]', container.select('[data-automation-id*="title"]')),
    ]
    
    for selector, elements in title_elements:
        for element in elements:
            text = element.get_text(strip=True)
            if text and len(text) > 5 and len(text) < 150:  # Reasonable title length
                title_candidates.append((selector, text))
    
    return title_candidates

def find_location_selectors(container):
    """Find potential location selectors in a container"""
    location_candidates = []
    
    # Look for location-related selectors
    location_elements = [
        ('.location', container.select('.location')),
        ('.job-location', container.select('.job-location')),
        ('.position-location', container.select('.position-location')),
        ('[data-testid*="location"]', container.select('[data-testid*="location"]')),
        ('[class*="location"]', container.select('[class*="location"]')),
    ]
    
    for selector, elements in location_elements:
        for element in elements:
            text = element.get_text(strip=True)
            if text and is_location_text(text):
                location_candidates.append((selector, text))
    
    # Also check for text that looks like locations
    all_text_elements = container.find_all(text=True)
    for text in all_text_elements:
        text = text.strip()
        if is_location_text(text):
            parent = text.parent
            if parent and parent.name:
                selector = parent.name
                if parent.get('class'):
                    selector += '.' + '.'.join(parent.get('class'))
                location_candidates.append((selector, text))
    
    return location_candidates

def is_location_text(text: str) -> bool:
    """Check if text looks like a location"""
    if not text or len(text) < 2 or len(text) > 100:
        return False
    
    location_patterns = [
        r'\b[A-Z][a-z]+,\s*[A-Z]{2}\b',  # City, ST
        r'\b[A-Z][a-z]+,\s*[A-Z][a-z]+\b',  # City, Country
        r'\bRemote\b',
        r'\b(San Francisco|New York|Seattle|Austin|Boston|Chicago|Los Angeles|Washington|Denver|Atlanta)\b',
        r'\b(USA|US|United States|Canada|UK|Remote)\b'
    ]
    
    return any(re.search(pattern, text) for pattern in location_patterns)

def find_search_elements_requests(soup: BeautifulSoup):
    """Find search functionality on the page"""
    print_section("SEARCH FUNCTIONALITY ANALYSIS")
    
    # Find search inputs
    search_inputs = soup.find_all('input', {'type': 'search'})
    search_inputs.extend(soup.find_all('input', {'placeholder': re.compile(r'search', re.I)}))
    search_inputs.extend(soup.find_all('input', {'name': re.compile(r'search', re.I)}))
    search_inputs.extend(soup.find_all('input', {'id': re.compile(r'search', re.I)}))
    
    if search_inputs:
        print(f"🔍 Found {len(search_inputs)} search inputs:")
        for i, inp in enumerate(search_inputs, 1):
            placeholder = inp.get('placeholder', '')
            name = inp.get('name', '')
            id_attr = inp.get('id', '')
            input_type = inp.get('type', 'text')
            
            print(f"   {i}. Input:")
            print(f"      • Type: {input_type}")
            print(f"      • Placeholder: '{placeholder}'")
            print(f"      • Name: '{name}'")
            print(f"      • ID: '{id_attr}'")
            
            # Suggest selector
            if id_attr:
                print(f"      • Suggested selector: #{id_attr}")
            elif name:
                print(f"      • Suggested selector: input[name='{name}']")
            else:
                print(f"      • Suggested selector: input[type='{input_type}']")
    else:
        print(f"❌ No search inputs found")
    
    # Find search buttons
    search_buttons = soup.find_all('button', string=re.compile(r'search', re.I))
    search_buttons.extend(soup.find_all('input', {'type': 'submit', 'value': re.compile(r'search', re.I)}))
    
    if search_buttons:
        print(f"\n🔘 Found {len(search_buttons)} search buttons:")
        for i, btn in enumerate(search_buttons, 1):
            text = btn.get_text(strip=True) or btn.get('value', '')
            btn_type = btn.get('type', btn.name)
            btn_class = ' '.join(btn.get('class', []))
            
            print(f"   {i}. Button: '{text}' (type: {btn_type})")
            if btn_class:
                print(f"      • Class: {btn_class}")
                print(f"      • Suggested selector: .{btn_class.replace(' ', '.')}")

def analyze_with_selenium(url: str):
    """Analyze webpage using Selenium for JavaScript content"""
    print_section("SELENIUM ANALYSIS (JavaScript Content)")
    
    driver = None
    try:
        # Setup Chrome driver
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        print(f"🚀 Starting Chrome driver...")
        driver = webdriver.Chrome(options=chrome_options)
        
        print(f"📡 Loading: {url}")
        driver.get(url)
        
        # Wait for initial load
        time.sleep(3)
        
        print(f"✅ Page loaded successfully")
        print(f"📏 Page title: {driver.title}")
        print(f"🔗 Current URL: {driver.current_url}")
        
        # Wait a bit more for dynamic content
        print(f"⏳ Waiting for dynamic content...")
        time.sleep(5)
        
        # Look for job containers
        job_containers = find_job_containers_selenium(driver)
        
        if job_containers:
            print(f"\n🎯 POTENTIAL JOB CONTAINERS FOUND:")
            for selector, count, sample_text in job_containers[:8]:
                print(f"   • {selector}: {count} elements")
                print(f"     Sample: '{sample_text[:60]}...'")
            
            # Analyze best container
            best_selector = job_containers[0][0]
            analyze_job_container_selenium(driver, best_selector)
        else:
            print(f"\n❌ No obvious job containers found with Selenium")
            print(f"💡 Try scrolling or interacting with the page")
        
        # Look for search functionality
        find_search_elements_selenium(driver)
        
        # Test dynamic loading
        test_dynamic_loading(driver)
        
        return job_containers
        
    except Exception as e:
        print(f"❌ Selenium analysis failed: {e}")
        return []
        
    finally:
        if driver:
            print(f"🧹 Closing browser...")
            driver.quit()

def find_job_containers_selenium(driver):
    """Find potential job containers using Selenium"""
    container_patterns = [
        '.job', '.job-item', '.job-card', '.job-posting', '.job-result', '.job-listing',
        '.position', '.opening', '.career-item', '.listing', '.vacancy',
        '.search-result', '.result-item', '.posting', '.opportunity',
        '[data-job-id]', '[data-testid*="job"]', '[data-automation-id*="job"]',
        '[data-position-id]', '[data-listing-id]',
        '.row', '.item', '.card', '.entry', '.record', 'tr', 'li'
    ]
    
    potential_containers = []
    
    for pattern in container_patterns:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, pattern)
            count = len(elements)
            
            if 2 <= count <= 100:  # Reasonable range
                # Get sample text from first element
                sample_text = ""
                if elements:
                    try:
                        sample_text = elements[0].text[:100]
                    except Exception:
                        sample_text = "Unable to get text"
                
                # Simple scoring based on pattern and count
                score = calculate_confidence_selenium(elements, pattern)
                
                if score > 0.3:
                    potential_containers.append((pattern, count, sample_text))
                    
        except Exception:
            continue
    
    # Sort by count (more elements might be better for job listings)
    return sorted(potential_containers, key=lambda x: x[1], reverse=True)

def calculate_confidence_selenium(elements, selector):
    """Calculate confidence for Selenium elements"""
    if not elements:
        return 0.0
    
    confidence = 0.0
    sample_size = min(3, len(elements))
    
    for element in elements[:sample_size]:
        try:
            text = element.text.lower()
            
            # Job-related keywords
            job_keywords = ['engineer', 'developer', 'manager', 'analyst', 'remote', 'full-time']
            keyword_score = sum(1 for keyword in job_keywords if keyword in text) * 0.15
            
            # Links within element
            links = element.find_elements(By.TAG_NAME, "a")
            link_score = 0.3 if links else 0
            
            # Job selector bonus
            selector_score = 0.4 if 'job' in selector.lower() else 0
            
            confidence += keyword_score + link_score + selector_score
            
        except Exception:
            continue
    
    return min(confidence / sample_size, 1.0)

def analyze_job_container_selenium(driver, container_selector: str):
    """Analyze job container using Selenium"""
    print_section(f"SELENIUM CONTAINER ANALYSIS: {container_selector}")
    
    try:
        containers = driver.find_elements(By.CSS_SELECTOR, container_selector)
        print(f"📦 Found {len(containers)} containers")
        
        # Analyze first container
        if containers:
            container = containers[0]
            
            # Find title elements
            title_elements = container.find_elements(By.TAG_NAME, "a")
            title_elements.extend(container.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4"))
            title_elements.extend(container.find_elements(By.CSS_SELECTOR, "[class*='title']"))
            
            if title_elements:
                print(f"   📝 Potential titles:")
                for elem in title_elements[:3]:
                    try:
                        text = elem.text.strip()
                        tag = elem.tag_name
                        class_attr = elem.get_attribute('class') or ''
                        
                        if text and len(text) > 5:
                            selector = tag
                            if class_attr:
                                selector += f".{class_attr.replace(' ', '.')}"
                            print(f"      • {selector}: '{text[:50]}...'")
                    except Exception:
                        continue
            
            # Find location elements
            location_elements = container.find_elements(By.CSS_SELECTOR, "[class*='location']")
            if location_elements:
                print(f"   📍 Potential locations:")
                for elem in location_elements[:3]:
                    try:
                        text = elem.text.strip()
                        class_attr = elem.get_attribute('class') or ''
                        if text:
                            print(f"      • .{class_attr.replace(' ', '.')}: '{text}'")
                    except Exception:
                        continue
                        
    except Exception as e:
        print(f"❌ Container analysis failed: {e}")

def find_search_elements_selenium(driver):
    """Find search elements using Selenium"""
    print_section("SELENIUM SEARCH ANALYSIS")
    
    try:
        # Find search inputs
        search_selectors = [
            "input[type='search']",
            "input[placeholder*='search' i]",
            "input[name*='search' i]",
            "input[id*='search' i]",
            ".search-input",
            "#search"
        ]
        
        search_inputs = []
        for selector in search_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                search_inputs.extend(elements)
            except Exception:
                continue
        
        if search_inputs:
            print(f"🔍 Found {len(search_inputs)} search inputs:")
            for i, inp in enumerate(search_inputs[:5], 1):
                try:
                    placeholder = inp.get_attribute('placeholder') or ''
                    name = inp.get_attribute('name') or ''
                    id_attr = inp.get_attribute('id') or ''
                    
                    print(f"   {i}. Input:")
                    print(f"      • Placeholder: '{placeholder}'")
                    print(f"      • Name: '{name}'")
                    print(f"      • ID: '{id_attr}'")
                    
                    if id_attr:
                        print(f"      • Selector: #{id_attr}")
                    elif name:
                        print(f"      • Selector: input[name='{name}']")
                except:
                    continue
        
        # Find search buttons
        button_selectors = [
            "button[type='submit']",
            ".search-button",
            ".btn-search",
            "input[type='submit']"
        ]
        
        search_buttons = []
        for selector in button_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                search_buttons.extend(elements)
            except:
                continue
        
        if search_buttons:
            print(f"\n🔘 Found {len(search_buttons)} potential search buttons:")
            for i, btn in enumerate(search_buttons[:3], 1):
                try:
                    text = btn.text or btn.get_attribute('value') or ''
                    class_attr = btn.get_attribute('class') or ''
                    
                    print(f"   {i}. Button: '{text}'")
                    if class_attr:
                        print(f"      • Class: {class_attr}")
                        print(f"      • Selector: .{class_attr.replace(' ', '.')}")
                except:
                    continue
                    
    except Exception as e:
        print(f"❌ Search analysis failed: {e}")

def test_dynamic_loading(driver):
    """Test for dynamic loading features"""
    print_section("DYNAMIC LOADING TEST")
    
    # Test scrolling
    try:
        initial_height = driver.execute_script("return document.body.scrollHeight")
        print(f"📏 Initial page height: {initial_height}px")
        
        # Scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        print(f"📏 Height after scroll: {new_height}px")
        
        if new_height > initial_height:
            print(f"✅ Infinite scroll detected! (+{new_height - initial_height}px)")
        else:
            print(f"❌ No infinite scroll detected")
            
    except Exception as e:
        print(f"⚠️ Scroll test failed: {e}")
    
    # Look for "Load More" buttons
    try:
        load_more_selectors = [
            "button:contains('Load More')",
            "button:contains('Show More')",
            ".load-more",
            ".show-more",
            "[data-automation-id*='loadMore']"
        ]
        
        load_more_buttons = []
        for selector in load_more_selectors:
            try:
                # Use XPath for text-based selection
                if 'contains' in selector:
                    xpath = f"//button[contains(text(), '{'Load More' if 'Load More' in selector else 'Show More'}')]"
                    elements = driver.find_elements(By.XPATH, xpath)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                load_more_buttons.extend(elements)
            except:
                continue
        
        if load_more_buttons:
            print(f"🔄 Found {len(load_more_buttons)} 'Load More' buttons:")
            for i, btn in enumerate(load_more_buttons[:3], 1):
                try:
                    text = btn.text or 'No text'
                    class_attr = btn.get_attribute('class') or ''
                    print(f"   {i}. Button: '{text}'")
                    if class_attr:
                        print(f"      • Selector: .{class_attr.replace(' ', '.')}")
                except:
                    continue
        else:
            print(f"❌ No 'Load More' buttons found")
            
    except Exception as e:
        print(f"⚠️ Load More test failed: {e}")

def generate_config_template(url: str, requests_containers: list, selenium_containers: Optional[list]):
    """Generate configuration template based on analysis"""
    print_section("CONFIGURATION TEMPLATE")
    
    # Extract company name from URL
    domain = urlparse(url).netloc
    company_name = domain.replace('www.', '').replace('careers.', '').split('.')[0].title()
    
    # Determine best method
    method = "selenium" if selenium_containers and not requests_containers else "requests"
    if selenium_containers and requests_containers:
        method = "selenium"  # Prefer selenium if both work
    
    # Get best container
    best_container = None
    if method == "selenium" and selenium_containers:
        best_container = selenium_containers[0][0]
    elif requests_containers:
        best_container = requests_containers[0][0]
    
    config = {
        company_name: {
            "enabled": True,
            "scraping_method": method,
            "careers_url": url,
            "search_params": {
                "q": "software engineer new grad"
            },
            "selectors": {
                "job_container": best_container or ".job-item",
                "title": ".job-title",  # UPDATE THIS
                "location": ".job-location",  # UPDATE THIS
                "url": "a"  # UPDATE THIS
            }
        }
    }
    
    if method == "selenium":
        config[company_name]["selenium_config"] = {
            "search_steps": [
                {
                    "action": "type",
                    "selector": "input[type='search']",  # UPDATE THIS
                    "value": "software engineer new grad",
                    "wait": 2
                },
                {
                    "action": "click",
                    "selector": "button[type='submit']",  # UPDATE THIS
                    "wait": 3
                }
            ],
            "dynamic_loading": {
                "infinite_scroll": True,
                "max_scrolls": 3,
                "scroll_pause": 2
            }
        }
    
    print(f"📝 Suggested configuration for {company_name}:")
    print(f"   • Method: {method}")
    print(f"   • Best container: {best_container}")
    print()
    print(json.dumps(config, indent=2))
    
    print(f"\n💡 Next steps:")
    print(f"   1. Add this to your companies_config.json")
    print(f"   2. Update the selectors marked with 'UPDATE THIS'")
    print(f"   3. Test with: python test_single_company.py {company_name}")
    print(f"   4. Fine-tune search steps and selectors as needed")

def main():
    if len(sys.argv) != 2:
        print("Usage: python selector_finder.py <careers_url>")
        print()
        print("Examples:")
        print("  python selector_finder.py https://careers.spotify.com")
        print("  python selector_finder.py https://jobs.netflix.com")
        print("  python selector_finder.py https://www.tesla.com/careers")
        print()
        print("This tool will:")
        print("  • Analyze the page structure")
        print("  • Find potential job container selectors") 
        print("  • Identify search functionality")
        print("  • Test for dynamic loading")
        print("  • Generate configuration template")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Validate URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    print_header(f"CAREER PAGE SELECTOR ANALYSIS")
    print(f"🎯 Target URL: {url}")
    print(f"🕐 Analysis started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Analyze with requests first
    requests_containers = analyze_with_requests(url)
    
    # Analyze with Selenium
    selenium_containers = analyze_with_selenium(url)
    
    # Generate configuration template
    generate_config_template(url, requests_containers, selenium_containers)
    
    # Summary
    print_header("ANALYSIS SUMMARY")
    
    print(f"📊 Results:")
    print(f"   • Requests found {len(requests_containers)} potential containers")
    print(f"   • Selenium found {len(selenium_containers) if selenium_containers else 0} potential containers")
    
    if requests_containers or selenium_containers:
        print(f"✅ Analysis completed successfully!")
        
        if selenium_containers and not requests_containers:
            print(f"💡 Recommendation: Use Selenium (JavaScript-heavy site)")
        elif requests_containers and not selenium_containers:
            print(f"💡 Recommendation: Use Requests (static HTML site)")
        elif both := (requests_containers and selenium_containers):
            print(f"💡 Recommendation: Try Requests first, fallback to Selenium")
        
        print(f"\n📋 Next steps:")
        print(f"   1. Copy the configuration template above")
        print(f"   2. Add it to companies_config.json")
        print(f"   3. Update the selectors marked 'UPDATE THIS'")
        print(f"   4. Test with: python test_single_company.py CompanyName")
        
    else:
        print(f"❌ No job containers found")
        print(f"\n🔍 Possible reasons:")
        print(f"   • Site requires login to view jobs")
        print(f"   • Jobs are loaded via complex JavaScript/AJAX")
        print(f"   • Site has anti-bot protection")
        print(f"   • No current job openings")
        print(f"   • Jobs are hosted on external platform")
        
        print(f"\n💡 Try these alternatives:")
        print(f"   • Check if jobs are on a different subdomain")
        print(f"   • Look for 'View All Jobs' or 'Open Positions' links")
        print(f"   • Try searching for 'new grad' or 'software engineer' on the page")
        print(f"   • Check if company uses external job board (Greenhouse, Lever, etc.)")

if __name__ == "__main__":
    main()