from __future__ import annotations

import os
import datetime

from flask import Flask, render_template, request, redirect, url_for
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

# Predefined lists for preferences
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


def create_app():
    """
    Create and configure the Flask application.
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # MongoDB connection
    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]

    try:
        cxn.admin.command("ping")
        print(" *", "Connected to MongoDB!")
    except Exception as e:
        print(" * MongoDB connection error:", e)

    @app.route("/")
    def home():
        """
        Route for the home page. Displays job board.
        """
        jobs = list(db.jobs.find({}).sort("posted_date", -1))
        return render_template("index.html", job_board=jobs, recommendations=jobs[:3])

    @app.route("/preferences/<user_id>")
    def preferences(user_id):
        """
        Route for viewing/editing user preferences.
        # TODO: Replace user_id with session-based auth
        """
        company_prefs = list(db.company_preferences.find({"user_id": user_id}))
        role_prefs = list(db.role_preferences.find({"user_id": user_id}))
        location_prefs = list(db.location_preferences.find({"user_id": user_id}))
        job_type_prefs = db.job_type_preferences.find_one({"user_id": user_id})

        return render_template(
            "preferences.html",
            user_id=user_id,
            companies=COMPANIES,
            roles=ROLES,
            locations=LOCATIONS,
            job_types=JOB_TYPES,
            company_prefs={p["company"]: p["rank"] for p in company_prefs},
            role_prefs={p["role"]: p["rank"] for p in role_prefs},
            location_prefs={p["location"]: p["rank"] for p in location_prefs},
            job_type_prefs=job_type_prefs.get("types", []) if job_type_prefs else [],
        )

    @app.route("/preferences/<user_id>", methods=["POST"])
    def save_preferences(user_id):
        """
        Save all preferences for a user.
        # TODO: Replace user_id with session-based auth
        """
        errors = []

        # --- Collect company rankings ---
        company_rankings = {}
        for company in COMPANIES:
            rank = request.form.get(f"company_{company}")
            if rank and rank.isdigit() and 1 <= int(rank) <= len(COMPANIES):
                company_rankings[company] = int(rank)

        # Check for duplicate company ranks
        if len(company_rankings.values()) != len(set(company_rankings.values())):
            errors.append("Company rankings must be unique (no duplicate numbers).")

        # --- Collect role rankings ---
        role_rankings = {}
        for role in ROLES:
            rank = request.form.get(f"role_{role}")
            if rank and rank.isdigit() and 1 <= int(rank) <= len(ROLES):
                role_rankings[role] = int(rank)

        # Check for duplicate role ranks
        if len(role_rankings.values()) != len(set(role_rankings.values())):
            errors.append("Role rankings must be unique (no duplicate numbers).")

        # --- Collect location rankings ---
        location_rankings = {}
        for location in LOCATIONS:
            rank = request.form.get(f"location_{location}")
            if rank and rank.isdigit() and 1 <= int(rank) <= len(LOCATIONS):
                location_rankings[location] = int(rank)

        # Check for duplicate location ranks
        if len(location_rankings.values()) != len(set(location_rankings.values())):
            errors.append("Location rankings must be unique (no duplicate numbers).")

        # --- Collect job type selections (multi-select, no validation needed) ---
        selected_job_types = request.form.getlist("job_types")

        # --- If errors, redirect back with error messages ---
        if errors:
            return render_template(
                "preferences.html",
                user_id=user_id,
                companies=COMPANIES,
                roles=ROLES,
                locations=LOCATIONS,
                job_types=JOB_TYPES,
                company_prefs=company_rankings,
                role_prefs=role_rankings,
                location_prefs=location_rankings,
                job_type_prefs=selected_job_types,
                errors=errors,
            )

        # --- Save to database (clear old, insert new) ---
        now = datetime.datetime.now(datetime.UTC)

        # Companies
        db.company_preferences.delete_many({"user_id": user_id})
        for company, rank in company_rankings.items():
            db.company_preferences.insert_one({
                "user_id": user_id, "company": company, "rank": rank, "created_at": now
            })

        # Roles
        db.role_preferences.delete_many({"user_id": user_id})
        for role, rank in role_rankings.items():
            db.role_preferences.insert_one({
                "user_id": user_id, "role": role, "rank": rank, "created_at": now
            })

        # Locations
        db.location_preferences.delete_many({"user_id": user_id})
        for location, rank in location_rankings.items():
            db.location_preferences.insert_one({
                "user_id": user_id, "location": location, "rank": rank, "created_at": now
            })

        # Job types
        db.job_type_preferences.delete_many({"user_id": user_id})
        if selected_job_types:
            db.job_type_preferences.insert_one({
                "user_id": user_id, "types": selected_job_types, "created_at": now
            })

        return redirect(url_for("preferences", user_id=user_id))

    @app.errorhandler(Exception)
    def handle_error(e):
        """
        Output any errors - good for debugging.
        """
        return render_template("error.html", error=e)

    return app


app = create_app()

if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    app.run(debug=True, port=int(FLASK_PORT))
