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
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.job-tile")))
        time.sleep(0.5)
    except TimeoutException:
        print(f"Timeout waiting for job listings to load on page {page_num}")
        return page_jobs
    
    job_elements = driver.find_elements(By.CSS_SELECTOR, "div.job-tile")
    
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
            
            link_elem = job_elem.find_element(By.CSS_SELECTOR, "a.job-link")
            job_url = link_elem.get_attribute('href')
            if job_url:
                if not job_url.startswith('http'):
                    job_url = 'https://www.amazon.jobs' + job_url
                job_data['url'] = job_url
            
            job_div = job_elem.find_element(By.CSS_SELECTOR, "div.job")
            job_data['job_id'] = job_div.get_attribute('data-job-id')
            
            title_elem = job_elem.find_element(By.CSS_SELECTOR, "h3.job-title")
            job_data['title'] = title_elem.text.strip()
            
            location_elem = job_elem.find_element(By.CSS_SELECTOR, "ul.list-unstyled li.text-nowrap")
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
        time.sleep(1)
        
        current_url = driver.current_url
        current_page = None
        try:
            current_page_elem = driver.find_element(By.CSS_SELECTOR, "button.page-button.current-page")
            current_page = current_page_elem.text
            print(f"Current page: {current_page}")
        except:
            pass
        
        next_button_selectors = [
            "button.btn.circle.right[data-label='right']",
            "button[aria-label='Next page']",
            "button.btn.circle.right",
            ".pagination-control button.right",
            "button[data-label='right']"
        ]
        
        next_button = None
        for selector in next_button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for btn in buttons:
                    try:
                        class_name = btn.get_attribute('class') or ''
                        aria_disabled = btn.get_attribute('aria-disabled') or ''
                        data_label = btn.get_attribute('data-label') or ''
                        enabled = btn.is_enabled()
                        
                        is_disabled = 'disabled' in class_name.split() or aria_disabled == 'true'
                        
                        if enabled and not is_disabled and (data_label == 'right' or 'right' in class_name):
                            next_button = btn
                            break
                    except:
                        continue
                
                if next_button:
                    break
            except:
                continue
        
        if not next_button:
            print("\nNo next button found - reached end")
            return False
        
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
        time.sleep(0.5)
        
        driver.execute_script("arguments[0].click();", next_button)
        print("Clicked next button, loading next page...")
        
        time.sleep(3)
        
        new_url = driver.current_url
        if new_url != current_url:
            if current_page:
                try:
                    new_page_elem = driver.find_element(By.CSS_SELECTOR, "button.page-button.current-page")
                    new_page = new_page_elem.text
                    print(f"Successfully moved to page {new_page}")
                except:
                    pass
            return True
        
        try:
            wait.until(EC.staleness_of(next_button))
            return True
        except:
            return False
        
    except Exception as e:
        print(f"\nError during pagination: {e}")
        return False


def scrape_amazon_jobs(url):
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


def save_to_csv(jobs_data, filename='data/amazon_jobs.csv'):
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
    url = "https://www.amazon.jobs/en/search?offset=0&result_limit=10&sort=relevant&category%5B%5D=software-development&category%5B%5D=project-program-product-management-technical&category%5B%5D=machine-learning-science&category%5B%5D=systems-quality-security-engineering&country%5B%5D=USA&distanceType=Mi&radius=24km&latitude=38.89036&longitude=-77.03196&loc_group_id=&loc_query=&base_query=&city=&country=USA&region=&county=&query_options=&"
    
    print("Starting Amazon Jobs Scraper...")
    jobs = scrape_amazon_jobs(url)
    
    if jobs:
        save_to_csv(jobs)
        print("\nScraping completed successfully!")
    else:
        print("\nNo jobs found.")


if __name__ == "__main__":
    main()
