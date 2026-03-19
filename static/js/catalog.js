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

// ── Autocomplete for course input (ADD mode only) ────────────────────

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

// ── Cascade warning toggle in edit mode ──────────────────────────────

function checkCascadeWarning() {
    var oldSubj = document.getElementById("editOldSubject").value;
    var oldCat = document.getElementById("editOldCatalog").value;
    var newSubj = (document.getElementById("editSubject").value || "").trim().toUpperCase();
    var newCat = (document.getElementById("editCatalogNum").value || "").trim();
    var warn = document.getElementById("cascadeWarn");
    if (newSubj !== oldSubj || newCat !== oldCat) {
        warn.style.display = "block";
    } else {
        warn.style.display = "none";
    }
}

// ── Source toggle (catalog vs new course) ────────────────────────────

function setAddSource(source) {
    document.getElementById("addSource").value = source;
    document.getElementById("btnFromCatalog").classList.toggle("active", source === "catalog");
    document.getElementById("btnNewCourse").classList.toggle("active", source === "new");
    document.getElementById("catalogSearch").style.display = source === "catalog" ? "" : "none";
    document.getElementById("newCourseFields").style.display = source === "new" ? "" : "none";
    if (source === "new") {
        document.getElementById("newSubject").focus();
    } else {
        courseInput.focus();
    }
}

// ── Add Course Modal ─────────────────────────────────────────────────

function openAddModal() {
    document.getElementById("modalMode").value = "add";
    document.getElementById("addEditTitle").textContent = "Add Course to Sequence";
    document.getElementById("cascadeWarn").style.display = "none";
    document.getElementById("sourceToggle").style.display = "";
    document.getElementById("editDetailFields").style.display = "none";
    document.getElementById("editCourseCode").style.display = "none";
    setAddSource("catalog");
    courseInput.value = "";
    selectedSubject = "";
    selectedCatalog = "";
    document.getElementById("newSubject").value = "";
    document.getElementById("newCatalog").value = "";
    document.getElementById("newTitle").value = "";
    document.getElementById("newCredits").value = "";
    document.getElementById("newPrereqs").value = "";
    document.getElementById("modalElective").checked = false;
    document.getElementById("modalTermId").value = CURRENT_TERM_ID;
    document.getElementById("addEditModal").classList.remove("hidden");
    courseInput.focus();
}

// ── Edit Course Modal ────────────────────────────────────────────────

function openEditModal(btn) {
    var subject = btn.dataset.subject;
    var catalog = btn.dataset.catalog;
    var iselective = btn.dataset.elective === "true";
    var title = btn.dataset.title;
    var credits = btn.dataset.credits;
    var prerequisites = btn.dataset.prereqs;

    document.getElementById("modalMode").value = "edit";
    document.getElementById("addEditTitle").textContent = "Edit " + subject + " " + catalog;
    document.getElementById("cascadeWarn").style.display = "none";
    document.getElementById("sourceToggle").style.display = "none";

    // Hide autocomplete search — edit mode uses direct input fields
    document.getElementById("catalogSearch").style.display = "none";
    document.getElementById("newCourseFields").style.display = "none";

    // Show editable course code fields
    document.getElementById("editCourseCode").style.display = "";
    document.getElementById("editSubject").value = subject;
    document.getElementById("editCatalogNum").value = catalog;

    // Show editable detail fields
    document.getElementById("editDetailFields").style.display = "";
    document.getElementById("editTitle").value = title || "";
    document.getElementById("editCredits").value = credits || "";
    document.getElementById("editPrereqs").value = prerequisites || "";

    document.getElementById("modalElective").checked = iselective;
    document.getElementById("modalTermId").value = CURRENT_TERM_ID;

    // Store original values for the update request
    document.getElementById("editOldSubject").value = subject;
    document.getElementById("editOldCatalog").value = catalog;
    document.getElementById("editOldTermId").value = CURRENT_TERM_ID;

    document.getElementById("addEditModal").classList.remove("hidden");
}

function closeAddEditModal() {
    document.getElementById("addEditModal").classList.add("hidden");
    document.getElementById("editCourseCode").style.display = "none";
    acList.style.display = "none";
}

// ── Attach cascade warning listeners ─────────────────────────────────

var editSubjectInput = document.getElementById("editSubject");
var editCatalogNumInput = document.getElementById("editCatalogNum");
if (editSubjectInput) editSubjectInput.addEventListener("input", checkCascadeWarning);
if (editCatalogNumInput) editCatalogNumInput.addEventListener("input", checkCascadeWarning);

// ── Save (Create / Update) ───────────────────────────────────────────

function saveAddEdit() {
    var mode = document.getElementById("modalMode").value;
    var source = document.getElementById("addSource").value;
    var termid = document.getElementById("modalTermId").value;
    var elective = document.getElementById("modalElective").checked;

    var url, body;

    if (mode === "add" && source === "new") {
        // New course mode — read from manual fields
        var subj = (document.getElementById("newSubject").value || "").trim().toUpperCase();
        var catNum = (document.getElementById("newCatalog").value || "").trim();
        var title = (document.getElementById("newTitle").value || "").trim();
        var credits = document.getElementById("newCredits").value;
        var prereqs = (document.getElementById("newPrereqs").value || "").trim();

        if (!subj || !catNum || !title) {
            showToast("Subject, catalog number, and title are required", "error");
            return;
        }

        url = "/create-course";
        body = {
            termid: termid,
            subject: subj,
            catalog: catNum,
            iselective: elective,
            create_new: true,
            title: title,
            classunit: credits ? parseFloat(credits) : null,
            prerequisites: prereqs
        };
    } else if (mode === "edit") {
        // Edit mode — read subject/catalog from edit fields
        var newSubject = (document.getElementById("editSubject").value || "").trim().toUpperCase();
        var newCatalog = (document.getElementById("editCatalogNum").value || "").trim();
        var editOldSubject = document.getElementById("editOldSubject").value;
        var editOldCatalog = document.getElementById("editOldCatalog").value;
        var editOldTermId = document.getElementById("editOldTermId").value;
        var editTitle = (document.getElementById("editTitle").value || "").trim();
        var editCredits = document.getElementById("editCredits").value;
        var editPrereqs = (document.getElementById("editPrereqs").value || "").trim();

        if (!newSubject || !newCatalog) {
            showToast("Subject and catalog number are required", "error");
            return;
        }

        url = "/update-course";
        body = {
            old_termid: editOldTermId,
            old_subject: editOldSubject,
            old_catalog: editOldCatalog,
            new_termid: termid,
            new_subject: newSubject,
            new_catalog: newCatalog,
            iselective: elective,
            title: editTitle,
            classunit: editCredits !== "" ? parseFloat(editCredits) : null,
            prerequisites: editPrereqs
        };
    } else {
        // Catalog search mode — add existing course from catalog
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

        url = "/create-course";
        body = {
            termid: termid,
            subject: selectedSubject,
            catalog: selectedCatalog,
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
