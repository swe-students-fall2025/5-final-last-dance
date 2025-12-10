from __future__ import annotations

import os
import csv
import datetime
from datetime import timezone

from flask import Flask, render_template, request, redirect, url_for, abort
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.join("scrapers", "data")

CSV_SOURCES = [    
    (os.path.join(CSV_DIR, "meta_internships.csv"), "Meta"),
    (os.path.join(CSV_DIR, "microsoft_jobs.csv"), "Microsoft"),
    # (os.path.join(CSV_DIR, "google_jobs.csv"), "Google"),
    # (os.path.join(CSV_DIR, "amazon_jobs.csv"), "Amazon"),
]

COMPANIES = [
    "Google", "Microsoft", "Apple", "Amazon", "Meta",
    "Netflix", "Spotify", "Stripe", "Airbnb", "Uber"
]

ROLES = [
    "Software Engineer", "Data Scientist", "Product Manager",
    "DevOps Engineer", "ML Engineer", "Frontend Developer",
    "Backend Developer", "Full Stack Developer", "Data Analyst",
    "UX Designer", "Data Engineer"
]

LOCATIONS = [
    "Remote",
    "New York, NY",
    "San Francisco, CA",
    "Austin, TX",
    "Seattle, WA",
    "Toronto, Canada",
    "London, UK",
    "Berlin, Germany",
    "Los Angeles, CA",
    "Chicago, IL"
]

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]

TIERS = [
    {"value": 1, "label": "Target"},
    {"value": 2, "label": "Good"},
    {"value": 3, "label": "Safety"},
    {"value": 4, "label": "Not at all"},
]

DEFAULT_TIER = 3

def load_jobs_from_csv(path: str, company_name: str):
    """Load jobs from a CSV produced by a scraper and normalize fields."""
    if not os.path.exists(path):
        print(f"[CSV] File not found for {company_name}: {path}")
        return []

    jobs = []
    print(f"[CSV] Loading jobs for {company_name} from {path}")

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("title") or "").strip()
            location = (row.get("location") or "").strip()
            department = (row.get("department") or "").strip()
            job_id = (row.get("job_id") or "").strip()
            url = (row.get("url") or "").strip()
            scraped_str = (row.get("scraped_at") or "").strip()

            if not title or not url:
                continue

            scraped_dt = None
            if scraped_str:
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        scraped_dt = datetime.datetime.strptime(scraped_str, fmt).replace(
                            tzinfo=timezone.utc
                        )
                        break
                    except ValueError:
                        continue

            title_lower = title.lower()
            dept_lower = department.lower()

            if "intern" in title_lower or "intern" in dept_lower:
                job_type = "Internship"
            elif "contract" in title_lower or "contract" in dept_lower:
                job_type = "Contract"
            else:
                job_type = "Full-time"

            tags = []
            if department:
                for part in department.split("+"):
                    tag = part.replace("more", "").strip()
                    if tag:
                        tags.append(tag)
            if location:
                primary_location = location.split("+")[0].strip()
                if primary_location and primary_location not in tags:
                    tags.append(primary_location)

            job = {
                "title": title,
                "location": location,
                "department": department,
                "job_id": job_id,
                "url": url,
                "scraped_at": scraped_dt,
                "posted_date": scraped_dt,
                "company": company_name,
                "type": job_type,
                "tags": tags,
            }
            jobs.append(job)

    print(f"[CSV] Loaded {len(jobs)} jobs for {company_name}")
    return jobs

def score_jobs_for_user(db, user_id: str, jobs):
    now = datetime.datetime.now(timezone.utc)

    company_prefs = {
        p["company"]: p["rank"]
        for p in db.company_preferences.find({"user_id": user_id})
    }
    location_prefs = {
        p["location"]: p["rank"]
        for p in db.location_preferences.find({"user_id": user_id})
    }
    role_prefs = {
        p["role"]: p["rank"]
        for p in db.role_preferences.find({"user_id": user_id})
    }
    job_type_pref_doc = db.job_type_preferences.find_one({"user_id": user_id})
    job_type_prefs = set(job_type_pref_doc.get("types", [])) if job_type_pref_doc else set()

    scored_jobs = []

    for job in jobs:
        score = 0

        # Identifier + slug for detail URLs
        raw_company = job.get("company") or "Unknown"
        identifier = job.get("job_id") or job.get("url") or str(job.get("_id", ""))
        job["identifier"] = identifier
        job["company_slug"] = raw_company.lower().replace(" ", "-")

        company = job.get("company")
        if company in company_prefs:
            rank = company_prefs[company]
            score += (5 - rank) * 22

        location = job.get("location")
        if location in location_prefs:
            rank = location_prefs[location]
            score += (5 - rank) * 18

        role = job.get("role") or job.get("title")
        if role:
            for canonical_role in ROLES:
                if canonical_role.lower() in str(role).lower():
                    rank = role_prefs.get(canonical_role)
                    if rank:
                        score += (5 - rank) * 20
                    break

        jtype = job.get("type")
        if jtype in job_type_prefs:
            score += 15

        posted_dt = job.get("posted_date") or job.get("scraped_at")
        if isinstance(posted_dt, datetime.datetime):
            days_old = max(0, (now - posted_dt).days)
            recency_boost = max(0, 25 - days_old)
            score += recency_boost

        score = max(0, min(100, score))
        job["match_score"] = int(score)

        if "posted" not in job and isinstance(posted_dt, datetime.datetime):
            job["posted"] = posted_dt.strftime("%b %d")

        scored_jobs.append(job)

    return scored_jobs

def load_and_score_jobs(db, user_id: str):
    """Load all jobs (Mongo + CSV) and score them for this user."""
    # 1) Jobs that might already be in Mongo
    mongo_jobs = list(db.jobs.find({}))

    # 2) Jobs from all CSV-based scrapers
    csv_jobs = []
    for path, company_name in CSV_SOURCES:
        csv_jobs.extend(load_jobs_from_csv(path, company_name))

    # 3) Combine & dedupe by (company, job_id) or URL
    combined = mongo_jobs + csv_jobs
    unique_jobs = {}
    for job in combined:
        company = job.get("company") or "Unknown"
        key = (
            company,
            job.get("job_id")
            or job.get("url")
            or str(job.get("_id", "")),
        )
        if key not in unique_jobs:
            unique_jobs[key] = job

    jobs = list(unique_jobs.values())
    return score_jobs_for_user(db, user_id, jobs)

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder="static", template_folder="templates")

    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]

    try:
        cxn.admin.command("ping")
        print(" *", "Connected to MongoDB!")
    except Exception as e:
        print(" * MongoDB connection error:", e)

    @app.route("/")
    def home():
        user_id = request.args.get("user_id", "testuser")

        jobs = load_and_score_jobs(db, user_id)

        recommended_jobs = sorted(
            jobs, key=lambda j: j.get("match_score", 0), reverse=True
        )[:8]

        trending_jobs = sorted(
            jobs,
            key=lambda j: (
                j.get("scraped_at")
                or j.get("posted_date")
                or datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
            ),
            reverse=True,
        )[:10]

        # PREVIEW: only show a slice of the live board on the homepage
        live_preview = sorted(
            jobs,
            key=lambda j: (
                j.get("scraped_at")
                or j.get("posted_date")
                or datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
            ),
            reverse=True,
        )[:16] 

        return render_template(
            "index.html",
            user_id=user_id,
            recommendations=recommended_jobs,
            trending_jobs=trending_jobs,
            job_board_preview=live_preview,
            total_live_jobs=len(jobs),
            job_types=JOB_TYPES,
        )
    
    @app.route("/jobs", endpoint="jobs")
    def job_board():
        """Full live job board with client-side filtering."""
        user_id = request.args.get("user_id", "testuser")

        jobs = load_and_score_jobs(db, user_id)

        jobs_sorted = sorted(
            jobs,
            key=lambda j: (
                j.get("match_score", 0),
                j.get("scraped_at")
                or j.get("posted_date")
                or datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
            ),
            reverse=True,
        )

        return render_template(
            "jobs.html",
            user_id=user_id,
            job_board=jobs_sorted,
            job_types=JOB_TYPES,
            total_live_jobs=len(jobs),
        )
    
    @app.route("/jobs/<company_slug>/<identifier>")
    def job_detail(company_slug, identifier):
        """Detail page for a single job."""
        user_id = request.args.get("user_id", "testuser")

        jobs = load_and_score_jobs(db, user_id)

        job = next(
            (
                j
                for j in jobs
                if j.get("identifier") == identifier
                and j.get("company_slug") == company_slug
            ),
            None,
        )

        if not job:
            abort(404)

        return render_template(
            "job_detail.html",
            user_id=user_id,
            job=job,
        )

    @app.route("/preferences/<user_id>")
    def preferences(user_id):
        """Route for viewing/editing user preferences."""
        active_tab = request.args.get("tab", "companies")
        
        company_prefs = list(db.company_preferences.find({"user_id": user_id}))
        role_prefs = list(db.role_preferences.find({"user_id": user_id}))
        location_prefs = list(db.location_preferences.find({"user_id": user_id}))
        job_type_prefs = db.job_type_preferences.find_one({"user_id": user_id})

        return render_template(
            "preferences.html",
            user_id=user_id,
            active_tab=active_tab,
            tiers=TIERS,
            default_tier=DEFAULT_TIER,
            companies=COMPANIES,
            roles=ROLES,
            locations=LOCATIONS,
            job_types=JOB_TYPES,
            company_prefs={p["company"]: p["rank"] for p in company_prefs},
            role_prefs={p["role"]: p["rank"] for p in role_prefs},
            location_prefs={p["location"]: p["rank"] for p in location_prefs},
            job_type_prefs=job_type_prefs.get("types", []) if job_type_prefs else [],
        )

    @app.route("/preferences/<user_id>/companies", methods=["POST"])
    def save_company_preferences(user_id):
        """Save company preferences."""
        now = datetime.datetime.now(timezone.utc)
        db.company_preferences.delete_many({"user_id": user_id})
        
        for company in COMPANIES:
            tier = request.form.get(f"company_{company}", str(DEFAULT_TIER))
            if tier.isdigit() and 1 <= int(tier) <= 4:
                db.company_preferences.insert_one({
                    "user_id": user_id, 
                    "company": company, 
                    "rank": int(tier), 
                    "created_at": now
                })

        return redirect(url_for("preferences", user_id=user_id, tab="companies"))

    @app.route("/preferences/<user_id>/roles", methods=["POST"])
    def save_role_preferences(user_id):
        """Save role preferences."""
        now = datetime.datetime.now(timezone.utc)
        db.role_preferences.delete_many({"user_id": user_id})
        
        for role in ROLES:
            tier = request.form.get(f"role_{role}", str(DEFAULT_TIER))
            if tier.isdigit() and 1 <= int(tier) <= 4:
                db.role_preferences.insert_one({
                    "user_id": user_id, 
                    "role": role, 
                    "rank": int(tier), 
                    "created_at": now
                })

        return redirect(url_for("preferences", user_id=user_id, tab="roles"))

    @app.route("/preferences/<user_id>/locations", methods=["POST"])
    def save_location_preferences(user_id):
        """Save location preferences."""
        now = datetime.datetime.now(timezone.utc)
        db.location_preferences.delete_many({"user_id": user_id})
        
        for location in LOCATIONS:
            tier = request.form.get(f"location_{location}", str(DEFAULT_TIER))
            if tier.isdigit() and 1 <= int(tier) <= 4:
                db.location_preferences.insert_one({
                    "user_id": user_id, 
                    "location": location, 
                    "rank": int(tier), 
                    "created_at": now
                })

        return redirect(url_for("preferences", user_id=user_id, tab="locations"))

    @app.route("/preferences/<user_id>/job_types", methods=["POST"])
    def save_job_type_preferences(user_id):
        """Save job type preferences."""
        selected_job_types = request.form.getlist("job_types")

        now = datetime.datetime.now(timezone.utc)
        db.job_type_preferences.delete_many({"user_id": user_id})
        if selected_job_types:
            db.job_type_preferences.insert_one({
                "user_id": user_id, "types": selected_job_types, "created_at": now
            })

        return redirect(url_for("preferences", user_id=user_id, tab="job_types"))

    @app.errorhandler(Exception)
    def handle_error(e):
        """Output any errors - good for debugging."""
        return render_template("error.html", error=e)

    return app


app = create_app()

if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    app.run(debug=True, port=int(FLASK_PORT))
