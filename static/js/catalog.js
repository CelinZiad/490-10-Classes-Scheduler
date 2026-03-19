/* Catalog page – search, create, update, delete sequence courses */

const currentTermId = document.getElementById("termid")?.value;

// ── Client-side table filter ────────────────────────────────────────

const searchBox = document.getElementById("course-search");
if (searchBox) {
  searchBox.addEventListener("input", () => {
    const q = searchBox.value.toLowerCase();
    document.querySelectorAll("#catalog-table tbody tr").forEach((tr) => {
      const text = tr.textContent.toLowerCase();
      tr.style.display = text.includes(q) ? "" : "none";
    });
  });
}

// ── Toast helper ────────────────────────────────────────────────────

function showToast(msg, type = "success") {
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Autocomplete for course search in modal ─────────────────────────

const courseInput = document.getElementById("modal-course-input");
const acList = document.getElementById("ac-list");
let acTimer = null;
let selectedSubject = "";
let selectedCatalog = "";

function buildAcItem(course) {
  const div = document.createElement("div");
  div.dataset.subject = course.subject;
  div.dataset.catalog = course.catalog;

  const strong = document.createElement("strong");
  strong.textContent = `${course.subject} ${course.catalog}`;
  div.appendChild(strong);

  const label = ` – ${course.title || ""}${course.classunit ? " (" + course.classunit + " cr)" : ""}`;
  div.appendChild(document.createTextNode(label));

  div.addEventListener("click", () => {
    selectedSubject = course.subject;
    selectedCatalog = course.catalog;
    courseInput.value = `${selectedSubject} ${selectedCatalog}`;
    acList.style.display = "none";
  });

  return div;
}

if (courseInput) {
  courseInput.addEventListener("input", () => {
    clearTimeout(acTimer);
    const q = courseInput.value.trim();
    if (q.length < 2) {
      acList.style.display = "none";
      return;
    }
    acTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/search-catalog?q=${encodeURIComponent(q)}`);
        const items = await res.json();
        if (!items.length) {
          acList.style.display = "none";
          return;
        }
        acList.replaceChildren();
        items.forEach((c) => acList.appendChild(buildAcItem(c)));
        acList.style.display = "block";
      } catch (e) {
        console.error("Autocomplete error:", e);
      }
    }, 250);
  });

  // Close autocomplete on outside click
  document.addEventListener("click", (e) => {
    if (!courseInput.contains(e.target) && !acList.contains(e.target)) {
      acList.style.display = "none";
    }
  });
}

// ── Add Course Modal ─────────────────────────────────────────────────

document.getElementById("btn-add-course")?.addEventListener("click", () => {
  document.getElementById("modal-mode").value = "add";
  document.getElementById("modal-title").textContent = "Add Course to Sequence";
  document.getElementById("cascade-warn").style.display = "none";
  courseInput.value = "";
  selectedSubject = "";
  selectedCatalog = "";
  document.getElementById("modal-elective").checked = false;
  document.getElementById("modal-termid").value = currentTermId;
  document.getElementById("modal-add-edit").classList.add("open");
  courseInput.focus();
});

// ── Edit Course Modal ────────────────────────────────────────────────

window.openEdit = function (btn) {
  const tr = btn.closest("tr");
  const subj = tr.dataset.subject;
  const cat = tr.dataset.catalog;
  const elective = tr.dataset.elective === "true";

  document.getElementById("modal-mode").value = "edit";
  document.getElementById("modal-title").textContent = `Edit ${subj} ${cat}`;
  document.getElementById("cascade-warn").style.display = "block";

  courseInput.value = `${subj} ${cat}`;
  selectedSubject = subj;
  selectedCatalog = cat;
  document.getElementById("modal-elective").checked = elective;
  document.getElementById("modal-termid").value = currentTermId;

  document.getElementById("edit-old-subject").value = subj;
  document.getElementById("edit-old-catalog").value = cat;
  document.getElementById("edit-old-termid").value = currentTermId;

  document.getElementById("modal-add-edit").classList.add("open");
  courseInput.focus();
};

// ── Close Modal ──────────────────────────────────────────────────────

window.closeModal = function () {
  document.getElementById("modal-add-edit").classList.remove("open");
  acList.style.display = "none";
};

// Close on backdrop click
document.getElementById("modal-add-edit")?.addEventListener("click", (e) => {
  if (e.target === e.currentTarget) closeModal();
});

// ── Save (Create / Update) ───────────────────────────────────────────

document.getElementById("modal-save")?.addEventListener("click", async () => {
  const mode = document.getElementById("modal-mode").value;
  const termid = parseInt(document.getElementById("modal-termid").value, 10);
  const elective = document.getElementById("modal-elective").checked;

  // Parse subject and catalog from input if user typed manually
  if (!selectedSubject || !selectedCatalog) {
    const parts = courseInput.value.trim().split(/\s+/);
    if (parts.length >= 2) {
      selectedSubject = parts[0].toUpperCase();
      selectedCatalog = parts.slice(1).join(" ");
    }
  }

  if (!selectedSubject || !selectedCatalog) {
    showToast("Please select a valid course", "error");
    return;
  }

  try {
    let res;
    if (mode === "add") {
      res = await fetch("/api/sequence-course", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sequencetermid: termid,
          subject: selectedSubject,
          catalog: selectedCatalog,
          iselective: elective,
        }),
      });
    } else {
      res = await fetch("/api/sequence-course", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          old_termid: parseInt(document.getElementById("edit-old-termid").value, 10),
          old_subject: document.getElementById("edit-old-subject").value,
          old_catalog: document.getElementById("edit-old-catalog").value,
          new_termid: termid,
          new_subject: selectedSubject,
          new_catalog: selectedCatalog,
          iselective: elective,
        }),
      });
    }

    const data = await res.json();
    if (res.ok) {
      showToast(data.message);
      closeModal();
      location.reload();
    } else {
      showToast(data.error || "Something went wrong", "error");
    }
  } catch (e) {
    showToast("Network error: " + e.message, "error");
  }
});

// ── Delete Course Modal ──────────────────────────────────────────────

window.openDelete = function (btn) {
  const tr = btn.closest("tr");
  const subj = tr.dataset.subject;
  const cat = tr.dataset.catalog;

  document.getElementById("del-course-name").textContent = `${subj} ${cat}`;
  document.getElementById("del-subject").value = subj;
  document.getElementById("del-catalog").value = cat;
  document.getElementById("modal-delete").classList.add("open");
};

window.closeDeleteModal = function () {
  document.getElementById("modal-delete").classList.remove("open");
};

document.getElementById("modal-delete")?.addEventListener("click", (e) => {
  if (e.target === e.currentTarget) closeDeleteModal();
});

document.getElementById("modal-confirm-delete")?.addEventListener("click", async () => {
  const subject = document.getElementById("del-subject").value;
  const catalog = document.getElementById("del-catalog").value;

  try {
    const res = await fetch("/api/sequence-course", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sequencetermid: parseInt(currentTermId, 10),
        subject: subject,
        catalog: catalog,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message);
      closeDeleteModal();
      location.reload();
    } else {
      showToast(data.error || "Delete failed", "error");
    }
  } catch (e) {
    showToast("Network error: " + e.message, "error");
  }
});
