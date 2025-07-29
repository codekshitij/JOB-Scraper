#!/usr/bin/env python3
"""
Enhanced New Grad Job Scraper with Selenium Support
Architecture: Script -> JSON Config -> JSON Results -> Excel Export -> GitHub Actions
Supports both static HTML and JavaScript-rendered pages
"""

import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import logging
import time
import random
from typing import List, Dict, Optional, Union
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import argparse
from pathlib import Path
import re
from fake_useragent import UserAgent

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedJobScraper:
    def __init__(self, config_file: str = "companies_config.json"):
        self.config_file = config_file
        self.ua = UserAgent()
        
        # Initialize requests session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Initialize Selenium driver
        self.driver = None
        self._setup_selenium_driver()
        
        # Load company configurations
        self.companies = self.load_companies_config()
        
        # Results storage
        self.results: Dict[str, Union[str, int, List, Dict]] = {
            "scrape_timestamp": datetime.now().isoformat(),
            "total_companies": len(self.companies),
            "successful_scrapes": 0,
            "selenium_scrapes": 0,
            "requests_scrapes": 0,
            "total_jobs_found": 0,
            "new_grad_jobs": [],
            "errors": [],
            "scraping_stats": {}
        }

    def _setup_selenium_driver(self):
        """Setup headless Chrome driver with anti-detection measures"""
        try:
            chrome_options = Options()
            
            # Headless mode for GitHub Actions
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Anti-detection measures
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(f"--user-agent={self.ua.random}")
            
            # Performance optimizations
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-javascript") # We'll enable for specific cases
            chrome_options.add_argument("--disable-css")
            
            # Memory optimizations
            chrome_options.add_argument("--memory-pressure-off")
            chrome_options.add_argument("--max_old_space_size=4096")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Set implicit wait
            self.driver.implicitly_wait(10)
            
            logger.info("✅ Selenium Chrome driver initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Selenium driver: {e}")
            logger.warning("🔄 Falling back to requests-only mode")
            self.driver = None

    def load_companies_config(self) -> Dict:
        """Load company configurations from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"📋 Loaded {len(config)} companies from {self.config_file}")
            return config
        except FileNotFoundError:
            logger.error(f"❌ Config file {self.config_file} not found!")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {self.config_file}: {e}")
            return {}

    def is_cs_related_role(self, title: str, description: str = "") -> bool:
        """Check if the job is Computer Science related"""
        text = f"{title} {description}".lower()
        
        # Core CS job titles and keywords
        cs_keywords = [
            # Software Engineering
            "software engineer", "software developer", "swe", "backend", "frontend", 
            "full stack", "fullstack", "web developer", "mobile developer", "ios developer", 
            "android developer", "react developer", "python developer", "java developer",
            "javascript developer", ".net developer", "node.js developer",
            
            # Systems & Infrastructure
            "systems engineer", "devops", "site reliability", "sre", "cloud engineer",
            "infrastructure engineer", "platform engineer", "security engineer",
            "network engineer", "database administrator", "dba",
            
            # Data & AI/ML
            "data scientist", "data engineer", "data analyst", "machine learning", "ml engineer",
            "ai engineer", "artificial intelligence", "deep learning", "analytics engineer",
            "business intelligence", "quantitative analyst", "quant developer",
            
            # Product & Technical
            "product manager", "technical product manager", "program manager", "tpm",
            "technical program manager", "solutions engineer", "sales engineer",
            "customer engineer", "technical consultant", "implementation engineer",
            
            # Research & Specialized
            "research engineer", "research scientist", "algorithm engineer", "compiler engineer",
            "embedded software", "firmware engineer", "hardware engineer", "asic engineer",
            "computer vision", "nlp engineer", "robotics engineer", "game developer",
            
            # QA & Testing
            "qa engineer", "test engineer", "automation engineer", "quality assurance",
            "sdet", "software development engineer in test",
            
            # General CS terms
            "computer science", "cs", "engineering", "technical", "developer", "programmer"
        ]
        
        # Non-CS roles to exclude
        non_cs_keywords = [
            # Business/Marketing/Sales (unless technical)
            "marketing", "sales", "business development", "account manager", "recruiter",
            "hr", "human resources", "finance", "accounting", "legal", "operations",
            "customer service", "support specialist", "content writer", "copywriter",
            
            # Design (unless technical)
            "graphic designer", "ui designer", "ux designer", "visual designer",
            "brand designer", "marketing designer",
            
            # Other non-technical
            "project coordinator", "administrative", "receptionist", "office manager",
            "warehouse", "logistics", "supply chain", "manufacturing", "mechanical",
            "civil engineer", "chemical engineer", "biomedical", "electrical technician"
        ]
        
        # Check for CS-related keywords
        cs_score = sum(3 if keyword in title.lower() else 1 
                      for keyword in cs_keywords if keyword in text)
        
        # Check for non-CS keywords (but allow technical versions)
        non_cs_score = 0
        for keyword in non_cs_keywords:
            if keyword in text and not any(tech in text for tech in ["technical", "software", "digital", "tech"]):
                non_cs_score += 2 if keyword in title.lower() else 1
        
        return cs_score > non_cs_score and cs_score >= 1

    def is_new_grad_role(self, title: str, description: str = "") -> bool:
        """Enhanced new grad detection with better keyword matching"""
        text = f"{title} {description}".lower()
        
        # Positive indicators (stronger weight for title matches)
        new_grad_keywords = [
            "new grad", "new graduate", "university", "recent graduate",
            "entry level", "junior", "associate", "college", "campus",
            "early career", "graduate program", "rotational", "fresh graduate",
            "0-2 years", "entry-level", "grad program", "new college graduate"
        ]
        
        # Negative indicators (exclude these)
        exclude_keywords = [
            "senior", "lead", "principal", "staff", "director", "manager",
            "vp", "vice president", "intern", "internship", "co-op",
            "mid-level", "experienced", "5+ years", "minimum 3 years"
        ]
        
        # Calculate positive score (higher weight for title matches)
        positive_score = 0
        for keyword in new_grad_keywords:
            if keyword in title.lower():
                positive_score += 3  # Higher weight for title
            elif keyword in text.lower():
                positive_score += 1
        
        # Calculate negative score
        negative_score = 0
        for keyword in exclude_keywords:
            if keyword in title.lower():
                negative_score += 5  # Heavy penalty for title
            elif keyword in text.lower():
                negative_score += 1
        
        # Experience requirements check
        experience_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'minimum\s+(\d+)\s+years?',
            r'at least\s+(\d+)\s+years?',
            r'(\d+)-(\d+)\s+years?\s+experience'
        ]
        
        for pattern in experience_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    years = max(int(x) for x in match if x.isdigit())
                else:
                    years = int(match) if match.isdigit() else 0
                
                if years > 2:
                    negative_score += years * 2
        
        # Decision logic
        final_score = positive_score - negative_score
        return final_score > 0 and positive_score >= 1

    def is_relevant_job(self, title: str, description: str = "") -> bool:
        """Combined filter: must be both CS-related AND new grad role"""
        return (self.is_cs_related_role(title, description) and 
                self.is_new_grad_role(title, description))

    def extract_job_info(self, job_element, selectors: Dict, base_url: str, method: str = "requests") -> Optional[Dict]:
        """Extract job information from HTML element (works for both requests and selenium)"""
        try:
            # Handle different element types (BeautifulSoup vs Selenium WebElement)
            if method == "selenium":
                # Selenium WebElement methods
                def find_element_text(selector):
                    try:
                        elem = job_element.find_element(By.CSS_SELECTOR, selector)
                        return elem.text.strip()
                    except:
                        return ""
                
                def find_element_href(selector):
                    try:
                        elem = job_element.find_element(By.CSS_SELECTOR, selector)
                        return elem.get_attribute('href') or ""
                    except:
                        return ""
                
            else:
                # BeautifulSoup methods
                def find_element_text(selector):
                    elem = job_element.select_one(selector)
                    return elem.get_text(strip=True) if elem else ""
                
                def find_element_href(selector):
                    elem = job_element.select_one(selector)
                    return elem.get('href', '') if elem else ""
            
            # Extract title
            title = find_element_text(selectors.get("title", ""))
            if not title:
                return None
            
            # Extract location
            location = find_element_text(selectors.get("location", ""))
            if not location:
                location = "Not specified"
            
            # Extract URL
            job_url = find_element_href(selectors.get("url", "a"))
            if not job_url:
                return None
            
            # Make URL absolute
            if job_url.startswith('/'):
                job_url = base_url.rstrip('/') + job_url
            elif not job_url.startswith('http') and job_url:
                job_url = base_url.rstrip('/') + '/' + job_url.lstrip('/')
            
            # Extract additional fields if selectors provided
            department = find_element_text(selectors.get("department", ""))
            job_type = find_element_text(selectors.get("job_type", ""))
            posted_date = find_element_text(selectors.get("posted_date", ""))
            
            # Generate unique job ID
            job_id = hashlib.md5(f"{title}_{job_url}".encode()).hexdigest()
            
            return {
                "job_id": job_id,
                "title": title,
                "location": location,
                "url": job_url,
                "department": department,
                "job_type": job_type,
                "posted_date": posted_date or datetime.now().strftime("%Y-%m-%d"),
                "scraped_at": datetime.now().isoformat(),
                "scraping_method": method
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting job info: {e}")
            return None

    def scrape_with_requests(self, company_name: str, company_config: Dict) -> List[Dict]:
        """Scrape using requests + BeautifulSoup for static HTML"""
        logger.info(f"🌐 Scraping {company_name} with requests...")
        
        jobs = []
        
        try:
            # Get the careers page URL
            url = company_config.get("careers_url")
            search_params = company_config.get("search_params", {})
            
            # Add new grad search terms
            if search_params:
                for key in ["q", "query", "search", "keywords"]:
                    if key in search_params:
                        if "new grad" not in search_params[key].lower():
                            search_params[key] += " new grad"
            
            # Make request with timeout and retries
            for attempt in range(3):
                try:
                    response = self.session.get(url, params=search_params, timeout=30)
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    if attempt == 2:
                        raise
                    logger.warning(f"⚠️ Request attempt {attempt + 1} failed for {company_name}: {e}")
                    time.sleep(2)
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get job containers
            job_selector = company_config.get("selectors", {}).get("job_container")
            if not job_selector:
                logger.error(f"❌ No job_container selector provided for {company_name}")
                return jobs
            
            job_elements = soup.select(job_selector)
            logger.info(f"📄 Found {len(job_elements)} job containers for {company_name}")
            
            # Extract job information
            base_url = "/".join(url.split("/")[:3]) if url else ""
            selectors = company_config.get("selectors", {})
            
            for job_element in job_elements:
                job_info = self.extract_job_info(job_element, selectors, base_url, "requests")
                if job_info and self.is_relevant_job(job_info["title"]):
                    job_info["company"] = company_name
                    job_info["is_new_grad"] = True
                    job_info["is_cs_related"] = True
                    jobs.append(job_info)
                    logger.debug(f"✅ Found CS new grad role: {job_info['title']}")
            
            self.results["requests_scrapes"] = self.results.get("requests_scrapes", 0) + 1
            
        except Exception as e:
            logger.error(f"❌ Requests scraping failed for {company_name}: {e}")
            raise
        
        return jobs

    def scrape_with_selenium(self, company_name: str, company_config: Dict) -> List[Dict]:
        """Scrape using Selenium for JavaScript-heavy sites"""
        if not self.driver:
            logger.error(f"❌ Selenium driver not available for {company_name}")
            return []
        
        logger.info(f"🚀 Scraping {company_name} with Selenium...")
        
        jobs = []
        
        try:
            url = company_config.get("careers_url")
            selectors = company_config.get("selectors", {})
            selenium_config = company_config.get("selenium_config", {})
            
            # Navigate to page
            self.driver.get(url)
            
            # Wait for initial page load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Handle search if needed
            if company_config.get("search_params") or selenium_config.get("search_steps"):
                self._perform_selenium_search(company_config, selenium_config)
            
            # Handle dynamic loading (infinite scroll, load more buttons, etc.)
            self._handle_dynamic_content(selenium_config)
            
            # Wait for job containers to load
            job_container_selector = selectors.get("job_container")
            if not job_container_selector:
                logger.error(f"❌ No job_container selector for {company_name}")
                return jobs
            
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, job_container_selector))
                )
            except TimeoutException:
                logger.warning(f"⚠️ Timeout waiting for job containers on {company_name}")
                # Try to continue anyway, sometimes jobs load but selector is slightly off
            
            # Extract job elements
            job_elements = self.driver.find_elements(By.CSS_SELECTOR, job_container_selector)
            logger.info(f"🎯 Found {len(job_elements)} job elements for {company_name}")
            
            # Extract job information
            base_url = "/".join(url.split("/")[:3]) if url else ""
            
            for job_element in job_elements:
                try:
                    job_info = self.extract_job_info(job_element, selectors, base_url, "selenium")
                    if job_info and self.is_relevant_job(job_info["title"]):
                        job_info["company"] = company_name
                        job_info["is_new_grad"] = True
                        job_info["is_cs_related"] = True
                        jobs.append(job_info)
                        logger.debug(f"✅ Found CS new grad role: {job_info['title']}")
                except Exception as e:
                    logger.debug(f"⚠️ Error processing job element: {e}")
                    continue
            
            self.results["selenium_scrapes"] = self.results.get("selenium_scrapes", 0) + 1
            
        except Exception as e:
            logger.error(f"❌ Selenium scraping failed for {company_name}: {e}")
            raise
        
        return jobs

    def _perform_selenium_search(self, company_config: Dict, selenium_config: Dict):
        """Perform search operations using Selenium"""
        try:
            search_steps = selenium_config.get("search_steps", [])
            search_params = company_config.get("search_params", {})
            
            # If no custom search steps, try generic search
            if not search_steps and search_params:
                self._generic_selenium_search(search_params)
                return
            
            # Execute custom search steps
            for step in search_steps:
                action = step.get("action")
                selector = step.get("selector")
                value = step.get("value", "")
                wait_time = step.get("wait", 2)
                
                if action == "click":
                    element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    element.click()
                    
                elif action == "type":
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    element.clear()
                    element.send_keys(value)
                    
                elif action == "select":
                    element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    element.click()
                    # Select option by text or value
                    option_selector = step.get("option_selector")
                    if option_selector:
                        option = self.driver.find_element(By.CSS_SELECTOR, option_selector)
                        option.click()
                
                elif action == "wait":
                    time.sleep(wait_time)
                
                elif action == "scroll":
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                time.sleep(wait_time)
                
        except Exception as e:
            logger.warning(f"⚠️ Search operation failed: {e}")

    def _generic_selenium_search(self, search_params: Dict):
        """Generic search implementation for common patterns"""
        try:
            search_term = "new grad software engineer"
            
            # Override with specific search term if provided
            for key in ["q", "query", "search", "keywords"]:
                if key in search_params:
                    search_term = search_params[key]
                    break
            
            # Common search input selectors
            search_selectors = [
                "input[type='search']",
                "input[name*='search']",
                "input[placeholder*='search']",
                "input[id*='search']",
                ".search-input",
                "#search",
                ".job-search-input"
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if search_input:
                search_input.clear()
                search_input.send_keys(search_term)
                
                # Try to submit
                try:
                    search_input.send_keys(Keys.RETURN)
                except:
                    # Look for search button
                    search_button_selectors = [
                        "button[type='submit']",
                        ".search-button",
                        ".btn-search",
                        "input[type='submit']"
                    ]
                    
                    for btn_selector in search_button_selectors:
                        try:
                            button = self.driver.find_element(By.CSS_SELECTOR, btn_selector)
                            button.click()
                            break
                        except NoSuchElementException:
                            continue
                
                # Wait for results
                time.sleep(3)
                
            else:
                logger.warning("⚠️ Could not find search input field")
                
        except Exception as e:
            logger.warning(f"⚠️ Generic search failed: {e}")

    def _handle_dynamic_content(self, selenium_config: Dict):
        """Handle infinite scroll, load more buttons, etc."""
        try:
            dynamic_config = selenium_config.get("dynamic_loading", {})
            
            if dynamic_config.get("infinite_scroll"):
                self._handle_infinite_scroll(dynamic_config)
            
            if dynamic_config.get("load_more_button"):
                self._handle_load_more_button(dynamic_config)
                
        except Exception as e:
            logger.warning(f"⚠️ Dynamic content handling failed: {e}")

    def _handle_infinite_scroll(self, config: Dict):
        """Handle infinite scroll loading"""
        max_scrolls = config.get("max_scrolls", 5)
        scroll_pause = config.get("scroll_pause", 2)
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for i in range(max_scrolls):
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(scroll_pause)
            
            # Check if new content loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logger.info(f"📜 No more content to scroll (stopped at scroll {i+1})")
                break
            
            last_height = new_height
            logger.debug(f"📜 Scrolled {i+1}/{max_scrolls}")

    def _handle_load_more_button(self, config: Dict):
        """Handle 'Load More' buttons"""
        button_selector = config.get("button_selector", ".load-more")
        max_clicks = config.get("max_clicks", 10)
        click_pause = config.get("click_pause", 2)
        
        for i in range(max_clicks):
            try:
                button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
                )
                
                # Scroll button into view
                self.driver.execute_script("arguments[0].scrollIntoView();", button)
                time.sleep(1)
                
                # Click button
                button.click()
                time.sleep(click_pause)
                
                logger.debug(f"🔄 Clicked load more button {i+1}/{max_clicks}")
                
            except TimeoutException:
                logger.info(f"🔄 No more 'Load More' button found (stopped at click {i+1})")
                break
            except Exception as e:
                logger.warning(f"⚠️ Error clicking load more button: {e}")
                break

    def scrape_company(self, company_name: str, company_config: Dict) -> List[Dict]:
        """Scrape jobs from a single company using the appropriate method"""
        if not company_config.get("enabled", True):
            logger.info(f"⏭️ Skipping {company_name} (disabled)")
            return []
        
        start_time = time.time()
        jobs = []
        
        try:
            # Determine scraping method
            scraping_method = company_config.get("scraping_method", "requests")
            
            if scraping_method == "selenium":
                jobs = self.scrape_with_selenium(company_name, company_config)
            else:
                # Try requests first, fallback to selenium if needed
                try:
                    jobs = self.scrape_with_requests(company_name, company_config)
                except Exception as e:
                    logger.warning(f"⚠️ Requests failed for {company_name}, trying Selenium: {e}")
                    if self.driver:
                        jobs = self.scrape_with_selenium(company_name, company_config)
                    else:
                        raise
            
            # Record statistics
            scrape_time = round(time.time() - start_time, 2)
            self.results["scraping_stats"][company_name] = {
                "jobs_found": len(jobs),
                "scrape_time_seconds": scrape_time,
                "method_used": scraping_method,
                "success": True
            }
            
            logger.info(f"✅ {company_name}: {len(jobs)} new grad jobs found in {scrape_time}s")
            self.results["successful_scrapes"] += 1
            
            # Rate limiting between companies
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            scrape_time = round(time.time() - start_time, 2)
            error_msg = f"Failed to scrape {company_name}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            self.results["errors"].append({
                "company": company_name,
                "error": error_msg,
                "timestamp": datetime.now().isoformat(),
                "scrape_time_seconds": scrape_time
            })
            
            self.results["scraping_stats"][company_name] = {
                "jobs_found": 0,
                "scrape_time_seconds": scrape_time,
                "method_used": company_config.get("scraping_method", "requests"),
                "success": False,
                "error": str(e)
            }
        
        return jobs

    def scrape_all_companies(self) -> Dict:
        """Scrape all companies and return results"""
        logger.info(f"🚀 Starting to scrape {len(self.companies)} companies...")
        
        all_jobs = []
        
        for company_name, company_config in self.companies.items():
            jobs = self.scrape_company(company_name, company_config)
            all_jobs.extend(jobs)
        
        # Update results
        self.results["new_grad_jobs"] = all_jobs
        self.results["total_jobs_found"] = len(all_jobs)
        
        # Summary
        logger.info(f"🎉 Scraping completed!")
        logger.info(f"📊 Summary: {len(all_jobs)} new grad jobs found")
        logger.info(f"🌐 Requests scrapes: {self.results['requests_scrapes']}")
        logger.info(f"🚀 Selenium scrapes: {self.results['selenium_scrapes']}")
        logger.info(f"✅ Successful companies: {self.results['successful_scrapes']}/{len(self.companies)}")
        
        return self.results

    def cleanup(self):
        """Clean up resources"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("🧹 Selenium driver closed")
        except Exception as e:
            logger.warning(f"⚠️ Error closing Selenium driver: {e}")
        
        try:
            if self.session:
                self.session.close()
                logger.info("🧹 Requests session closed")
        except Exception as e:
            logger.warning(f"⚠️ Error closing requests session: {e}")

    def save_results_json(self, filename: Optional[str] = None) -> str:
        """Save results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"job_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to {filename}")
        return filename

    def load_previous_results(self, filename: str) -> Optional[Dict]:
        """Load previous results for comparison"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"⚠️ Previous results file {filename} not found")
            return None
        except json.JSONDecodeError:
            logger.error(f"❌ Invalid JSON in {filename}")
            return None

    def compare_with_previous(self, previous_file: str = "latest_results.json") -> Dict:
        """Compare current results with previous scrape"""
        previous_results = self.load_previous_results(previous_file)
        
        comparison = {
            "has_updates": False,
            "new_jobs": [],
            "removed_jobs": [],
            "summary": {}
        }
        
        if not previous_results:
            comparison["has_updates"] = True
            comparison["new_jobs"] = self.results["new_grad_jobs"]
            comparison["summary"] = {
                "total_new_jobs": len(self.results["new_grad_jobs"]),
                "total_removed_jobs": 0,
                "net_change": len(self.results["new_grad_jobs"])
            }
            return comparison
        
        # Create sets of job IDs for comparison
        current_job_ids = {job["job_id"] for job in self.results["new_grad_jobs"]}
        previous_job_ids = {job["job_id"] for job in previous_results.get("new_grad_jobs", [])}
        
        # Find new and removed jobs
        new_job_ids = current_job_ids - previous_job_ids
        removed_job_ids = previous_job_ids - current_job_ids
        
        # Get full job objects for new jobs
        comparison["new_jobs"] = [
            job for job in self.results["new_grad_jobs"] 
            if job["job_id"] in new_job_ids
        ]
        
        # Get removed job info
        comparison["removed_jobs"] = [
            job for job in previous_results.get("new_grad_jobs", [])
            if job["job_id"] in removed_job_ids
        ]
        
        # Update comparison summary
        comparison["has_updates"] = len(new_job_ids) > 0 or len(removed_job_ids) > 0
        comparison["summary"] = {
            "total_new_jobs": len(new_job_ids),
            "total_removed_jobs": len(removed_job_ids),
            "net_change": len(new_job_ids) - len(removed_job_ids)
        }
        
        return comparison

def create_excel_report(json_file: str, output_file: Optional[str] = None) -> str:
    """Convert JSON results to Excel report with CS filtering stats"""
    logger.info(f"📊 Creating Excel report from {json_file}")
    
    # Load JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Create output filename
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"cs_new_grad_jobs_report_{timestamp}.xlsx"
    
    # Create Excel writer
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        
        # Jobs sheet
        if data["new_grad_jobs"]:
            jobs_df = pd.DataFrame(data["new_grad_jobs"])
            jobs_df.to_excel(writer, sheet_name='CS New Grad Jobs', index=False)
        
        # Summary sheet
        summary_data = {
            "Metric": [
                "Scrape Timestamp",
                "Total Companies Configured", 
                "Successful Scrapes",
                "Total CS Jobs Found",
                "Selenium Scrapes",
                "Requests Scrapes",
                "Companies with Errors"
            ],
            "Value": [
                data["scrape_timestamp"],
                data["total_companies"],
                data["successful_scrapes"],
                data["total_jobs_found"],
                data["selenium_scrapes"],
                data["requests_scrapes"],
                len(data["errors"])
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Scraping Stats sheet
        if data.get("scraping_stats"):
            stats_data = []
            for company, stats in data["scraping_stats"].items():
                stats_data.append({
                    "Company": company,
                    "Jobs Found": stats["jobs_found"],
                    "Scrape Time (s)": stats["scrape_time_seconds"],
                    "Method Used": stats["method_used"],
                    "Success": stats["success"],
                    "Error": stats.get("error", "")
                })
            
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Scraping Stats', index=False)
        
        # Errors sheet
        if data["errors"]:
            errors_df = pd.DataFrame(data["errors"])
            errors_df.to_excel(writer, sheet_name='Errors', index=False)
        
        # Company breakdown
        if data["new_grad_jobs"]:
            company_counts = pd.DataFrame(data["new_grad_jobs"]).groupby('company').size().reset_index()
            company_counts.columns = ['Company', 'CS Job Count']
            company_counts = company_counts.sort_values('CS Job Count', ascending=False)
            company_counts.to_excel(writer, sheet_name='Company Breakdown', index=False)
    
    logger.info(f"📊 Excel report saved to {output_file}")
    return output_file

def send_email_notification(results: Dict, comparison: Dict, excel_file: str):
    """Send email notification with CS job results"""
    
    # Email configuration from environment variables
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    
    if not all([email_user, email_password, recipient_email]):
        logger.error("❌ Email configuration incomplete. Set EMAIL_USER, EMAIL_PASSWORD, RECIPIENT_EMAIL")
        return
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = recipient_email
    msg['Subject'] = f"🎓 CS New Grad Jobs Update - {results['total_jobs_found']} Jobs Found"
    
    # Email body
    if comparison["has_updates"]:
        body = f"""
🎓 COMPUTER SCIENCE NEW GRAD JOBS UPDATE 🎓

📊 SUMMARY:
• Total CS Jobs Found: {results['total_jobs_found']}
• New Jobs This Scan: {comparison['summary']['total_new_jobs']}
• Removed Jobs: {comparison['summary']['total_removed_jobs']}
• Net Change: {comparison['summary']['net_change']:+d}
• Companies Scraped: {results['successful_scrapes']}/{results['total_companies']}
• Selenium Used: {results['selenium_scrapes']} companies
• Requests Used: {results['requests_scrapes']} companies

🆕 NEW CS JOBS FOUND:
"""
        
        for job in comparison["new_jobs"][:15]:  # Show first 15 new jobs
            body += f"• {job['title']} at {job['company']} ({job['location']})\n"
            body += f"  Method: {job.get('scraping_method', 'requests').title()}\n"
            body += f"  Apply: {job['url']}\n\n"
        
        if len(comparison["new_jobs"]) > 15:
            body += f"... and {len(comparison['new_jobs']) - 15} more CS jobs (see Excel attachment)\n\n"
        
        if comparison["removed_jobs"]:
            body += f"❌ {len(comparison['removed_jobs'])} jobs were removed since last scan.\n\n"
        
    else:
        body = f"""
📊 CS NEW GRAD JOBS - NO NEW UPDATES

• Total CS Jobs Found: {results['total_jobs_found']}
• Companies Scraped: {results['successful_scrapes']}/{results['total_companies']}
• Selenium Used: {results['selenium_scrapes']} companies
• Requests Used: {results['requests_scrapes']} companies
• No new jobs since last scan
• Full report attached for reference
"""
    
    body += f"""
🔍 FILTERING APPLIED:
✅ Computer Science related roles only
✅ New graduate positions only
✅ Entry-level (0-2 years experience)
❌ Internships excluded
❌ Senior roles excluded

🕐 Scrape completed at: {results['scrape_timestamp']}

📎 Detailed Excel report with all CS jobs is attached.

---
Automated CS New Grad Job Scraper with Selenium Support
"""
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach Excel file
    try:
        with open(excel_file, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {os.path.basename(excel_file)}',
        )
        msg.attach(part)
    except Exception as e:
        logger.error(f"❌ Failed to attach Excel file: {e}")
    
    # Send email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_user, email_password)
        text = msg.as_string()
        server.sendmail(email_user, recipient_email, text)
        server.quit()
        
        logger.info(f"📧 Email notification sent to {recipient_email}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")

def main():
    parser = argparse.ArgumentParser(description='Enhanced CS New Grad Job Scraper with Selenium')
    parser.add_argument('--config', default='companies_config.json', help='Companies configuration file')
    parser.add_argument('--output', help='Output JSON file name')
    parser.add_argument('--excel', help='Excel output file name')
    parser.add_argument('--no-email', action='store_true', help='Skip email notification')
    parser.add_argument('--previous', default='latest_results.json', help='Previous results file for comparison')
    parser.add_argument('--test-company', help='Test scraping for a single company')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = EnhancedJobScraper(args.config)
    
    try:
        # Test mode for single company
        if args.test_company:
            if args.test_company in scraper.companies:
                logger.info(f"🧪 Testing scraper for {args.test_company}")
                jobs = scraper.scrape_company(args.test_company, scraper.companies[args.test_company])
                
                print(f"\n{'='*60}")
                print(f"TEST RESULTS FOR {args.test_company.upper()}")
                print(f"{'='*60}")
                print(f"Jobs found: {len(jobs)}")
                
                for i, job in enumerate(jobs[:5], 1):  # Show first 5 jobs
                    print(f"\n{i}. {job['title']}")
                    print(f"   Location: {job['location']}")
                    print(f"   URL: {job['url']}")
                    print(f"   Method: {job['scraping_method']}")
                
                if len(jobs) > 5:
                    print(f"\n... and {len(jobs) - 5} more jobs")
                
                print(f"{'='*60}")
                return
            else:
                logger.error(f"❌ Company '{args.test_company}' not found in config")
                return
        
        # Run full scraping
        results = scraper.scrape_all_companies()
        
        # Save results
        json_file = scraper.save_results_json(args.output)
        
        # Compare with previous results
        comparison = scraper.compare_with_previous(args.previous)
        
        # Create Excel report
        excel_file = create_excel_report(json_file, args.excel)
        
        # Copy current results as latest for next comparison
        import shutil
        shutil.copy2(json_file, 'latest_results.json')
        
        # Send email notification
        if not args.no_email:
            send_email_notification(results, comparison, excel_file)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"🎓 CS NEW GRAD JOB SCRAPING COMPLETED")
        print(f"{'='*60}")
        print(f"📊 Total CS Jobs Found: {results['total_jobs_found']}")
        print(f"🆕 New Jobs This Run: {comparison['summary']['total_new_jobs']}")
        print(f"🏢 Companies Scraped: {results['successful_scrapes']}/{results['total_companies']}")
        print(f"🚀 Selenium Scrapes: {results['selenium_scrapes']}")
        print(f"🌐 Requests Scrapes: {results['requests_scrapes']}")
        print(f"❌ Errors: {len(results['errors'])}")
        print(f"💾 JSON Output: {json_file}")
        print(f"📊 Excel Report: {excel_file}")
        
        # Show top companies with most jobs
        if results['new_grad_jobs']:
            company_counts = {}
            for job in results['new_grad_jobs']:
                company_counts[job['company']] = company_counts.get(job['company'], 0) + 1
            
            top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"\n🏆 TOP COMPANIES BY CS JOB COUNT:")
            for company, count in top_companies:
                print(f"   • {company}: {count} jobs")
        
        # Show any errors
        if results['errors']:
            print(f"\n⚠️ COMPANIES WITH ERRORS:")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"   • {error['company']}: {error['error'][:80]}...")
        
        print(f"{'='*60}")
        
    finally:
        # Always cleanup resources
        scraper.cleanup()

if __name__ == "__main__":
    main()

