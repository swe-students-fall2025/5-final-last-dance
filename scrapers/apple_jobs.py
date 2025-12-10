import csv
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException


def setup_driver():
    """Setup Chrome driver with options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def scrape_page_jobs(driver, wait, page_num):
    """Extract jobs from current page"""
    page_jobs = []
    
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.rc-accordion-item")))
        time.sleep(1)
    except TimeoutException:
        print(f"Timeout waiting for job listings to load on page {page_num}")
        return page_jobs
    
    job_elements = driver.find_elements(By.CSS_SELECTOR, "li.rc-accordion-item")
    
    if not job_elements:
        print("No job elements found")
        return page_jobs
    
    print(f"Processing {len(job_elements)} job listings on page {page_num}...")
    
    for idx, job_elem in enumerate(job_elements, 1):
        try:
            job_data = {
                'title': '',
                'location': '',
                'department': '',
                'job_id': '',
                'url': '',
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Extract job title
            try:
                title_elem = job_elem.find_element(By.CSS_SELECTOR, "h3 a.link-inline")
                job_data['title'] = title_elem.text.strip()
                
                # Extract job URL
                job_url = title_elem.get_attribute('href')
                if job_url:
                    if not job_url.startswith('http'):
                        job_url = 'https://jobs.apple.com' + job_url
                    job_data['url'] = job_url
            except:
                pass
            
            # Extract location
            try:
                location_elem = job_elem.find_element(By.CSS_SELECTOR, "span[id*='search-store-name-container']")
                job_data['location'] = location_elem.text.strip()
            except:
                pass
            
            # Extract department/team name
            try:
                dept_elem = job_elem.find_element(By.CSS_SELECTOR, "span.team-name")
                job_data['department'] = dept_elem.text.strip()
            except:
                pass
            
            # Extract job ID (role number)
            try:
                role_num_elem = job_elem.find_element(By.CSS_SELECTOR, "span[id*='search-role-number']")
                job_data['job_id'] = role_num_elem.text.strip()
            except:
                # Try to extract from href or aria-label
                try:
                    title_elem = job_elem.find_element(By.CSS_SELECTOR, "h3 a.link-inline")
                    aria_label = title_elem.get_attribute('aria-label')
                    if aria_label:
                        # Extract job ID from aria-label like "Role Name 200635900"
                        parts = aria_label.split()
                        for part in parts:
                            if part.isdigit() and len(part) >= 8:
                                job_data['job_id'] = part
                                break
                except:
                    pass
            
            if job_data['title'] and job_data['url']:
                page_jobs.append(job_data)
                print(f"  {idx}. {job_data['title'][:60]}")
            
        except Exception as e:
            print(f"Error processing job {idx}: {e}")
    
    return page_jobs


def click_next_button(driver, wait):
    """Click the next page button and return True if successful"""
    try:
        # Scroll to pagination area
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # Get current page number
        current_page = None
        try:
            page_input = driver.find_element(By.CSS_SELECTOR, "input#pagination-search-page-number")
            current_page = page_input.get_attribute('value')
            print(f"Current page: {current_page}")
        except:
            pass
        
        # Get total pages
        try:
            total_pages_elem = driver.find_element(By.CSS_SELECTOR, "span.rc-pagination-total-pages")
            total_pages = total_pages_elem.text.strip()
            print(f"Total pages: {total_pages}")
            
            if current_page and int(current_page) >= int(total_pages):
                print("\nAlready on last page")
                return False
        except:
            pass
        
        # Find next button
        next_button_selectors = [
            "button.icon-chevronend[aria-label='Next Page']",
            "button[aria-label='Next Page']",
            "div.rc-pagination-arrow button.icon-chevronend"
        ]
        
        next_button = None
        for selector in next_button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for btn in buttons:
                    try:
                        # Check if button is enabled
                        is_disabled = btn.get_attribute('disabled')
                        aria_disabled = btn.get_attribute('aria-disabled')
                        
                        if is_disabled is None and aria_disabled != 'true':
                            next_button = btn
                            break
                    except:
                        continue
                
                if next_button:
                    break
            except:
                continue
        
        if not next_button:
            print("\nNo enabled next button found - reached end")
            return False
        
        # Scroll button into view
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
        time.sleep(0.5)
        
        # Click next button
        driver.execute_script("arguments[0].click();", next_button)
        print("Clicked next button, loading next page...")
        
        # Wait for page to load
        time.sleep(3)
        
        # Verify page changed
        if current_page:
            try:
                page_input = driver.find_element(By.CSS_SELECTOR, "input#pagination-search-page-number")
                new_page = page_input.get_attribute('value')
                
                if new_page != current_page:
                    print(f"Successfully moved to page {new_page}")
                    return True
                else:
                    print(f"Warning: Still on page {current_page}")
                    return False
            except:
                pass
        
        # Wait for new content to load
        try:
            wait.until(EC.staleness_of(next_button))
            return True
        except:
            return True
        
    except Exception as e:
        print(f"\nError during pagination: {e}")
        return False


def scrape_apple_jobs(url):
    """Scrape jobs"""
    driver = setup_driver()
    jobs_data = []
    seen_job_ids = set()
    
    try:
        print(f"Loading page: {url}")
        driver.get(url)
        
        wait = WebDriverWait(driver, 20)
        page_num = 1
        
        while True:
            print(f"\nScraping page {page_num}...")
            
            page_jobs = scrape_page_jobs(driver, wait, page_num)
            
            new_jobs_count = 0
            for job in page_jobs:
                job_id = job.get('job_id') or job.get('url')
                if job_id and job_id not in seen_job_ids:
                    jobs_data.append(job)
                    seen_job_ids.add(job_id)
                    new_jobs_count += 1
            
            print(f"\nAdded {new_jobs_count} new jobs from page {page_num}")
            print(f"Total unique jobs so far: {len(jobs_data)}")
            
            if not click_next_button(driver, wait):
                print("\nReached last page.")
                break
            
            page_num += 1
        
        print(f"\nSuccessfully scraped {len(jobs_data)} total unique jobs across {page_num} pages")
        
    except Exception as e:
        print(f"Error during scraping: {e}")
    
    finally:
        driver.quit()
    
    return jobs_data


def save_to_csv(jobs_data, filename='data/apple_jobs.csv'):
    """Save job data to CSV file, appending new jobs only"""
    if not jobs_data:
        print("No data to save")
        return
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    fieldnames = ['title', 'location', 'department', 'job_id', 'url', 'scraped_at']
    
    # Read existing jobs
    existing_jobs = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    job_id = row.get('job_id') or row.get('url')
                    if job_id:
                        existing_jobs[job_id] = row
            print(f"Found {len(existing_jobs)} existing jobs in CSV")
        except Exception as e:
            print(f"Error reading existing CSV: {e}")
    
    # Add new jobs only
    new_jobs = []
    for job in jobs_data:
        job_id = job.get('job_id') or job.get('url')
        if job_id and job_id not in existing_jobs:
            new_jobs.append(job)
            existing_jobs[job_id] = job
    
    # Write all jobs (existing + new)
    all_jobs = list(existing_jobs.values())
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_jobs)
    
    print(f"\nAdded {len(new_jobs)} new jobs")
    print(f"Total jobs in CSV: {len(all_jobs)}")


def main():
    """Main execution function"""
    url = "https://jobs.apple.com/en-us/search?location=new-york-state985&team=machine-learning-infrastructure-MLAI-MLI+deep-learning-and-reinforcement-learning-MLAI-DLRL+natural-language-processing-and-speech-technologies-MLAI-NLP+computer-vision-MLAI-CV+applied-research-MLAI-AR+acoustic-technologies-HRDWR-ACT+analog-and-digital-design-HRDWR-ADD+architecture-HRDWR-ARCH+battery-engineering-HRDWR-BE+camera-technologies-HRDWR-CAM+display-technologies-HRDWR-DISP+engineering-project-management-HRDWR-EPM+environmental-technologies-HRDWR-ENVT+health-technology-HRDWR-HT+machine-learning-and-ai-HRDWR-MCHLN+mechanical-engineering-HRDWR-ME+process-engineering-HRDWR-PE+reliability-engineering-HRDWR-REL+sensor-technologies-HRDWR-SENT+silicon-technologies-HRDWR-SILT+system-design-and-test-engineering-HRDWR-SDE+wireless-hardware-HRDWR-WT+apps-and-frameworks-SFTWR-AF+cloud-and-infrastructure-SFTWR-CLD+core-operating-systems-SFTWR-COS+devops-and-site-reliability-SFTWR-DSR+engineering-project-management-SFTWR-EPM+information-systems-and-technology-SFTWR-ISTECH+machine-learning-and-ai-SFTWR-MCHLN+security-and-privacy-SFTWR-SEC+software-quality-automation-and-tools-SFTWR-SQAT+wireless-software-SFTWR-WSFT+internships-STDNT-INTRN"
    
    print("Starting Apple Jobs Scraper...")
    jobs = scrape_apple_jobs(url)
    
    if jobs:
        save_to_csv(jobs)
        print("\nScraping completed successfully!")
    else:
        print("\nNo jobs found.")


if __name__ == "__main__":
    main()
