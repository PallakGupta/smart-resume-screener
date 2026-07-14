"""Quick smoke test for local verification."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
client = TestClient(app)


def main() -> None:
    r = client.get("/api/health")
    print("health", r.status_code, r.json())
    assert r.status_code == 200

    for name in ["alex_rivera.txt", "jordan_lee.txt", "sam_patel.txt"]:
        path = SAMPLES / name
        with path.open("rb") as fh:
            u = client.post(
                "/api/resumes",
                files={"file": (name, fh, "text/plain")},
            )
        print(
            "upload",
            name,
            u.status_code,
            u.json().get("candidate_name"),
            "skills",
            len(u.json().get("skills") or []),
        )
        assert u.status_code == 201

    job = client.post(
        "/api/jobs",
        json={
            "title": "Backend Engineer",
            "company": "Acme",
            "description": (
                "We need a backend engineer with Python, FastAPI, SQL, PostgreSQL, "
                "Docker, and LLM/OpenAI experience for AI recruiting tools. AWS and "
                "Kubernetes are nice to have for scaling services in production."
            ),
            "required_skills": ["Python", "FastAPI", "SQL", "Docker", "LLM"],
        },
    )
    print("job", job.status_code, job.json()["id"], job.json().get("required_skills"))
    assert job.status_code == 201

    screened = client.post(
        "/api/screen",
        json={"job_id": job.json()["id"], "shortlist_min_score": 6},
    )
    body = screened.json()
    print(
        "screen",
        screened.status_code,
        "shortlisted",
        body["shortlisted_count"],
        "total",
        body["total_screened"],
    )
    for row in body["results"]:
        print(
            f"  {row['score']:>4}  shortlisted={row['shortlisted']}  "
            f"{row['candidate_name']}  by={row['scored_by']}"
        )
    assert screened.status_code == 200

    home = client.get("/")
    print("dashboard", home.status_code, home.headers.get("content-type"))
    assert home.status_code == 200
    print("DONE")


if __name__ == "__main__":
    main()
