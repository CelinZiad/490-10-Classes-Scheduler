/**
 * Timetable JavaScript - FullCalendar Integration
 */

// Global state
let calendar = null;
let filterOptions = null;

// ECE subjects for quick filter
const ECE_SUBJECTS = ['COEN', 'ELEC', 'COMP', 'SOEN'];

// DOM elements
const termFilter = document.getElementById('term-filter');
const subjectFilter = document.getElementById('subject-filter');
const componentFilter = document.getElementById('component-filter');
const buildingFilter = document.getElementById('building-filter');
const applyBtn = document.getElementById('apply-filters');
const clearBtn = document.getElementById('clear-filters');
const eventCount = document.getElementById('event-count');
const filterInfo = document.getElementById('filter-info');
const modal = document.getElementById('event-modal');
const modalBody = document.getElementById('modal-body');
const loadingOverlay = document.getElementById('loading-overlay');

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', async () => {
  showLoading(true);

  try {
    // Load filter options first
    await loadFilters();

    // Initialize FullCalendar
    initCalendar();

    // Set up event listeners
    setupEventListeners();

    // Apply default ECE filter
    applyQuickFilter('ECE');
  } catch (error) {
    console.error('Failed to initialize timetable:', error);
    eventCount.textContent = 'Error loading timetable';
  } finally {
    showLoading(false);
  }
});

/**
 * Load filter options from API
 */
async function loadFilters() {
  const response = await fetch('/api/filters');
  filterOptions = await response.json();

  // Populate term dropdown
  termFilter.innerHTML = filterOptions.terms.map((t, i) =>
    `<option value="${t.code}" ${i === 0 ? 'selected' : ''}>${t.name}</option>`
  ).join('');

  // Populate subject dropdown
  subjectFilter.innerHTML = '<option value="">All Subjects</option>' +
    filterOptions.subjects.map(s => `<option value="${s}">${s}</option>`).join('');

  // Populate component dropdown
  componentFilter.innerHTML = '<option value="">All Types</option>' +
    filterOptions.components.map(c => `<option value="${c}">${c}</option>`).join('');

  // Populate building dropdown
  buildingFilter.innerHTML = '<option value="">All Buildings</option>' +
    filterOptions.buildings.map(b => `<option value="${b}">${b}</option>`).join('');
}

/**
 * Initialize FullCalendar
 */
function initCalendar() {
  const calendarEl = document.getElementById('calendar');

  calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'timeGridWeek',

    // Time range: 8:00 AM to 9:00 PM (university hours)
    slotMinTime: '08:00:00',
    slotMaxTime: '21:00:00',
    slotDuration: '00:15:00',

    // Week settings
    weekends: false,  // Mon-Fri only
    firstDay: 1,      // Start on Monday

    // Header toolbar
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'timeGridWeek,timeGridDay,listWeek'
    },

    // Events from API
    events: {
      url: '/api/events',
      method: 'GET',
      extraParams: getFilterParams,
      failure: () => {
        eventCount.textContent = 'Error loading events';
      }
    },

    // Event rendering
    eventDidMount: (info) => {
      // Add tooltip
      info.el.title = `${info.event.title}\n${info.event.extendedProps.building}-${info.event.extendedProps.room}`;
    },

    // Event click handler
    eventClick: (info) => {
      showEventModal(info.event);
    },

    // Update stats when events load
    eventsSet: (events) => {
      updateStats(events);
    },

    // Visual options
    nowIndicator: true,
    allDaySlot: false,
    expandRows: true,
    stickyHeaderDates: true,
    dayHeaderFormat: { weekday: 'short' },
    slotLabelFormat: {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    }
  });

  calendar.render();
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
  // Apply filters button
  applyBtn.addEventListener('click', applyFilters);

  // Clear filters button
  clearBtn.addEventListener('click', clearFilters);

  // Quick filter tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const filter = e.target.dataset.filter;
      applyQuickFilter(filter);
    });
  });

  // Modal close
  document.querySelector('.modal-close').addEventListener('click', closeModal);
  document.querySelector('.modal-backdrop').addEventListener('click', closeModal);

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });
}

/**
 * Get current filter parameters
 */
function getFilterParams() {
  const params = {
    term: termFilter.value
  };

  if (subjectFilter.value) {
    params.subject = subjectFilter.value;
  }

  if (componentFilter.value) {
    params.component = componentFilter.value;
  }

  if (buildingFilter.value) {
    params.building = buildingFilter.value;
  }

  return params;
}

/**
 * Apply filters
 */
function applyFilters() {
  showLoading(true);
  calendar.refetchEvents();
  setTimeout(() => showLoading(false), 500);
}

/**
 * Clear all filters
 */
function clearFilters() {
  subjectFilter.value = '';
  componentFilter.value = '';
  buildingFilter.value = '';

  // Reset quick tabs
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelector('[data-filter="all"]').classList.add('active');

  applyFilters();
}

/**
 * Apply quick filter
 */
function applyQuickFilter(filter) {
  // Update active tab
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelector(`[data-filter="${filter}"]`).classList.add('active');

  // Set subject filter
  if (filter === 'all') {
    subjectFilter.value = '';
    filterInfo.textContent = '';
  } else if (filter === 'ECE') {
    // ECE includes COEN, ELEC, COMP, SOEN
    subjectFilter.value = ECE_SUBJECTS.join(',');
    filterInfo.textContent = 'Showing ECE subjects (COEN, ELEC, COMP, SOEN)';
  } else {
    subjectFilter.value = filter;
    filterInfo.textContent = `Showing ${filter} courses`;
  }

  applyFilters();
}

/**
 * Update stats display
 */
function updateStats(events) {
  const count = events.length;
  eventCount.textContent = `${count} class${count !== 1 ? 'es' : ''} displayed`;
}

/**
 * Show event modal
 */
function showEventModal(event) {
  const props = event.extendedProps;

  modalBody.innerHTML = `
    <h2>${event.title}</h2>
    <div class="modal-info">
      <p><strong>Course:</strong> ${props.subject} ${props.catalog}</p>
      <p><strong>Section:</strong> ${props.section}</p>
      <p><strong>Type:</strong> ${props.component}</p>
      <p><strong>Time:</strong> ${formatTimeRange(event)}</p>
      <p><strong>Days:</strong> ${formatDays(event.daysOfWeek || event._def?.recurringDef?.typeData?.daysOfWeek || [])}</p>
      <p><strong>Location:</strong> ${props.building}-${props.room}</p>
      <p><strong>Enrollment:</strong> ${props.enrollment}/${props.capacity}</p>
      ${props.waitlistCapacity > 0 ? `<p><strong>Waitlist:</strong> ${props.waitlist}/${props.waitlistCapacity}</p>` : ''}
    </div>
    <div class="modal-actions">
      <button onclick="highlightSameCourse('${props.subject}', '${props.catalog}')" class="btn btn-primary">
        Show All Sections
      </button>
      <button onclick="filterByCourse('${props.subject}')" class="btn btn-ghost">
        Filter to ${props.subject}
      </button>
    </div>
  `;

  modal.classList.add('open');
}

/**
 * Close modal
 */
function closeModal() {
  modal.classList.remove('open');
}

/**
 * Format time range
 */
function formatTimeRange(event) {
  const startTime = event.startStr || event._def?.recurringDef?.typeData?.startTime || 'N/A';
  const endTime = event.endStr || event._def?.recurringDef?.typeData?.endTime || 'N/A';

  // Format HH:MM:SS to readable time
  const formatTime = (time) => {
    if (!time || time === 'N/A') return 'N/A';
    const [hours, minutes] = time.split(':');
    const h = parseInt(hours);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const hour12 = h % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
  };

  return `${formatTime(startTime)} - ${formatTime(endTime)}`;
}

/**
 * Format days array to readable string
 */
function formatDays(daysArray) {
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  if (!daysArray || daysArray.length === 0) return 'N/A';
  return daysArray.map(d => dayNames[d]).join(', ');
}

/**
 * Highlight all sections of a course
 */
function highlightSameCourse(subject, catalog) {
  const events = calendar.getEvents();
  events.forEach(event => {
    const props = event.extendedProps;
    if (props.subject === subject && props.catalog === catalog) {
      event.setProp('classNames', ['conflict-highlight']);
    } else {
      event.setProp('classNames', []);
    }
  });
  closeModal();
}

/**
 * Filter to specific subject
 */
function filterByCourse(subject) {
  subjectFilter.value = subject;
  filterInfo.textContent = `Showing ${subject} courses`;

  // Update quick tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.dataset.filter === subject) btn.classList.add('active');
  });

  applyFilters();
  closeModal();
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
  if (show) {
    loadingOverlay.classList.add('show');
  } else {
    loadingOverlay.classList.remove('show');
  }
}
