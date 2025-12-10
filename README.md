[![Build and Deploy Flask App](https://github.com/swe-students-fall2025/5-final-last-dance/actions/workflows/flask-app.yml/badge.svg?branch=main)](https://github.com/swe-students-fall2025/5-final-last-dance/actions/workflows/flask-app.yml)

# MAMG Tracker

MAMG Tracker — Final Project (SWE)

## Overview

MAMG Tracker aggregates job listings from Meta, Apple, Microsoft, Amazon, and Google, then ranks them based on your preferences. We built this because job hunting across multiple company sites is tedious. The app scrapes listings daily, scores each job against what you're looking for, and shows you the best matches first.

Live website: http://143.198.26.255/

## Contributors

**- [Alif](https://github.com/Alif-4)**

**- [Alfardil](https://github.com/alfardil)**

**- [Abdul](https://github.com/amendahawi)**

**- [Sam](https://github.com/SamRawdon)**

**- [Galal](https://github.com/gkbichara)**

# FEATURES

## Web App
* User registration and login with password
* MongoDB backend for user data and preferences
* Job ranking across four categories: companies, roles, locations, and job types
* Three-tier preference system (Tier 1/2/3) for each category
* Live job board sorted by match score
* Job detail pages with full descriptions
* Favorites system to save jobs
* Real-time preference updates

## Scrapers
* Five individual scrapers (Amazon, Apple, Google, Meta, Microsoft)
* Automated daily runs via GitHub Actions at 11 AM EST
* Keeps original scraped dates for tracking
* Automatically removes delisted jobs
* Selenium-based for handling dynamic content

# INSTALLATION AND SETUP

## Prerequisites

* Python 3.12+
* Pipenv
* MongoDB 4.0+
* Docker (optional)
* Chrome/Chromium (for scrapers)

## Running the App

```bash
git clone https://github.com/swe-students-fall2025/5-final-last-dance.git
cd 5-final-last-dance
cp .env.example .env
pipenv install
pipenv shell
python app.py
```

Visit http://127.0.0.1:5000

## Running Scrapers

```bash
cd scrapers
python google_jobs.py
python meta_jobs.py
# etc.
```

Each scraper updates its CSV file in `scrapers/data/`.

## Docker

```bash
docker pull alfardil28/pitchdeck
docker run -p 5000:5000 \
  -e MONGO_URI="your_mongo_uri" \
  -e MONGO_DBNAME="mamg_tracker" \
  alfardil28/pitchdeck
```

# TESTING

```bash
pipenv install --dev
pipenv run pytest
```

Tests cover authentication, job scoring, preferences, and favorites.

For coverage:
```bash
pipenv run pytest --cov=app --cov-report=html
```

# DEPLOYMENT

We use GitHub Actions for CI/CD:

**Flask App** (`.github/workflows/flask-app.yml`):
- Runs tests and linting
- Builds Docker image
- Pushes to Docker Hub
- Deploys to production server

**Job Scrapers** (`.github/workflows/scrape-jobs.yml`):
- Runs daily at 11 AM EST
- Executes all scrapers
- Updates CSV files
- Commits changes back to repo

# ARCHITECTURE

## Components

**Flask App** (`app.py`)
- Handles all routes and authentication
- Manages user sessions with Flask-Login
- Renders templates with Jinja2
- Connects to MongoDB for user data

**Job Scoring**
- Loads jobs from CSV files
- Calculates match scores based on user preferences
- Uses tier multipliers (Tier 1 = 3x, Tier 2 = 2x, Tier 3 = 1x)
- Scores across companies, roles, locations, and job types

**Scrapers** (`scrapers/`)
- One script per company
- Uses Selenium to scrape job listings
- Stores data in CSV format
- Preserves original scraped dates
- Removes jobs no longer listed

**Data Storage**
- MongoDB: users, preferences, favorites
- CSV files: job listings (title, location, department, URL, scraped_at)

## Tech Stack

- Flask + Flask-Login
- MongoDB + PyMongo
- Selenium WebDriver
- Docker
- GitHub Actions
- Pipenv

---

## Docker Hub

[alfardil28/pitchdeck](https://hub.docker.com/r/alfardil28/pitchdeck)
