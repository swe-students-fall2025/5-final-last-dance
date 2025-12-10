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
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/profile/job_details/'], a[href*='/jobs/']")))
        time.sleep(1) 
    except TimeoutException:
        print(f"Timeout waiting for job listings to load on page {page_num}")
        return page_jobs
    
    job_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/profile/job_details/']")
    
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
            
            job_url = job_elem.get_attribute('href')
            if job_url and '/profile/job_details/' in job_url:
                job_data['url'] = job_url
                job_data['job_id'] = job_url.split('/profile/job_details/')[-1].split('/')[0].split('?')[0]
            
            title_elem = job_elem.find_element(By.CSS_SELECTOR, "h3")
            job_data['title'] = title_elem.text.strip()
            
            spans = job_elem.find_elements(By.CSS_SELECTOR, "span.xbks1sj")
            if len(spans) >= 2:
                job_data['location'] = spans[0].text.strip()
                job_data['department'] = spans[2].text.strip() if len(spans) >= 3 else spans[1].text.strip()
            
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
        time.sleep(0.5)
        
        current_url = driver.current_url
        
        next_button_selectors = [
            "div[aria-label='Button to select next week']",
            "div[aria-label*='next'][role='button']",
            "button[aria-label*='next']"
        ]
        
        next_button = None
        for selector in next_button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        aria_disabled = button.get_attribute('aria-disabled')
                        class_name = button.get_attribute('class') or ''
                        
                        if aria_disabled == 'true' or 'disabled' in class_name.lower():
                            print("\nNext button is disabled - reached end of results")
                            return False
                        
                        opacity = driver.execute_script("return window.getComputedStyle(arguments[0]).opacity;", button)
                        if opacity and float(opacity) < 0.5:
                            print("\nNext button appears disabled (low opacity) - reached end")
                            return False
                        
                        next_button = button
                        break
                if next_button:
                    break
            except:
                continue
        
        if not next_button:
            print("\nNo next button found - reached end of results")
            return False
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        time.sleep(0.3)
        
        driver.execute_script("arguments[0].click();", next_button)
        print("\nClicked next button, loading next page...")
        time.sleep(2)
        
        try:
            wait.until(EC.staleness_of(next_button))
            time.sleep(1)
            return True
        except:
            return driver.current_url != current_url
        
    except Exception as e:
        print(f"\nError clicking next button: {e}")
        return False


def scrape_meta_jobs(url):
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
            
            # Add unique jobs only
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
                print("\nReached last page or no next button found.")
                break
            
            page_num += 1
        
        print(f"\nSuccessfully scraped {len(jobs_data)} total unique jobs across {page_num} pages")
        
    except Exception as e:
        print(f"Error during scraping: {e}")
    
    finally:
        driver.quit()
    
    return jobs_data


def save_to_csv(jobs_data, filename='data/meta_jobs.csv'):
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
    url = "https://www.metacareers.com/jobsearch?sort_by_new=true&offices[0]=New%20York%2C%20NY&teams[0]=Technical%20Program%20Management&teams[1]=Software%20Engineering&teams[2]=Research&teams[3]=Data%20%26%20Analytics&teams[4]=Artificial%20Intelligence&teams[5]=Advertising%20Technology&teams[6]=AR%2FVR"
    
    print("Starting Meta Jobs Scraper...")
    jobs = scrape_meta_jobs(url)
    
    if jobs:
        save_to_csv(jobs)
        print("\nScraping completed successfully!")
    else:
        print("\nNo jobs found.")


if __name__ == "__main__":
    main()

