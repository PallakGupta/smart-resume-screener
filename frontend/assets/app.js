const API = "/api";

const els = {
  healthStatus: document.getElementById("healthStatus"),
  healthLabel: document.getElementById("healthLabel"),
  dropzone: document.getElementById("dropzone"),
  fileInput: document.getElementById("fileInput"),
  uploadMsg: document.getElementById("uploadMsg"),
  resumeList: document.getElementById("resumeList"),
  jobForm: document.getElementById("jobForm"),
  jobSelect: document.getElementById("jobSelect"),
  jobMsg: document.getElementById("jobMsg"),
  saveJobBtn: document.getElementById("saveJobBtn"),
  threshold: document.getElementById("threshold"),
  screenBtn: document.getElementById("screenBtn"),
  screenMsg: document.getElementById("screenMsg"),
  resultsMeta: document.getElementById("resultsMeta"),
  resultsGrid: document.getElementById("resultsGrid"),
};

function showMsg(el, text, type = "") {
  el.hidden = !text;
  el.textContent = text || "";
  el.className = `msg${type ? ` ${type}` : ""}`;
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, options);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
      : detail || res.statusText || "Request failed";
    throw new Error(message);
  }
  return data;
}

async function refreshHealth() {
  try {
    const h = await api("/health");
    els.healthStatus.classList.add("ok");
    els.healthStatus.classList.remove("err");
    els.healthLabel.textContent = h.llm_configured
      ? `LLM ready · ${h.model}`
      : "Heuristic mode (no API key)";
  } catch {
    els.healthStatus.classList.add("err");
    els.healthStatus.classList.remove("ok");
    els.healthLabel.textContent = "API offline";
  }
}

async function loadResumes() {
  const resumes = await api("/resumes");
  if (!resumes.length) {
    els.resumeList.innerHTML = `<li class="empty-state" style="padding:1rem">No resumes yet.</li>`;
    return;
  }
  els.resumeList.innerHTML = resumes
    .map(
      (r) => `
      <li class="resume-item" data-id="${r.id}">
        <header>
          <div>
            <strong>${escapeHtml(r.candidate_name || r.original_filename)}</strong>
            <div class="meta">${escapeHtml(r.email || "No email")} · ${escapeHtml(r.original_filename)}</div>
          </div>
          <button class="btn danger" type="button" data-delete="${r.id}">Delete</button>
        </header>
        <div class="chips">
          ${(r.skills || []).slice(0, 8).map((s) => `<span class="chip">${escapeHtml(s)}</span>`).join("")}
        </div>
      </li>`
    )
    .join("");
}

async function loadJobs(selectId) {
  const jobs = await api("/jobs");
  if (!jobs.length) {
    els.jobSelect.innerHTML = `<option value="">No jobs saved yet</option>`;
    return;
  }
  els.jobSelect.innerHTML = jobs
    .map(
      (j) =>
        `<option value="${j.id}">${escapeHtml(j.title)}${j.company ? ` · ${escapeHtml(j.company)}` : ""}</option>`
    )
    .join("");
  if (selectId) els.jobSelect.value = String(selectId);
}

async function uploadFiles(files) {
  if (!files?.length) return;
  showMsg(els.uploadMsg, `Uploading ${files.length} file(s)…`);
  let ok = 0;
  const errors = [];
  for (const file of files) {
    const body = new FormData();
    body.append("file", file);
    try {
      await api("/resumes", { method: "POST", body });
      ok += 1;
    } catch (err) {
      errors.push(`${file.name}: ${err.message}`);
    }
  }
  await loadResumes();
  if (errors.length) {
    showMsg(els.uploadMsg, `Uploaded ${ok}. Errors: ${errors.join(" | ")}`, "error");
  } else {
    showMsg(els.uploadMsg, `Uploaded ${ok} resume(s).`, "ok");
  }
}

els.dropzone.addEventListener("click", () => els.fileInput.click());
els.fileInput.addEventListener("change", (e) => {
  uploadFiles([...e.target.files]);
  e.target.value = "";
});

["dragenter", "dragover"].forEach((evt) => {
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.add("dragover");
  });
});
["dragleave", "drop"].forEach((evt) => {
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.remove("dragover");
  });
});
els.dropzone.addEventListener("drop", (e) => {
  uploadFiles([...e.dataTransfer.files]);
});

els.resumeList.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-delete]");
  if (!btn) return;
  const id = btn.getAttribute("data-delete");
  try {
    await api(`/resumes/${id}`, { method: "DELETE" });
    await loadResumes();
    showMsg(els.uploadMsg, "Resume deleted.", "ok");
  } catch (err) {
    showMsg(els.uploadMsg, err.message, "error");
  }
});

els.jobForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(els.jobForm);
  const skillsRaw = String(fd.get("skills") || "").trim();
  const payload = {
    title: String(fd.get("title") || "").trim(),
    company: String(fd.get("company") || "").trim() || null,
    description: String(fd.get("description") || "").trim(),
    required_skills: skillsRaw
      ? skillsRaw.split(",").map((s) => s.trim()).filter(Boolean)
      : [],
  };
  els.saveJobBtn.disabled = true;
  try {
    const job = await api("/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    showMsg(els.jobMsg, `Saved “${job.title}” (skills: ${(job.required_skills || []).slice(0, 6).join(", ") || "inferred"}).`, "ok");
    await loadJobs(job.id);
  } catch (err) {
    showMsg(els.jobMsg, err.message, "error");
  } finally {
    els.saveJobBtn.disabled = false;
  }
});

els.screenBtn.addEventListener("click", async () => {
  const jobId = Number(els.jobSelect.value);
  if (!jobId) {
    showMsg(els.screenMsg, "Save or select a job first.", "error");
    return;
  }
  const threshold = Number(els.threshold.value) || 6;
  els.screenBtn.disabled = true;
  showMsg(els.screenMsg, "Screening candidates…");
  try {
    const data = await api("/screen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, shortlist_min_score: threshold }),
    });
    renderResults(data);
    showMsg(
      els.screenMsg,
      `Screened ${data.total_screened}. Shortlisted ${data.shortlisted_count} (≥ ${data.shortlist_min_score}).`,
      "ok"
    );
  } catch (err) {
    showMsg(els.screenMsg, err.message, "error");
  } finally {
    els.screenBtn.disabled = false;
  }
});

function renderResults(data) {
  els.resultsMeta.textContent = `${data.job_title} · ${data.shortlisted_count} shortlisted of ${data.total_screened}`;
  const ranked = data.results || [];
  if (!ranked.length) {
    els.resultsGrid.innerHTML = `<div class="empty-state">No results yet.</div>`;
    return;
  }

  els.resultsGrid.innerHTML = ranked
    .map((r, i) => {
      const pct = Math.max(0, Math.min(100, (r.score / 10) * 100));
      const low = r.score < 6;
      return `
        <article class="result-card" style="animation-delay:${i * 0.05}s">
          <div class="score-ring ${low ? "low" : ""}" style="--pct:${pct}">${r.score.toFixed(1)}</div>
          <div class="result-body">
            <h3>
              ${escapeHtml(r.candidate_name || r.resume_filename || `Candidate #${r.resume_id}`)}
              <span class="badge ${r.shortlisted ? "yes" : "no"}">${r.shortlisted ? "Shortlisted" : "Not shortlisted"}</span>
            </h3>
            <p class="sub">${escapeHtml(r.candidate_email || "No email")} · scored by ${escapeHtml(r.scored_by)}</p>
            <p class="justification">${escapeHtml(r.justification)}</p>
            <div class="two-col">
              <div>
                <h4>Strengths</h4>
                <ul>${(r.strengths || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("") || "<li>—</li>"}</ul>
              </div>
              <div>
                <h4>Gaps</h4>
                <ul>${(r.gaps || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("") || "<li>—</li>"}</ul>
              </div>
            </div>
            <div class="chips" style="margin-top:0.85rem">
              ${(r.candidate_skills || []).slice(0, 10).map((s) => `<span class="chip">${escapeHtml(s)}</span>`).join("")}
            </div>
          </div>
        </article>`;
    })
    .join("");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

(async function init() {
  await refreshHealth();
  try {
    await Promise.all([loadResumes(), loadJobs()]);
  } catch (err) {
    showMsg(els.uploadMsg, err.message, "error");
  }
})();
