from __future__ import annotations

from dataclasses import dataclass, field
from flask import Flask, render_template

app = Flask(__name__, static_folder="static", template_folder="templates")


@dataclass
class JobPosting:
    title: str
    company: str
    location: str
    summary: str
    tags: list[str] = field(default_factory=list)
    type: str = "Full-time"
    match_score: int = 0
    posted: str = "Today"


def build_sample_postings() -> list[JobPosting]:
    return [
        JobPosting(
            title="Placeholder Job 1",
            company="N/A",
            location="Remote (US)",
            summary="Job description will be here.",
            tags=["Skill 1", "Skill 2", "Skill 3"],
            match_score=92,
            posted="2 days ago",
        ),
        JobPosting(
            title="Placeholder Job 2",
            company="N/A",
            location="Toronto, Canada",
            summary="Job description will be here.",
            tags=["Skill 1", "Skill 2", "Skill 3"],
            match_score=88,
            posted="5 days ago",
        ),
        JobPosting(
            title="Placeholder Job 3",
            company="N/A",
            location="Austin, TX",
            summary="Job description will be here.",
            tags=["Skill 1", "Skill 2", "Skill 3"],
            match_score=81,
            posted="1 day ago",
        ),
    ]


def recommend_jobs(job_board: list[JobPosting], interests: set[str]) -> list[JobPosting]:
    scored = sorted(
        job_board,
        key=lambda posting: (
            posting.match_score,
            bool(interests & set(posting.tags)),
        ),
        reverse=True,
    )
    return scored[:3]


@app.route("/")
def index():
    job_board = build_sample_postings()
    interests = {"ML pipelines", "Python", "Documentation"}
    recommendations = recommend_jobs(job_board, interests)
    return render_template(
        "index.html",
        job_board=job_board,
        recommendations=recommendations,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
