let currentSource = 'scheduleterm';

async function loadWaitlistStats(){
  const container = document.getElementById('waitlist-table-container');
  container.innerHTML = 'Loading...';
  try{
    const res = await fetch(`/api/waitlist/stats?source=${currentSource}`);
    if(!res.ok) throw new Error('Failed to load');
    const data = await res.json();
    if(!data.length){
      container.innerHTML = '<p>No courses found.</p>';
      return;
    }

    const table = document.createElement('table');
    table.className = 'data-table';

    if(currentSource === 'optimized'){
      table.innerHTML = '<thead><tr><th>Subject</th><th>Catalog</th><th>Section</th><th>Component</th><th>Action</th></tr></thead>';
    } else {
      table.innerHTML = '<thead><tr><th>Subject</th><th>Catalog</th><th>Section</th><th>Waitlist</th><th>Capacity</th><th>Action</th></tr></thead>';
    }

    const tbody = document.createElement('tbody');
    data.forEach(r=>{
      const tr = document.createElement('tr');
      if(currentSource === 'optimized'){
        tr.innerHTML = `<td>${r.subject}</td><td>${r.catalog}</td><td>${r.section||''}</td><td>${r.component||''}</td><td><button class="btn btn-ghost" data-subject="${r.subject}" data-catalog="${r.catalog}">Process</button></td>`;
      } else {
        tr.innerHTML = `<td>${r.subject}</td><td>${r.catalog}</td><td>${r.section||''}</td><td>${r.waitlist}</td><td>${r.waitlistCapacity}</td><td><button class="btn btn-ghost" data-subject="${r.subject}" data-catalog="${r.catalog}">Process</button></td>`;
      }
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    container.innerHTML = '';
    container.appendChild(table);

    container.querySelectorAll('button[data-subject]').forEach(b=>{
      b.addEventListener('click', ()=>{
        const subject = b.dataset.subject;
        const catalog = b.dataset.catalog;
        document.getElementById('wl-subject').value = subject;
        document.getElementById('wl-catalog').value = catalog;
        loadStudentsDropdown(subject, catalog);
      });
    });

  }catch(e){
    container.innerHTML = '<p>Error loading data.</p>';
    console.error(e);
  }
}

function getSelectedStudents(){
  const sel = document.getElementById('wl-students');
  return Array.from(sel.selectedOptions).map(o => parseInt(o.value, 10)).filter(n => !Number.isNaN(n));
}

async function runWaitlist(){
  const subject = document.getElementById('wl-subject').value.trim().toUpperCase();
  const catalog = document.getElementById('wl-catalog').value.trim();
  const students = getSelectedStudents();
  const resultEl = document.getElementById('wl-result');
  resultEl.style.display = 'none';
  resultEl.innerHTML = '';

  if(!subject || !catalog){
    resultEl.style.display = '';
    resultEl.innerHTML = '<p class="status status-warning">Enter subject and catalog.</p>';
    return;
  }
  if(!students.length){
    resultEl.style.display = '';
    resultEl.innerHTML = '<p class="status status-warning">Select at least one student.</p>';
    return;
  }

  resultEl.innerHTML = '<p>Running algorithm...</p>';
  resultEl.style.display = '';

  try{
    const controller = new AbortController();
    const id = setTimeout(()=>controller.abort(), 20000);
    const res = await fetch('/api/waitlist/run', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({subject, catalog, students}),
      signal: controller.signal,
    });
    clearTimeout(id);

    let data;
    try{
      data = await res.json();
    }catch(err){
      const txt = await res.text().catch(()=>'<non-json response>');
      resultEl.innerHTML = `<p class="status status-error">Server returned non-JSON response: ${txt}</p>`;
      console.error('Non-JSON response', txt);
      return;
    }
    if(!res.ok){
      resultEl.innerHTML = `<p class="status status-error">Error: ${data.error||'unknown'}</p>`;
      return;
    }

    let html = '<h3>Proposed Lab Slots</h3>';
    if(!data.results || data.results.length === 0){
      html += '<p>No available slots found.</p>';
    } else {
      html += '<table class="data-table"><thead><tr><th>Day</th><th>Time Slot</th><th>Available Students</th></tr></thead><tbody>';
      for(const slot of data.results){
        html += `<tr><td>${slot.day}</td><td>${slot.time}</td><td>${slot.students.join(', ')}</td></tr>`;
      }
      html += '</tbody></table>';
    }
    html += `<p style="margin-top:12px;"><a href="/api/waitlist/download?subject=${encodeURIComponent(subject)}&catalog=${encodeURIComponent(catalog)}">Download CSV of results</a></p>`;
    resultEl.innerHTML = html;

    loadWaitlistStats();
  }catch(e){
    resultEl.innerHTML = '<p class="status status-error">Unexpected error.</p>';
    console.error(e);
  }
}

async function loadStudentsDropdown(subject, catalog){
  const sel = document.getElementById('wl-students');
  sel.innerHTML = '<option disabled>Loading...</option>';

  // Also show the candidate panel
  const panel = document.getElementById('wl-students-panel');
  const list = document.getElementById('wl-students-list');
  panel.style.display = 'none';
  list.innerHTML = 'Loading...';

  try{
    const res = await fetch(`/api/waitlist/students?subject=${encodeURIComponent(subject)}&catalog=${encodeURIComponent(catalog)}`);
    if(!res.ok) throw new Error('no students');
    const data = await res.json();

    if(!data.length){
      sel.innerHTML = '<option disabled>No students found for this course</option>';
      list.innerHTML = '<p>No candidate students found.</p>';
      panel.style.display = '';
      return;
    }

    // Populate dropdown
    sel.innerHTML = '';
    data.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.studyid;
      opt.textContent = `${s.studyid} — ${s.studyname || '(no name)'}`;
      sel.appendChild(opt);
    });

    // Populate checkbox panel
    list.innerHTML = '';
    data.forEach(s => {
      const el = document.createElement('div');
      el.style.padding = '6px 4px';
      el.innerHTML = `<label style="display:flex; gap:8px; align-items:center;"><input type="checkbox" data-studyid="${s.studyid}"/> <strong>${s.studyid}</strong> — ${s.studyname||'(no name)'} </label>`;
      list.appendChild(el);
    });
    panel.style.display = '';
  }catch(e){
    sel.innerHTML = '<option disabled>Error loading students</option>';
    list.innerHTML = '<p>Error loading students.</p>';
    panel.style.display = '';
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  loadWaitlistStats();
  document.getElementById('wl-run').addEventListener('click', runWaitlist);

  // Source toggle
  document.getElementById('source-scheduleterm').addEventListener('click', ()=>{
    currentSource = 'scheduleterm';
    document.getElementById('source-scheduleterm').classList.add('active');
    document.getElementById('source-optimized').classList.remove('active');
    loadWaitlistStats();
  });
  document.getElementById('source-optimized').addEventListener('click', ()=>{
    currentSource = 'optimized';
    document.getElementById('source-optimized').classList.add('active');
    document.getElementById('source-scheduleterm').classList.remove('active');
    loadWaitlistStats();
  });

  // Add selected checkbox students to dropdown selection
  document.getElementById('wl-add-selected').addEventListener('click', ()=>{
    const checked = Array.from(document.querySelectorAll('#wl-students-list input[type=checkbox]:checked'))
      .map(i => i.dataset.studyid);
    const sel = document.getElementById('wl-students');
    Array.from(sel.options).forEach(opt => {
      if(checked.includes(opt.value)){
        opt.selected = true;
      }
    });
  });

  // Auto-load students when subject/catalog fields lose focus
  const subjectEl = document.getElementById('wl-subject');
  const catalogEl = document.getElementById('wl-catalog');
  catalogEl.addEventListener('blur', ()=>{
    const s = subjectEl.value.trim().toUpperCase();
    const c = catalogEl.value.trim();
    if(s && c) loadStudentsDropdown(s, c);
  });
});
