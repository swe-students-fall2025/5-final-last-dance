import csv
import os
from pathlib import Path


def combine_job_csvs():
    """Combine job files into one"""
    
    data_dir = Path('data')
    
    # job csv files
    job_files = [
        'meta_jobs.csv',
        'microsoft_jobs.csv',
        'amazon_jobs.csv',
        'google_jobs.csv',
        'apple_jobs.csv'
    ]
    
    combined_jobs = []
    
    # read through
    for filename in job_files:
        filepath = data_dir / filename
        
        if not filepath.exists():
            print(f"Warning: {filename} not found, skipping...")
            continue
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                jobs = list(reader)
                
                # add company name based on file
                company = filename.replace('_jobs.csv', '').capitalize()
                for job in jobs:
                    if not job.get('department') or job['department'] == '':
                        job['department'] = company
                    job['company'] = company
                
                combined_jobs.extend(jobs)
                print(f"Added {len(jobs)} jobs from {filename}")
        
        except Exception as e:
            print(f"Error reading {filename}: {e}")
    
    if not combined_jobs:
        print("No jobs found to combine")
        return
    
    # create output file
    output_file = data_dir / 'all_jobs.csv'
    
    fieldnames = ['company', 'title', 'location', 'department', 'job_id', 'url', 'scraped_at']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(combined_jobs)
    
    print(f"\n✓ Combined {len(combined_jobs)} total jobs")
    print(f"✓ Saved to {output_file}")
    
    print("\nJobs by company:")
    company_counts = {}
    for job in combined_jobs:
        company = job.get('company', 'Unknown')
        company_counts[company] = company_counts.get(company, 0) + 1
    
    for company, count in sorted(company_counts.items()):
        print(f"  {company}: {count} jobs")


if __name__ == "__main__":
    combine_job_csvs()
