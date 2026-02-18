/**
 * Timetable - FullCalendar integration with sequence plan/term filtering.
 */

let calendar = null;
let filterOptions = null;
let activeSubjectFilter = "";
let activeSource = "scheduleterm"; // "scheduleterm" or "optimized"

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

function applyFilters() {
  showLoading(true);
  calendar.refetchEvents();
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
