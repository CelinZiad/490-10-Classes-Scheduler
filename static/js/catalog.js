/* Catalog page – search, create, update, delete sequence courses */
/* Delete logic originally by Vincent (PR #101), extended with search/create/update */

let selectedCourse = null;
let selectedSubject = "";
let selectedCatalog = "";
let acTimer = null;

// ── Toast helper ────────────────────────────────────────────────────

function showToast(msg, type) {
    var el = document.createElement("div");
    el.className = "toast toast-" + (type || "success");
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(function() { el.remove(); }, 3500);
}

// ── Client-side table filter ────────────────────────────────────────

var searchBox = document.getElementById("course-search");
if (searchBox) {
    searchBox.addEventListener("input", function() {
        var q = searchBox.value.toLowerCase();
        var rows = document.querySelectorAll("#catalog-table tbody tr");
        for (var i = 0; i < rows.length; i++) {
            var text = rows[i].textContent.toLowerCase();
            rows[i].style.display = text.indexOf(q) !== -1 ? "" : "none";
        }
    });
}

// ── Delete Modal (Vincent's original logic) ─────────────────────────

function openDeleteModal(subject, catalog, termid) {
    selectedCourse = { subject: subject, catalog: catalog, termid: termid };
    document.getElementById("deleteText").textContent =
        "Delete " + subject + " " + catalog + " from this semester?";
    document.getElementById("deleteModal").classList.remove("hidden");
}

function closeDeleteModal() {
    document.getElementById("deleteModal").classList.add("hidden");
}

function confirmDelete() {
    fetch("/delete-course", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(selectedCourse)
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.error) {
            showToast(data.error, "error");
        } else {
            showToast(data.message || "Deleted");
            location.reload();
        }
    })
    .catch(function(err) {
        showToast("Network error: " + err.message, "error");
    });
}

// ── Autocomplete for course input ───────────────────────────────────

var courseInput = document.getElementById("courseInput");
var acList = document.getElementById("acList");

function buildAcItem(course) {
    var div = document.createElement("div");
    div.dataset.subject = course.subject;
    div.dataset.catalog = course.catalog;

    var strong = document.createElement("strong");
    strong.textContent = course.subject + " " + course.catalog;
    div.appendChild(strong);

    var label = " \u2013 " + (course.title || "");
    if (course.classunit) label += " (" + course.classunit + " cr)";
    div.appendChild(document.createTextNode(label));

    div.addEventListener("click", function() {
        selectedSubject = course.subject;
        selectedCatalog = course.catalog;
        courseInput.value = course.subject + " " + course.catalog;
        acList.style.display = "none";
    });

    return div;
}

if (courseInput) {
    courseInput.addEventListener("input", function() {
        clearTimeout(acTimer);
        var q = courseInput.value.trim();
        if (q.length < 2) {
            acList.style.display = "none";
            return;
        }
        acTimer = setTimeout(function() {
            fetch("/api/search-catalog?q=" + encodeURIComponent(q))
                .then(function(res) { return res.json(); })
                .then(function(items) {
                    if (!items.length) {
                        acList.style.display = "none";
                        return;
                    }
                    while (acList.firstChild) acList.removeChild(acList.firstChild);
                    for (var i = 0; i < items.length; i++) {
                        acList.appendChild(buildAcItem(items[i]));
                    }
                    acList.style.display = "block";
                })
                .catch(function(e) {
                    console.error("Autocomplete error:", e);
                });
        }, 250);
    });

    document.addEventListener("click", function(e) {
        if (courseInput && !courseInput.contains(e.target) && acList && !acList.contains(e.target)) {
            acList.style.display = "none";
        }
    });
}

// ── Add Course Modal ─────────────────────────────────────────────────

function openAddModal() {
    document.getElementById("modalMode").value = "add";
    document.getElementById("addEditTitle").textContent = "Add Course to Sequence";
    document.getElementById("cascadeWarn").style.display = "none";
    courseInput.value = "";
    selectedSubject = "";
    selectedCatalog = "";
    document.getElementById("modalElective").checked = false;
    document.getElementById("modalTermId").value = CURRENT_TERM_ID;
    document.getElementById("addEditModal").classList.remove("hidden");
    courseInput.focus();
}

// ── Edit Course Modal ────────────────────────────────────────────────

function openEditModal(subject, catalog, iselective) {
    document.getElementById("modalMode").value = "edit";
    document.getElementById("addEditTitle").textContent = "Edit " + subject + " " + catalog;
    document.getElementById("cascadeWarn").style.display = "block";

    courseInput.value = subject + " " + catalog;
    selectedSubject = subject;
    selectedCatalog = catalog;
    document.getElementById("modalElective").checked = iselective;
    document.getElementById("modalTermId").value = CURRENT_TERM_ID;

    document.getElementById("editOldSubject").value = subject;
    document.getElementById("editOldCatalog").value = catalog;
    document.getElementById("editOldTermId").value = CURRENT_TERM_ID;

    document.getElementById("addEditModal").classList.remove("hidden");
    courseInput.focus();
}

function closeAddEditModal() {
    document.getElementById("addEditModal").classList.add("hidden");
    acList.style.display = "none";
}

// ── Save (Create / Update) ───────────────────────────────────────────

function saveAddEdit() {
    var mode = document.getElementById("modalMode").value;
    var termid = document.getElementById("modalTermId").value;
    var elective = document.getElementById("modalElective").checked;

    // Parse subject/catalog from input if user typed manually
    if (!selectedSubject || !selectedCatalog) {
        var parts = courseInput.value.trim().split(/\s+/);
        if (parts.length >= 2) {
            selectedSubject = parts[0].toUpperCase();
            selectedCatalog = parts.slice(1).join(" ");
        }
    }

    if (!selectedSubject || !selectedCatalog) {
        showToast("Please select a valid course", "error");
        return;
    }

    var url, body;
    if (mode === "add") {
        url = "/create-course";
        body = {
            termid: termid,
            subject: selectedSubject,
            catalog: selectedCatalog,
            iselective: elective
        };
    } else {
        url = "/update-course";
        body = {
            old_termid: document.getElementById("editOldTermId").value,
            old_subject: document.getElementById("editOldSubject").value,
            old_catalog: document.getElementById("editOldCatalog").value,
            new_termid: termid,
            new_subject: selectedSubject,
            new_catalog: selectedCatalog,
            iselective: elective
        };
    }

    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    })
    .then(function(res) { return res.json().then(function(d) { return { ok: res.ok, data: d }; }); })
    .then(function(result) {
        if (result.ok) {
            showToast(result.data.message);
            closeAddEditModal();
            location.reload();
        } else {
            showToast(result.data.error || "Something went wrong", "error");
        }
    })
    .catch(function(e) {
        showToast("Network error: " + e.message, "error");
    });
}
