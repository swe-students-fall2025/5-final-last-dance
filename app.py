from __future__ import annotations

import os
import csv
import datetime
from datetime import timezone

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    abort,
    flash,
    jsonify,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
from urllib.parse import quote
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

CSV_DIR = os.path.join("scrapers", "data")

CSV_SOURCES = [
    (os.path.join(CSV_DIR, "meta_internships.csv"), "Meta"),
    (os.path.join(CSV_DIR, "microsoft_jobs.csv"), "Microsoft"),
    (os.path.join(CSV_DIR, "amazon_jobs.csv"), "Amazon"),
    (os.path.join(CSV_DIR, "google_jobs.csv"), "Google"),
    (os.path.join(CSV_DIR, "apple_jobs.csv"), "Apple"),
]

COMPANIES = [
    "Google",
    "Microsoft",
    "Apple",
    "Amazon",
    "Meta",
    "Netflix",
    "Spotify",
    "Stripe",
    "Airbnb",
    "Uber",
]

ROLES = [
    "Software Engineer",
    "Data Scientist",
    "Product Manager",
    "DevOps Engineer",
    "ML Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Data Analyst",
    "UX Designer",
    "Data Engineer",
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
    "Chicago, IL",
]

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]

TIERS = [
    {"value": 1, "label": "Target"},
    {"value": 2, "label": "Good"},
    {"value": 3, "label": "Safety"},
    {"value": 4, "label": "Not at all"},
]

DEFAULT_TIER = 3

EPOCH = datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)

def get_recommended_jobs(jobs, min_score: int = 40, limit: int = 8):
    """
    Pick the jobs that best match the user's preferences:
    - only jobs at or above min_score
    - sorted by score, then recency
    - fallback to top jobs if there aren't enough above threshold
    """
    def sort_key(j):
        return (
            j.get("match_score", 0),
            j.get("scraped_at") or j.get("posted_date") or EPOCH,
        )

    filtered = [j for j in jobs if j.get("match_score", 0) >= min_score]
    filtered.sort(key=sort_key, reverse=True)

    # Fallback: if user hasn't set many prefs yet, just use top jobs overall
    if len(filtered) < limit:
        filtered = sorted(jobs, key=sort_key, reverse=True)

    return filtered[:limit]

class User(UserMixin):
    def __init__(self, user_id, username, email):
        self.id = user_id
        self.username = username
        self.email = email


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
                        scraped_dt = datetime.datetime.strptime(
                            scraped_str, fmt
                        ).replace(tzinfo=timezone.utc)
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
            primary_location = None
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

def _tier_multiplier(rank: int) -> int:
    """
    Map preference tier to multiplier:
      1 (Target)     -> strong positive
      2 (Good)       -> medium positive
      3 (Safety)     -> small positive
      4 (Not at all) -> negative
    """
    mapping = {1: 3, 2: 2, 3: 1, 4: -2}
    return mapping.get(rank, 0)


def score_jobs_for_user(db, user_id: str, jobs, mark_favorites=False):
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
        p["role"]: p["rank"] for p in db.role_preferences.find({"user_id": user_id})
    }
    job_type_pref_doc = db.job_type_preferences.find_one({"user_id": user_id})
    job_type_prefs = (
        set(job_type_pref_doc.get("types", [])) if job_type_pref_doc else set()
    )

    favorite_set = set()
    if mark_favorites:
        favorites = list(db.favorites.find({"user_id": user_id}))
        favorite_set = {(fav["company"], fav["identifier"]) for fav in favorites}

    scored_jobs = []

    for job in jobs:
        score = 0

        raw_company = job.get("company") or "Unknown"
        raw_identifier = job.get("job_id") or job.get("url") or str(job.get("_id", ""))
        identifier = quote(raw_identifier, safe="")
        job["identifier"] = identifier
        job["company_slug"] = raw_company.lower().replace(" ", "-")

        if mark_favorites:
            job["is_favorited"] = (raw_company, identifier) in favorite_set

        company = job.get("company")
        if company in company_prefs:
            rank = company_prefs[company]
            score += _tier_multiplier(rank) * 22

        location = job.get("location")
        if location in location_prefs:
            rank = location_prefs[location]
            score += _tier_multiplier(rank) * 18

        role = job.get("role") or job.get("title")
        if role:
            for canonical_role in ROLES:
                if canonical_role.lower() in str(role).lower():
                    rank = role_prefs.get(canonical_role)
                    if rank:
                        score += _tier_multiplier(rank) * 20
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
    mongo_jobs = list(db.jobs.find({}))

    csv_jobs = []
    for path, company_name in CSV_SOURCES:
        csv_jobs.extend(load_jobs_from_csv(path, company_name))

    combined = mongo_jobs + csv_jobs
    unique_jobs = {}
    for job in combined:
        company = job.get("company") or "Unknown"
        key = (
            company,
            job.get("job_id") or job.get("url") or str(job.get("_id", "")),
        )
        if key not in unique_jobs:
            unique_jobs[key] = job

    jobs = list(unique_jobs.values())
    return score_jobs_for_user(db, user_id, jobs, mark_favorites=True)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message = "Please log in to access this page."

    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]

    try:
        cxn.admin.command("ping")
        print(" *", "Connected to MongoDB!")
    except Exception as e:
        print(" * MongoDB connection error:", e)

    @login_manager.user_loader
    def load_user(user_id):
        user_doc = db.users.find_one({"_id": ObjectId(user_id)})
        if user_doc:
            return User(
                str(user_doc["_id"]), user_doc["username"], user_doc.get("email", "")
            )
        return None

    @app.route("/register", methods=["GET", "POST"])
    def register():
        """User registration."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()

            if not username or not email or not password:
                flash("All fields are required.", "error")
                return render_template("register.html")

            if db.users.find_one({"$or": [{"username": username}, {"email": email}]}):
                flash("Username or email already exists.", "error")
                return render_template("register.html")

            now = datetime.datetime.now(timezone.utc)
            user_id = db.users.insert_one(
                {
                    "username": username,
                    "email": email,
                    "password": generate_password_hash(password),
                    "created_at": now,
                }
            ).inserted_id

            user = User(str(user_id), username, email)
            login_user(user)
            flash("Registration successful! Welcome!", "success")
            return redirect(url_for("home"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """User login."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            if not username or not password:
                flash("Username and password are required.", "error")
                return render_template("login.html")

            user_doc = db.users.find_one({"username": username})
            if user_doc and check_password_hash(user_doc["password"], password):
                user = User(
                    str(user_doc["_id"]),
                    user_doc["username"],
                    user_doc.get("email", ""),
                )
                login_user(user)
                flash("Login successful!", "success")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("home"))
            else:
                flash("Invalid username or password.", "error")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        """User logout."""
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("home"))

    @app.route("/profile")
    @login_required
    def profile():
        """User profile page showing favorited jobs."""
        user_id = current_user.id

        favorites = list(db.favorites.find({"user_id": user_id}))
        favorite_identifiers = {
            (fav["company"], fav["identifier"]) for fav in favorites
        }

        all_jobs = load_and_score_jobs(db, user_id)
        favorited_jobs = []
        for job in all_jobs:
            company = job.get("company") or "Unknown"
            identifier = job.get("identifier")
            if (company, identifier) in favorite_identifiers:
                favorited_jobs.append(job)

        favorited_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)

        return render_template(
            "profile.html",
            user=current_user,
            favorited_jobs=favorited_jobs,
            total_favorites=len(favorited_jobs),
        )

    @app.route("/favorite/<company_slug>/<identifier>", methods=["POST"])
    @login_required
    def toggle_favorite(company_slug, identifier):
        """Toggle favorite status for a job."""
        user_id = current_user.id

        all_jobs = load_and_score_jobs(db, user_id)
        job = next(
            (
                j
                for j in all_jobs
                if j.get("identifier") == identifier
                and j.get("company_slug") == company_slug
            ),
            None,
        )

        if not job:
            return jsonify({"error": "Job not found"}), 404

        company = job.get("company") or "Unknown"

        existing = db.favorites.find_one(
            {"user_id": user_id, "company": company, "identifier": identifier}
        )

        if existing:
            db.favorites.delete_one({"_id": existing["_id"]})
            return jsonify({"favorited": False, "message": "Removed from favorites"})
        else:
            now = datetime.datetime.now(timezone.utc)
            db.favorites.insert_one(
                {
                    "user_id": user_id,
                    "company": company,
                    "identifier": identifier,
                    "company_slug": company_slug,
                    "created_at": now,
                }
            )
            return jsonify({"favorited": True, "message": "Added to favorites"})

    @app.route("/api/favorites")
    @login_required
    def get_favorites():
        """Get list of favorited job identifiers for current user."""
        user_id = current_user.id
        favorites = list(db.favorites.find({"user_id": user_id}))
        favorite_set = {(fav["company"], fav["identifier"]) for fav in favorites}
        return jsonify(
            {"favorites": [{"company": f[0], "identifier": f[1]} for f in favorite_set]}
        )

    @app.route("/")
    def home():
        user_id = current_user.id if current_user.is_authenticated else "testuser"

        jobs = load_and_score_jobs(db, user_id)

        recommended_jobs = get_recommended_jobs(jobs)  # <— key change

        trending_jobs = sorted(
            jobs,
            key=lambda j: (
                j.get("scraped_at")
                or j.get("posted_date")
                or EPOCH
            ),
            reverse=True,
        )[:10]

        live_preview = sorted(
            jobs,
            key=lambda j: (
                j.get("scraped_at")
                or j.get("posted_date")
                or EPOCH
            ),
            reverse=True,
        )[:20]

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
        user_id = current_user.id if current_user.is_authenticated else "testuser"

        jobs = load_and_score_jobs(db, user_id)

        jobs_sorted = sorted(
            jobs,
            key=lambda j: (
                j.get("match_score", 0),
                j.get("scraped_at")
                or j.get("posted_date")
                or datetime.datetime(1970, 1, 1, tzinfo=timezone.utc),
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
        user_id = current_user.id if current_user.is_authenticated else "testuser"

        is_favorited = False
        if current_user.is_authenticated:
            all_jobs = load_and_score_jobs(db, user_id)
            job = next(
                (
                    j
                    for j in all_jobs
                    if j.get("identifier") == identifier
                    and j.get("company_slug") == company_slug
                ),
                None,
            )
            if job:
                company = job.get("company") or "Unknown"
                favorite = db.favorites.find_one(
                    {
                        "user_id": current_user.id,
                        "company": company,
                        "identifier": identifier,
                    }
                )
                is_favorited = favorite is not None

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
            is_favorited=is_favorited,
        )

    @app.route("/preferences")
    @login_required
    def preferences():
        """Route for viewing/editing user preferences."""
        user_id = current_user.id
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

    def _allow_userid_preferences():
        if not app.config.get("ALLOW_USERID_PREFERENCES_ENDPOINTS", False):
            abort(404)

    def _save_company_preferences(user_id: str):
        now = datetime.datetime.now(timezone.utc)
        db.company_preferences.delete_many({"user_id": user_id})

        for company in COMPANIES:
            tier = request.form.get(f"company_{company}", str(DEFAULT_TIER))
            if tier.isdigit() and 1 <= int(tier) <= 4:
                db.company_preferences.insert_one(
                    {
                        "user_id": user_id,
                        "company": company,
                        "rank": int(tier),
                        "created_at": now,
                    }
                )

        return redirect(url_for("preferences", tab="companies"))

    @app.route("/preferences/companies", methods=["POST"])
    @login_required
    def save_company_preferences():
        """Save company preferences."""
        return _save_company_preferences(current_user.id)

    @app.route("/preferences/<user_id>/companies", methods=["POST"])
    def save_company_preferences_for_user(user_id):
        _allow_userid_preferences()
        return _save_company_preferences(user_id)

    def _save_role_preferences(user_id: str):
        now = datetime.datetime.now(timezone.utc)
        db.role_preferences.delete_many({"user_id": user_id})

        for role in ROLES:
            tier = request.form.get(f"role_{role}", str(DEFAULT_TIER))
            if tier.isdigit() and 1 <= int(tier) <= 4:
                db.role_preferences.insert_one(
                    {
                        "user_id": user_id,
                        "role": role,
                        "rank": int(tier),
                        "created_at": now,
                    }
                )

        return redirect(url_for("preferences", tab="roles"))

    @app.route("/preferences/roles", methods=["POST"])
    @login_required
    def save_role_preferences():
        """Save role preferences."""
        return _save_role_preferences(current_user.id)

    @app.route("/preferences/<user_id>/roles", methods=["POST"])
    def save_role_preferences_for_user(user_id):
        _allow_userid_preferences()
        return _save_role_preferences(user_id)

    def _save_location_preferences(user_id: str):
        now = datetime.datetime.now(timezone.utc)
        db.location_preferences.delete_many({"user_id": user_id})

        for location in LOCATIONS:
            tier = request.form.get(f"location_{location}", str(DEFAULT_TIER))
            if tier.isdigit() and 1 <= int(tier) <= 4:
                db.location_preferences.insert_one(
                    {
                        "user_id": user_id,
                        "location": location,
                        "rank": int(tier),
                        "created_at": now,
                    }
                )

        return redirect(url_for("preferences", tab="locations"))

    @app.route("/preferences/locations", methods=["POST"])
    @login_required
    def save_location_preferences():
        """Save location preferences."""
        return _save_location_preferences(current_user.id)

    @app.route("/preferences/<user_id>/locations", methods=["POST"])
    def save_location_preferences_for_user(user_id):
        _allow_userid_preferences()
        return _save_location_preferences(user_id)

    def _save_job_type_preferences(user_id: str):
        selected_job_types = request.form.getlist("job_types")

        now = datetime.datetime.now(timezone.utc)
        db.job_type_preferences.delete_many({"user_id": user_id})
        if selected_job_types:
            db.job_type_preferences.insert_one(
                {"user_id": user_id, "types": selected_job_types, "created_at": now}
            )

        return redirect(url_for("preferences", tab="job_types"))

    @app.route("/preferences/job_types", methods=["POST"])
    @login_required
    def save_job_type_preferences():
        """Save job type preferences."""
        return _save_job_type_preferences(current_user.id)

    @app.route("/preferences/<user_id>/job_types", methods=["POST"])
    def save_job_type_preferences_for_user(user_id):
        _allow_userid_preferences()
        return _save_job_type_preferences(user_id)

    def _header_metrics(user_id: str):
        # Anything NOT tier 4 ("Not at all") counts as "tracked"
        company_count = db.company_preferences.count_documents(
            {"user_id": user_id, "rank": {"$ne": 4}}
        )
        location_count = db.location_preferences.count_documents(
            {"user_id": user_id, "rank": {"$ne": 4}}
        )
        role_count = db.role_preferences.count_documents(
            {"user_id": user_id, "rank": {"$ne": 4}}
        )

        job_type_doc = db.job_type_preferences.find_one({"user_id": user_id})
        job_type_count = len(job_type_doc.get("types", [])) if job_type_doc else 0

        # How many dimensions are you actively using?
        dims_count = 0
        if company_count:
            dims_count += 1
        if role_count:
            dims_count += 1
        if location_count:
            dims_count += 1
        if job_type_count:
            dims_count += 1

        # Map “how dialed-in are your prefs?” → a match-score focus %
        threshold_map = {
            0: "50%+",
            1: "60%+",
            2: "70%+",
            3: "80%+",
            4: "85%+",
        }
        match_focus = threshold_map.get(dims_count, "85%+")

        return {
            "match_focus": match_focus,
            "companies_watched": company_count,
            "locations_tracked": location_count,
        }

    @app.context_processor
    def inject_global_header_metrics():
        user_id = current_user.id if current_user.is_authenticated else "testuser"

        # 1) Pref-based metrics
        summary = _header_metrics(user_id)

        # 2) Job-based metrics (live listings + top matches), shared on all pages
        try:
            jobs = load_and_score_jobs(db, user_id)
            header_live_listings = len(jobs)
            header_top_matches = len(
                sorted(jobs, key=lambda j: j.get("match_score", 0), reverse=True)[:8]
            )
        except Exception:
            header_live_listings = 0
            header_top_matches = 0

        current_year = datetime.datetime.now().year

        return dict(
            header_match_focus=summary["match_focus"],
            header_companies_watched=summary["companies_watched"],
            header_locations_tracked=summary["locations_tracked"],
            header_live_listings=header_live_listings,
            header_top_matches=header_top_matches,
            current_year=current_year,
        )

    @app.errorhandler(Exception)
    def handle_error(e):
        """Output any errors - good for debugging."""
        return render_template("error.html", error=e)

    return app

app = create_app()

if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    app.run(debug=True, port=int(FLASK_PORT))
