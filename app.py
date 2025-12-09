from __future__ import annotations

import os
import datetime
from datetime import timezone

from flask import Flask, render_template, request, redirect, url_for
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

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

        company = job.get("company")
        if company in company_prefs:
            rank = company_prefs[company]
            score += (5 - rank) * 22

        location = job.get("location")
        if location in location_prefs:
            rank = location_prefs[location]
            score += (5 - rank) * 18

        role = job.get("role") or job.get("title")
        for canonical_role in ROLES:
            if canonical_role.lower() in str(role).lower():
                rank = role_prefs.get(canonical_role)
                if rank:
                    score += (5 - rank) * 20
                break

        jtype = job.get("type")
        if jtype in job_type_prefs:
            score += 15

        posted_dt = job.get("posted_date")
        if isinstance(posted_dt, datetime.datetime):
            days_old = max(0, (now - posted_dt).days)
            recency_boost = max(0, 25 - days_old)
            score += recency_boost

        score = max(0, min(100, score))
        job["match_score"] = int(score)

        if "posted" not in job and isinstance(job.get("posted_date"), datetime.datetime):
            job["posted"] = job["posted_date"].strftime("%b %-d")

        scored_jobs.append(job)

    return scored_jobs

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

        jobs_cursor = db.jobs.find({}).sort("posted_date", -1)
        jobs = list(jobs_cursor)

        jobs = score_jobs_for_user(db, user_id, jobs)

        recommended_jobs = sorted(jobs, key=lambda j: j.get("match_score", 0), reverse=True)[:8]

        trending_jobs = sorted(
            jobs,
            key=lambda j: (
                j.get("scraped_at")
                or j.get("posted_date")
                or datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
            ),
            reverse=True,
        )[:10]

        return render_template(
            "index.html",
            user_id=user_id,
            job_board=jobs,
            recommendations=recommended_jobs,
            trending_jobs=trending_jobs,
            job_types=JOB_TYPES,
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
