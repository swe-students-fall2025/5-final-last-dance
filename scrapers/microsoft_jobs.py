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
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test-id='job-listing']")))
        time.sleep(0.2)
    except TimeoutException:
        print(f"Timeout waiting for job listings to load on page {page_num}")
        return page_jobs
    
    job_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-test-id='job-listing']")
    
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
            
            link_elem = job_elem.find_element(By.CSS_SELECTOR, "a[href*='/careers/job/']")
            job_url = link_elem.get_attribute('href')
            if job_url:
                job_data['url'] = job_url
                job_data['job_id'] = job_url.split('/careers/job/')[-1].split('/')[0].split('?')[0]
            
            title_elem = job_elem.find_element(By.CSS_SELECTOR, "div.title-1aNJK")
            job_data['title'] = title_elem.text.strip()
            
            location_elem = job_elem.find_element(By.CSS_SELECTOR, "div.fieldValue-3kEar")
            job_data['location'] = location_elem.text.strip()
            
            if job_data['title'] and job_data['url']:
                page_jobs.append(job_data)
                print(f"  {idx}. {job_data['title'][:60]}")
            
        except Exception as e:
            print(f"Error processing job {idx}: {e}")
    
    return page_jobs


def click_next_button(driver, wait):
    """Click the next page button and return True if successful"""
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.2)
        
        next_buttons = driver.find_elements(By.CSS_SELECTOR, "button.pagination-module_pagination-next__OHCf9")
        
        if not next_buttons:
            print("\nNo next button found - reached end")
            return False
        
        next_button = next_buttons[0]
        
        if not next_button.is_displayed() or not next_button.is_enabled():
            print("\nNext button not available - reached end")
            return False
        
        aria_disabled = next_button.get_attribute('aria-disabled')
        if aria_disabled == 'true':
            print("\nNext button is disabled - reached end")
            return False
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        time.sleep(0.1)
        
        driver.execute_script("arguments[0].click();", next_button)
        print("\nClicked next button, loading next page...")
        time.sleep(0.8)
        
        try:
            wait.until(EC.staleness_of(next_button))
            time.sleep(0.2)
            return True
        except:
            return True
        
    except Exception as e:
        print(f"\nNo next button found or error: {e}")
        return False


def scrape_microsoft_jobs(url):
    """Scrape jobs"""
    driver = setup_driver()
    jobs_data = []
    seen_job_ids = set()
    
    try:
        print(f"Loading page: {url}")
        driver.get(url)
        
        wait = WebDriverWait(driver, 10)
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


def save_to_csv(jobs_data, filename='data/microsoft_jobs.csv'):
    """Save job data to CSV file, keeping only active jobs and preserving original scraped_at dates"""
    if not jobs_data:
        print("No data to save")
        return
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    fieldnames = ['title', 'location', 'department', 'job_id', 'url', 'scraped_at']
    
    # Read existing jobs to preserve scraped_at dates
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
    
    # Process current jobs and preserve original scraped_at dates
    active_jobs = []
    new_jobs = []
    delisted_count = len(existing_jobs)
    
    for job in jobs_data:
        job_id = job.get('job_id') or job.get('url')
        if job_id:
            if job_id in existing_jobs:
                # Preserve original scraped_at date for existing jobs
                job['scraped_at'] = existing_jobs[job_id]['scraped_at']
            else:
                new_jobs.append(job)
            active_jobs.append(job)
    
    delisted_count -= len(active_jobs) - len(new_jobs)
    
    # Write only active jobs
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(active_jobs)
    
    print(f"\nAdded {len(new_jobs)} new jobs")
    print(f"Removed {delisted_count} delisted jobs")
    print(f"Total active jobs in CSV: {len(active_jobs)}")


def main():
    """Main execution function"""
    url = "https://apply.careers.microsoft.com/careers?start=0&location=united+states&pid=1970393556628754&sort_by=distance&filter_include_remote=1&filter_profession=program+management%2Chardware+engineering%2Cquantum+computing%2Canalytics%2Csoftware+engineering%2Cresearch%252C%2520applied%252C%2520%2526%2520data%2520sciences%2Cproduct+management"
    
    print("Starting Microsoft Jobs Scraper...")
    jobs = scrape_microsoft_jobs(url)
    
    if jobs:
        save_to_csv(jobs)
        print("\nScraping completed successfully!")
    else:
        print("\nNo jobs found.")


if __name__ == "__main__":
    main()
