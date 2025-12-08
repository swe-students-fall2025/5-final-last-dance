from __future__ import annotations

import os
import datetime

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
        """Route for the home page. Displays job board."""
        jobs = list(db.jobs.find({}).sort("posted_date", -1))
        return render_template("index.html", job_board=jobs, recommendations=jobs[:3])

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
        now = datetime.datetime.now(datetime.UTC)
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
        now = datetime.datetime.now(datetime.UTC)
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
        now = datetime.datetime.now(datetime.UTC)
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

        now = datetime.datetime.now(datetime.UTC)
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
