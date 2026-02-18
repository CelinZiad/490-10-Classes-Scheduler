async function loadWaitlistStats(){
  const container = document.getElementById('waitlist-table-container');
  container.innerHTML = 'Loading...';
  try{
    const res = await fetch('/api/waitlist/stats');
    if(!res.ok) throw new Error('Failed to load');
    const data = await res.json();
    if(!data.length){
      container.innerHTML = '<p>No courses currently at waitlist capacity.</p>';
      return;
    }

    const table = document.createElement('table');
    table.className = 'simple-table';
    table.innerHTML = '<thead><tr><th>Subject</th><th>Catalog</th><th>Section</th><th>Waitlist</th><th>Capacity</th><th>Action</th></tr></thead>';
    const tbody = document.createElement('tbody');
    data.forEach(r=>{
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${r.subject}</td><td>${r.catalog}</td><td>${r.section||''}</td><td>${r.waitlist}</td><td>${r.waitlistCapacity}</td><td><button class="btn btn-ghost" data-subject="${r.subject}" data-catalog="${r.catalog}">Process</button></td>`;
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
        // load candidate students for this course
        loadCourseStudents(subject, catalog);
      });
    });

  }catch(e){
    container.innerHTML = '<p>Error loading data.</p>';
    console.error(e);
  }
}

function parseStudentsInput(val){
  if(!val) return [];
  return val.split(',').map(s=>s.trim()).filter(s=>s).map(s=>parseInt(s,10)).filter(n=>!Number.isNaN(n));
}

async function runWaitlist(){
  const subject = document.getElementById('wl-subject').value.trim().toUpperCase();
  const catalog = document.getElementById('wl-catalog').value.trim();
  const studentsRaw = document.getElementById('wl-students').value;
  const students = parseStudentsInput(studentsRaw);
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
    resultEl.innerHTML = '<p class="status status-warning">Enter at least one student id.</p>';
    return;
  }

  resultEl.innerHTML = '<p>Running algorithm...</p>';
  resultEl.style.display = '';
  document.getElementById('wl-progress').value = 20;

  try{
    // use timeout for fetch so UI doesn't hang indefinitely
    const controller = new AbortController();
    const id = setTimeout(()=>controller.abort(), 20000);
    const res = await fetch('/api/waitlist/run', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({subject, catalog, students}),
      signal: controller.signal,
    });
    clearTimeout(id);
    document.getElementById('wl-progress').value = 60;

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

    // Show results summary
    let html = `<h3>Proposed slots</h3>`;
    if(!data.results || Object.keys(data.results).length===0){
      html += '<p>No available slots found.</p>';
    }else{
      html += '<ul>';
      for(const k of Object.keys(data.results).sort()){
        html += `<li>${k}: ${data.results[k].join(', ')}</li>`;
      }
      html += '</ul>';
    }
    html += `<p><a href="/api/waitlist/download?subject=${encodeURIComponent(subject)}&catalog=${encodeURIComponent(catalog)}">Download CSV of results</a></p>`;
    resultEl.innerHTML = html;
    document.getElementById('wl-progress').value = 100;

    // reload stats
    loadWaitlistStats();
  }catch(e){
    resultEl.innerHTML = '<p class="status status-error">Unexpected error.</p>';
    console.error(e);
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  loadWaitlistStats();
  document.getElementById('wl-run').addEventListener('click', runWaitlist);
  document.getElementById('wl-add-selected').addEventListener('click', ()=>{
    const checked = Array.from(document.querySelectorAll('#wl-students-list input[type=checkbox]:checked'))
      .map(i=>i.dataset.studyid);
    const input = document.getElementById('wl-students');
    const existing = parseStudentsInput(input.value);
    const merged = Array.from(new Set(existing.concat(checked.map(s=>parseInt(s,10)))));
    input.value = merged.join(',');
  });
});

async function loadCourseStudents(subject, catalog){
  const panel = document.getElementById('wl-students-panel');
  const list = document.getElementById('wl-students-list');
  panel.style.display = 'none';
  list.innerHTML = 'Loading...';
  try{
    const res = await fetch(`/api/waitlist/students?subject=${encodeURIComponent(subject)}&catalog=${encodeURIComponent(catalog)}`);
    if(!res.ok) throw new Error('no students');
    const data = await res.json();
    if(!data.length){
      list.innerHTML = '<p>No candidate students found.</p>';
      panel.style.display = '';
      return;
    }
    list.innerHTML = '';
    data.forEach(s=>{
      const el = document.createElement('div');
      el.style.padding = '6px 4px';
      el.innerHTML = `<label style="display:flex; gap:8px; align-items:center;"><input type="checkbox" data-studyid="${s.studyid}"/> <strong>${s.studyid}</strong> — ${s.studyname||'(no name)'} </label>`;
      list.appendChild(el);
    });
    panel.style.display = '';
  }catch(e){
    list.innerHTML = '<p>Error loading students.</p>';
    panel.style.display = '';
  }
}
