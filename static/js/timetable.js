/**
 * Timetable - FullCalendar integration with sequence plan/term filtering.
 */

let calendar = null;
let filterOptions = null;
let activeSubjectFilter = "";
let activeSource = "scheduleterm"; // "scheduleterm" or "optimized"
let currentClasses = {};

const ECE_SUBJECTS = ["COEN", "ELEC", "COMP", "SOEN"];

const planFilter = document.getElementById("plan-filter");
const semesterFilter = document.getElementById("semester-filter");
const termFilter = document.getElementById("term-filter");
const subjectFilter = document.getElementById("subject-filter");
const componentFilter = document.getElementById("component-filter");
const buildingFilter = document.getElementById("building-filter");
const applyBtn = document.getElementById("apply-filters");
const clearBtn = document.getElementById("clear-filters");
const eventCount = document.getElementById("event-count");
const filterInfo = document.getElementById("filter-info");
const modal = document.getElementById("event-modal");
const modalBody = document.getElementById("modal-body");
const loadingOverlay = document.getElementById("loading-overlay");

/* ------------------------------------------------------------------ */
/*  Initialisation                                                     */
/* ------------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", async () => {
  showLoading(true);
  try {
    await loadFilters();                           // initial load (all terms)
    await loadFilters(termFilter.value);           // scope dropdowns to default term
    initCalendar();
    setupEventListeners();
    applyQuickFilter("ECE");
  } catch (err) {
    console.error("Failed to initialise timetable:", err);
    eventCount.textContent = "Error loading timetable";
  } finally {
    showLoading(false);
  }
});

/* ------------------------------------------------------------------ */
/*  Load dropdown options from /api/filters                            */
/* ------------------------------------------------------------------ */

async function loadFilters(termCode) {
  const params = new URLSearchParams();
  if (termCode) params.set("term", termCode);
  if (planFilter.value) params.set("planid", planFilter.value);
  if (semesterFilter.value) params.set("termid", semesterFilter.value);

const url = `/api/filters${params.toString() ? `?${params}` : ""}`;

  const res = await fetch(url);
  filterOptions = await res.json();

  // Term dropdown (only rebuild on first load)
  if (!termCode) {
    termFilter.innerHTML = filterOptions.terms
      .map(
        (t, i) =>
          `<option value="${t.code}" ${i === 0 ? "selected" : ""}>${t.name}</option>`
      )
      .join("");
  }

  // Subject - preserve current selection if still valid
  const prevSubject = subjectFilter.value;
  subjectFilter.innerHTML =
    '<option value="">All Subjects</option>' +
    filterOptions.subjects
      .map((s) => `<option value="${s}">${s}</option>`)
      .join("");
  if (prevSubject && filterOptions.subjects.includes(prevSubject)) {
    subjectFilter.value = prevSubject;
  }

  // Component - preserve current selection
  const prevComponent = componentFilter.value;
  componentFilter.innerHTML =
    '<option value="">All Types</option>' +
    filterOptions.components
      .map((c) => `<option value="${c}">${c}</option>`)
      .join("");
  if (prevComponent && filterOptions.components.includes(prevComponent)) {
    componentFilter.value = prevComponent;
  }

  // Building - preserve current selection
  const prevBuilding = buildingFilter.value;
  buildingFilter.innerHTML =
    '<option value="">All Buildings</option>' +
    filterOptions.buildings
      .map((b) => `<option value="${b}">${b}</option>`)
      .join("");
  if (prevBuilding && filterOptions.buildings.includes(prevBuilding)) {
    buildingFilter.value = prevBuilding;
  }

  // Sequence plans
  const prevPlan = planFilter.value;
  planFilter.innerHTML =
    '<option value="">All Programs</option>' +
    filterOptions.plans
      .map((p) => `<option value="${p.planid}">${p.planname}</option>`)
      .join("");
  if (prevPlan) {
    planFilter.value = prevPlan;
  }
}

/* ------------------------------------------------------------------ */
/*  Load terms for a selected sequence plan                            */
/* ------------------------------------------------------------------ */

async function loadPlanTerms(planid) {
  if (!planid) {
    semesterFilter.innerHTML = '<option value="">Select plan first</option>';
    semesterFilter.disabled = true;
    return;
  }

  const res = await fetch(`/api/plans/${planid}/terms`);
  const terms = await res.json();

  semesterFilter.innerHTML =
    '<option value="">All Semesters</option>' +
    terms
      .map((t) => {
        const label =
          `Year ${t.yearnumber} ${capitalise(t.season)}` +
          (t.workterm ? " (Work)" : "");
        return `<option value="${t.sequencetermid}">${label}</option>`;
      })
      .join("");

  semesterFilter.disabled = false;
}

function capitalise(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
}

/* ------------------------------------------------------------------ */
/*  FullCalendar setup                                                 */
/* ------------------------------------------------------------------ */

function initCalendar() {
  const el = document.getElementById("calendar");

  calendar = new FullCalendar.Calendar(el, {
    initialView: "timeGridWeek",
    slotMinTime: "08:00:00",
    slotMaxTime: "22:15:00",
    slotDuration: "00:15:00",
    weekends: false,
    firstDay: 1,
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "timeGridWeek,timeGridDay,listWeek",
    },
    events: function (fetchInfo, successCallback, failureCallback) {
      const params = new URLSearchParams(getFilterParams());
      fetch(`/api/events?${params}`)
        .then((res) => res.json())
        .then((data) => successCallback(data))
        .catch(() => {
          eventCount.textContent = "Error loading events";
          failureCallback(new Error("Failed to load events"));
        });
    },
    eventDidMount: (info) => {
      const p = info.event.extendedProps;
      const name = p.coursetitle ? ` - ${p.coursetitle}` : "";
      info.el.title = `${info.event.title}${name}\n${p.component} | ${fmtLocation(p)}`;
    },
    eventContent: (arg) => {
      const p = arg.event.extendedProps;
      const lines = [];
      lines.push(`<b>${arg.event.title}</b>`);
      if (p.coursetitle) {
        lines.push(`<span class="fc-event-desc">${p.coursetitle}</span>`);
      }
      lines.push(`<span class="fc-event-meta">${p.component} | ${fmtLocation(p)}</span>`);
      return { html: lines.join("") };
    },
    eventClick: (info) => showEventModal(info.event),
    eventsSet: (events) => updateStats(events),
    nowIndicator: true,
    allDaySlot: false,
    expandRows: true,
    stickyHeaderDates: true,
    dayHeaderFormat: { weekday: "short" },
    slotLabelFormat: {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    },
  });

  calendar.render();
}
/* ------------------------------------------------------------------ */
/*  Optimized List                                                  */
/* ------------------------------------------------------------------ */

async function loadOptimizedList() {
  const container = document.getElementById("optimized-list-container");
  const content = document.getElementById("optimized-list-content");

  container.style.display = "block";
  content.innerHTML = "Loading...";

  try {
    const params = new URLSearchParams(getFilterParams());
    params.set("source", "optimized"); // ensure correct source

    const res = await fetch(`/api/list-optimized?${params}`);
    const data = await res.json();

    renderOptimizedList(data);

  } catch (err) {
    content.innerHTML = "Error loading list";
    console.error(err);
  }
}

function renderOptimizedList(data) {
  const container = document.getElementById("optimized-list-content");
  container.innerHTML = "";

  const orderedDays = [
    "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
  ];

  const COMPONENT_COLORS = {
    "LEC": "#3B82F6",
    "TUT": "#10B981",
    "LAB": "#F59E0B",
    "SEM": "#8B5CF6",
    "ONL": "#06B6D4"
  };

  for (const day of orderedDays) {
    const classes = data[day] || [];
    if (!classes.length) continue;

    const section = document.createElement("div");
    section.className = "day-section";

    const title = document.createElement("h3");
    title.className = "day-title";
    title.innerText = day;
    section.appendChild(title);

    // Sort like calendar (time + duration)
    classes.sort((a, b) => {
      const t = a.startTime.localeCompare(b.startTime);
      if (t !== 0) return t;

      const durA = getDuration(a.startTime, a.endTime);
      const durB = getDuration(b.startTime, b.endTime);
      return durB - durA;
    });

    const grid = document.createElement("div");
    grid.className = "day-grid";


    classes.forEach(cls => {
      currentClasses[cls.id] = cls
      const card = document.createElement("div");
      card.className = "nice-card";

      const color = COMPONENT_COLORS[cls.component] || "#6B7280";

      card.innerHTML = `
        <div class="card-header" style="background:${color}">
          <b>${cls.subject} ${cls.catalog}</b>
          <span class="badge">${cls.component}</span>
        </div>

        <div class="card-body">
          <div class="title">${cls.coursetitle || ""}</div>

          <div class="row">
            ⏰ ${cls.startTime} - ${cls.endTime}
          </div>

          <div class="row">
            📍 ${cls.building} ${cls.room}
          </div>

          <div class="row small">
            👥 ${cls.enrollment}/${cls.capacity}
            ⏳ ${cls.waitlist}/${cls.waitlistCapacity || 0}
          </div>
        </div>

        <div class="card-footer">
          <div class="btn-group">
            <button class="btn-edit" onclick="openEditModal(${cls.id})">
              Edit
            </button>
            <button class="btn-delete" onclick="openDeleteModal(${cls.id})">
              Delete
            </button>
          </div>
        </div>
      `;

      grid.appendChild(card);
    });

    section.appendChild(grid);
    container.appendChild(section);
  }
}

function getDuration(start, end) {
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  return (eh * 60 + em) - (sh * 60 + sm);
}

/* ------------------------------------------------------------------ */
/*  UI-modal                                                         */
/* ------------------------------------------------------------------ */

function openUIModal(title, message, actionsHTML) {
  document.getElementById("ui-modal-title").innerText = title;
  document.getElementById("ui-modal-message").innerText = message;
  document.getElementById("ui-modal-actions").innerHTML = actionsHTML;

  document.getElementById("ui-modal").classList.add("open");
}

function closeUIModal() {
  document.getElementById("ui-modal").classList.remove("open");
}

/* ------------------------------------------------------------------ */
/*  Block modal                                                        */
/* ------------------------------------------------------------------ */

let currentEditId = null;

function openEditModal(id) {
  currentEditId = id;

  const cls = currentClasses[id];

  if (!cls) return;

  document.getElementById("edit-subject").value = cls.subject;
  document.getElementById("edit-catalog").value = cls.catalog;
  document.getElementById("edit-section").value = cls.section;
  document.getElementById("edit-component").value = cls.component;
  document.getElementById("edit-day").value = cls.day || "";
  document.getElementById("edit-start").value = cls.startTime;
  document.getElementById("edit-end").value = cls.endTime;

  document.getElementById("edit-building").value = cls.building;
  document.getElementById("edit-room").value = cls.room;

  document.getElementById("edit-enrollment").value = cls.enrollment;
  document.getElementById("edit-capacity").value = cls.capacity;

  document.getElementById("edit-waitlist").value = cls.waitlist;
  document.getElementById("edit-waitlist-capacity").value = cls.waitlistCapacity;

  document.getElementById("edit-modal").classList.add("open");
}

async function saveEdit(event) {
  if (event) event.preventDefault();

  closeUIModal();

  const updated = {
    subject: document.getElementById("edit-subject").value,
    catalog: document.getElementById("edit-catalog").value,
    section: document.getElementById("edit-section").value,
    component: document.getElementById("edit-component").value,
    day: document.getElementById("edit-day")?.value,
    startTime: document.getElementById("edit-start").value,
    endTime: document.getElementById("edit-end").value,
    building: document.getElementById("edit-building").value,
    room: document.getElementById("edit-room").value,
    enrollment: Number(document.getElementById("edit-enrollment").value || 0),
    capacity: Number(document.getElementById("edit-capacity").value || 0),
    waitlist: Number(document.getElementById("edit-waitlist").value || 0),
    waitlistCapacity: Number(document.getElementById("edit-waitlist-capacity").value || 0),
  };

  const error = validateClass(updated);

  if (error) {
    openUIModal(
      "Invalid Input",
      error,
      `<button class="btn-primary" onclick="closeUIModal()">OK</button>`
    );
    return;
  }

  console.log("Sending update:", updated);

  await fetch(`/api/update-class/${currentEditId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updated)
  });

      closeEditModal();

    // FORCE fresh reload (no cache)
    fetch(`/api/list-optimized?${new URLSearchParams(getFilterParams())}`, {
      cache: "no-store"
    })
      .then(res => res.json())
      .then(data => {
        renderOptimizedList(data);
      });
}

function closeEditModal() {
  document.getElementById("edit-modal").classList.remove("open");
}

function openDeleteModal(id) {
  openUIModal(
    "Delete Class",
    "Are you sure you want to delete this class?",
    `
      <button class="btn-danger" onclick="confirmDelete(${id})">Delete</button>
      <button class="btn-ghost" onclick="closeUIModal()">Cancel</button>
    `
  );
}

function resetFormErrors() {
  document.querySelectorAll("#edit-form input").forEach(input => {
    input.classList.remove("input-error");
  });
}

function confirmDelete(id) {
  closeUIModal();

  fetch(`/api/delete-class/${id}`, {
    method: "DELETE"
  })
    .then(res => res.json())
    .then(() => {
      // reload list SAME WAY
      fetch(`/api/list-optimized?${new URLSearchParams(getFilterParams())}`, {
        cache: "no-store"
      })
        .then(res => res.json())
        .then(data => renderOptimizedList(data));
    })
    .catch(err => console.error("Delete failed:", err));
}

/* ------------------------------------------------------------------ */
/*  Create modal                                                        */
/* ------------------------------------------------------------------ */

function openCreateModal() {
  document.getElementById("create-modal").classList.add("open");
}

function closeCreateModal() {
  document.getElementById("create-modal").classList.remove("open");
}


function createClass() {
  const data = {
    subject: document.getElementById("create-subject").value,
    catalog: document.getElementById("create-catalog").value,
    section: document.getElementById("create-section").value,
    component: document.getElementById("create-component").value,
    day: document.getElementById("create-day").value,
    startTime: document.getElementById("create-start").value,
    endTime: document.getElementById("create-end").value,
    building: document.getElementById("create-building").value,
    room: document.getElementById("create-room").value,
    enrollment: parseInt(document.getElementById("create-enrollment").value || 0),
    capacity: parseInt(document.getElementById("create-capacity").value || 0),
    waitlist: parseInt(document.getElementById("create-waitlist").value || 0),
    waitlistCapacity: parseInt(document.getElementById("create-waitlist-capacity").value || 0),
  };


      data.subject = data.subject.toUpperCase();

      const error = validateClass(data);

      if (error) {
        openUIModal(
          "Invalid Input",
          error,
          `<button class="btn-primary" onclick="closeUIModal()">OK</button>`
        );
        return;
      }

    fetch("/api/create-class", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    }).then(() => {
      closeCreateModal();
      applyFilters();
    });
}

/* ------------------------------------------------------------------ */
/*  Validation within modal                                           */
/* ------------------------------------------------------------------ */

function validateClass(data) {

  // Trim all string values
  Object.keys(data).forEach(k => {
    if (typeof data[k] === "string") {
      data[k] = data[k].trim();
    }
  });

  // Required fields
  if (!data.subject) return "Subject is required";
  if (!data.catalog) return "Catalog is required";
  if (!data.section) return "Section is required";
  if (!data.component) return "Component is required";
  if (!data.startTime || !data.endTime) return "Start and end time required";

  // Subject format
  if (!/^[A-Z]{3,5}$/.test(data.subject)) {
    return "Subject must be uppercase letters (e.g. COEN)";
  }

//  // Catalog format
//  if (!/^[0-9]{3}$/.test(data.catalog)) {
//    return "Catalog must be 3 digits (e.g. 243)";
//  }

//  // Section format
//  if (!/^[A-Za-z0-9]{1,3}$/.test(data.section)) {
//    return "Section must be 1–3 characters (e.g. A1)";
//  }

  // Component validation
  const validComponents = ["LEC", "LAB", "TUT"];
  if (!validComponents.includes(data.component)) {
    return "Invalid component type";
  }

//  // Day validation
//  const validDays = ["Monday","Tuesday","Wednesday","Thursday","Friday"];
//  if (!validDays.includes(data.day)) {
//    return "Invalid day selected";
//  }

  // Time validation
  if (data.startTime >= data.endTime) {
    return "End time must be after start time";
  }

  // Numeric validation
  if (isNaN(data.enrollment) || data.enrollment < 0) {
    return "Enrollment must be ≥ 0";
  }

  if (isNaN(data.capacity) || data.capacity < 0) {
    return "Capacity must be ≥ 0";
  }

  if (isNaN(data.waitlist) || data.waitlist < 0) {
    return "Waitlist must be ≥ 0";
  }

  if (isNaN(data.waitlistCapacity) || data.waitlistCapacity < 0) {
    return "Waitlist capacity must be ≥ 0";
  }

  // Logical constraints
  if (data.enrollment > data.capacity) {
    return "Enrollment cannot exceed capacity";
  }

  if (data.waitlist > data.waitlistCapacity) {
    return "Waitlist cannot exceed waitlist capacity";
  }

  return null;
}


/* -------------------------------------------------- */
/* Helper: Convert duration to minutes                */
/* -------------------------------------------------- */

function getDuration(start, end) {
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);

  return (eh * 60 + em) - (sh * 60 + sm);
}
/* ------------------------------------------------------------------ */
/*  Event listeners                                                    */
/* ------------------------------------------------------------------ */

function setupEventListeners() {
  applyBtn.addEventListener("click", applyFilters);
  clearBtn.addEventListener("click", clearFilters);

  // When term changes, refresh subject/component/building dropdowns
  termFilter.addEventListener("change", async () => {
    await loadFilters(termFilter.value);
    applyFilters();
  });

  planFilter.addEventListener("change", async () => {
    await loadPlanTerms(planFilter.value);
    applyFilters();
  });

  semesterFilter.addEventListener("change", applyFilters);

  componentFilter.addEventListener("change", applyFilters);
  
  buildingFilter.addEventListener("change", applyFilters);

  subjectFilter.addEventListener("change", () => {
    activeSubjectFilter = subjectFilter.value;
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    if (!subjectFilter.value) {
      document.querySelector('[data-filter="all"]').classList.add("active");
      filterInfo.textContent = "";
    } else {
      const btn = document.querySelector(`[data-filter="${subjectFilter.value}"]`);
      if (btn) btn.classList.add("active");
      filterInfo.textContent = `Showing ${subjectFilter.value} courses`;
    }
    applyFilters();
  });

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", (e) =>
      applyQuickFilter(e.target.dataset.filter)
    );
  });

  document.querySelector(".modal-close").addEventListener("click", closeModal);
  document.querySelector(".modal-backdrop").addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  // Source toggle: Original vs Optimized
  const srcOriginal = document.getElementById("source-original");
  const srcOptimized = document.getElementById("source-optimized");
  if (srcOriginal && srcOptimized) {
    srcOriginal.addEventListener("click", () => {
      activeSource = "scheduleterm";
      srcOriginal.classList.add("active");
      srcOptimized.classList.remove("active");
      applyFilters();
    });
    srcOptimized.addEventListener("click", () => {
      activeSource = "optimized";
      srcOptimized.classList.add("active");
      srcOriginal.classList.remove("active");
      applyFilters();
    });
  }

  // Export dropdown toggle
  const exportBtn = document.getElementById("export-btn");
  const exportMenu = document.getElementById("export-menu");
  if (exportBtn && exportMenu) {
    exportBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      exportMenu.classList.toggle("open");
    });
    document.addEventListener("click", () => exportMenu.classList.remove("open"));
  }
}

/* ------------------------------------------------------------------ */
/*  Filter helpers                                                     */
/* ------------------------------------------------------------------ */

function getFilterParams() {
  const params = { term: termFilter.value };

  if (planFilter.value) params.planid = planFilter.value;
  if (semesterFilter.value) params.termid = semesterFilter.value;

  const subj = activeSubjectFilter || subjectFilter.value;
  if (subj) params.subject = subj;

  if (componentFilter.value) params.component = componentFilter.value;
  if (buildingFilter.value) params.building = buildingFilter.value;

  if (activeSource !== "scheduleterm") params.source = activeSource;

  return params;
}

//function applyFilters() {
//  showLoading(true);
//  calendar.refetchEvents();
//  setTimeout(() => showLoading(false), 500);
//}

function applyFilters() {
  showLoading(true);

  calendar.refetchEvents();

  if (activeSource === "optimized") {
    loadOptimizedList();
  } else {
    document.getElementById("optimized-list-container").style.display = "none";
  }

  setTimeout(() => showLoading(false), 500);
}
async function clearFilters() {
  planFilter.value = "";
  semesterFilter.innerHTML = '<option value="">Select plan first</option>';
  semesterFilter.disabled = true;
  subjectFilter.value = "";
  componentFilter.value = "";
  buildingFilter.value = "";
  activeSubjectFilter = "";
  await loadFilters(termFilter.value);

  document
    .querySelectorAll(".tab-btn")
    .forEach((b) => b.classList.remove("active"));
  document.querySelector('[data-filter="all"]').classList.add("active");
  filterInfo.textContent = "";

  applyFilters();
}

function applyQuickFilter(filter) {
  document
    .querySelectorAll(".tab-btn")
    .forEach((b) => b.classList.remove("active"));
  document.querySelector(`[data-filter="${filter}"]`).classList.add("active");

  if (filter === "all") {
    activeSubjectFilter = "";
    subjectFilter.value = "";
    filterInfo.textContent = "";
  } else if (filter === "ECE") {
    activeSubjectFilter = ECE_SUBJECTS.join(",");
    subjectFilter.value = "";
    filterInfo.textContent = "Showing ECE subjects (COEN, ELEC, COMP, SOEN)";
  } else {
    activeSubjectFilter = filter;
    subjectFilter.value = filter;
    filterInfo.textContent = `Showing ${filter} courses`;
  }

  applyFilters();
}

/* ------------------------------------------------------------------ */
/*  Stats                                                              */
/* ------------------------------------------------------------------ */

function updateStats(events) {
  const n = events.length;
  eventCount.textContent = `${n} class${n !== 1 ? "es" : ""} displayed`;
}

/* ------------------------------------------------------------------ */
/*  Event detail modal                                                 */
/* ------------------------------------------------------------------ */

function showEventModal(event) {
  const p = event.extendedProps;

  modalBody.innerHTML = `
    <h2>${event.title}</h2>
    ${p.coursetitle ? `<p class="modal-subtitle">${p.coursetitle}</p>` : ""}

    <div class="modal-info">
      <p><strong>Section:</strong> ${p.section}</p>
      <p><strong>Type:</strong> ${p.component}</p>
      <p><strong>Time:</strong> ${formatTimeRange(event)}</p>
      <p><strong>Days:</strong> ${formatDays(event)}</p>
      <p><strong>Location:</strong> ${fmtLocation(p)}</p>
      <p><strong>Enrollment:</strong> ${p.enrollment}/${p.capacity}</p>
      ${p.waitlistCapacity > 0 ? `<p><strong>Waitlist:</strong> ${p.waitlist}/${p.waitlistCapacity}</p>` : ""}
    </div>
    <div class="modal-actions">
      <button onclick="highlightSameCourse('${p.subject}','${p.catalog}')" class="btn btn-primary">
        Show All Sections
      </button>
      <button onclick="filterByCourse('${p.subject}')" class="btn btn-ghost">
        Filter to ${p.subject}
      </button>
    </div>
  `;
  modal.classList.add("open");
}

function closeModal() {
  modal.classList.remove("open");
}

/* ------------------------------------------------------------------ */
/*  Formatting helpers                                                 */
/* ------------------------------------------------------------------ */

function fmtLocation(p) {
  const b = p.building, r = p.room;
  if (b && b !== "TBA" && r && r !== "TBA") return `${b}-${r}`;
  if (b && b !== "TBA") return b;
  if (r && r !== "TBA") return `Room ${r}`;
  return "TBA";
}

function formatTimeRange(event) {
  const rd = event._def?.recurringDef?.typeData;
  const st = rd?.startTime;
  const et = rd?.endTime;
  if (!st || !et) return "N/A";

  function ms2str(ms) {
    const totalMin = Math.floor(ms / 60000);
    let h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    const ampm = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    return `${h}:${String(m).padStart(2, "0")} ${ampm}`;
  }

  return `${ms2str(st.milliseconds)} - ${ms2str(et.milliseconds)}`;
}

function formatDays(event) {
  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const arr =
    event._def?.recurringDef?.typeData?.daysOfWeek || [];
  if (!arr.length) return "N/A";
  return arr.map((d) => dayNames[d]).join(", ");
}

/* ------------------------------------------------------------------ */
/*  Cross-event actions                                                */
/* ------------------------------------------------------------------ */

function highlightSameCourse(subject, catalog) {
  calendar.getEvents().forEach((ev) => {
    const p = ev.extendedProps;
    ev.setProp(
      "classNames",
      p.subject === subject && p.catalog === catalog
        ? ["highlight-course"]
        : []
    );
  });
  closeModal();
}

function filterByCourse(subject) {
  activeSubjectFilter = subject;
  subjectFilter.value = subject;
  filterInfo.textContent = `Showing ${subject} courses`;

  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.remove("active");
    if (b.dataset.filter === subject) b.classList.add("active");
  });

  applyFilters();
  closeModal();
}

/* ------------------------------------------------------------------ */
/*  Loading overlay                                                    */
/* ------------------------------------------------------------------ */

function showLoading(show) {
  loadingOverlay.classList.toggle("show", show);
}
