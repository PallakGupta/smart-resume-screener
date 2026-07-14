"""LLM prompt templates for extraction and matching."""

EXTRACT_SYSTEM = """You are an expert technical recruiter and resume parser.
Extract structured candidate information from the resume text.
Return ONLY valid JSON matching the schema. Do not invent facts not present in the resume.
If a field is unknown, use null or an empty list."""

EXTRACT_USER = """Parse this resume and return JSON with this exact shape:
{{
  "candidate_name": "string or null",
  "email": "string or null",
  "phone": "string or null",
  "skills": ["skill1", "skill2"],
  "experience": [
    {{
      "title": "string or null",
      "company": "string or null",
      "duration": "string or null",
      "description": "string or null"
    }}
  ],
  "education": [
    {{
      "degree": "string or null",
      "institution": "string or null",
      "year": "string or null"
    }}
  ],
  "summary": "2-3 sentence professional summary grounded in the resume"
}}

Resume text:
---
{resume_text}
---"""

MATCH_SYSTEM = """You are an expert technical recruiter evaluating candidate fit.
Compare the candidate's resume (structured + raw text) against the job description.
Score fit from 1 to 10 using this rubric:
  1–3  Poor fit — major skill or experience gaps
  4–5  Weak fit — some overlap but significant gaps
  6–7  Good fit — meets most requirements; minor gaps
  8–9  Strong fit — clearly qualified with relevant depth
  10   Exceptional fit — rare; exceeds requirements across the board

Be fair and specific. Cite concrete skills/experience. Do not invent credentials.
Return ONLY valid JSON."""

MATCH_USER = """Compare the following resume with this job description and rate fit on 1–10 with justification.

Job title: {job_title}
Company: {company}

Job description:
---
{job_description}
---

Required skills (if provided): {required_skills}

Candidate structured data:
---
{structured_resume}
---

Resume text (excerpt):
---
{resume_text}
---

Return JSON with this exact shape:
{{
  "score": <number 1-10, may be decimal e.g. 7.5>,
  "justification": "3-5 sentences explaining the score with specific evidence",
  "strengths": ["strength 1", "strength 2"],
  "gaps": ["gap 1", "gap 2"]
}}"""

JOB_SKILLS_SYSTEM = """You extract key required skills from a job description.
Return ONLY a JSON array of skill strings (max 20), most important first."""

JOB_SKILLS_USER = """Extract required skills from this job posting as a JSON array of strings.

Job title: {job_title}

Description:
---
{job_description}
---"""
