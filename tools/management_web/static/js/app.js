/* ══════════════════════════════════════════════════════
   Management Web — SPA Controller
   Direct tool routing — no mode switching required
   ══════════════════════════════════════════════════════ */

'use strict';

// ─── Tool Definitions ────────────────────────────────────────────────────────
const TOOLS = {
  logging: {
    label:   'Logging',
    icon:    '📋',
    tabs: [
      { id: 'read',   label: 'Log Feed' },
      { id: 'write',  label: 'Write Entry' },
    ],
    actions: {
      read:  [{ label: 'Refresh', fn: 'loadLoggingFeed' }],
      write: [{ label: 'Submit', fn: 'submitLogEntry' }],
    },
  },
  reports: {
    label:   'Reports',
    icon:    '📄',
    tabs: [
      { id: 'entries',    label: 'Entries' },
      { id: 'categories', label: 'Categories' },
      { id: 'search',     label: 'Search' },
    ],
    actions: {
      entries:    [{ label: 'Refresh', fn: 'loadReportsEntries' }],
      categories: [{ label: 'Refresh', fn: 'loadReportsCategories' }],
      search:     [{ label: 'Search',  fn: 'runReportsSearch' }],
    },
  },
  notes: {
    label:   'Notes',
    icon:    '📝',
    tabs: [
      { id: 'list',       label: 'All Notes' },
      { id: 'categories', label: 'Categories' },
      { id: 'new',        label: 'New Note' },
      { id: 'search',     label: 'Search' },
    ],
    actions: {
      list:       [{ label: 'Refresh', fn: 'loadNotesList' }],
      categories: [{ label: 'Refresh', fn: 'loadNotesCategories' }],
      new:        [{ label: 'Save',    fn: 'submitNewNote' }],
      search:     [{ label: 'Search',  fn: 'runNotesSearch' }],
    },
  },
  jobs: {
    label:   'Jobs',
    icon:    '⚙️',
    tabs: [
      { id: 'active',      label: 'Active' },
      { id: 'completed',   label: 'Completed' },
      { id: 'maintenance', label: 'Maintenance' },
      { id: 'search',      label: 'Search' },
    ],
    actions: {
      active:      [{ label: 'Refresh', fn: 'loadJobsActive' }],
      completed:   [{ label: 'Refresh', fn: 'loadJobsCompleted' }],
      maintenance: [{ label: 'Refresh', fn: 'loadJobsMaintenance' }],
      search:      [{ label: 'Search',  fn: 'runJobsSearch' }],
    },
  },
  reminders: {
    label:   'Reminders',
    icon:    '🔔',
    tabs: [
      { id: 'active',    label: 'Active' },
      { id: 'completed', label: 'History' },
      { id: 'add',       label: 'Add Reminder' },
    ],
    actions: {
      active:    [{ label: 'Refresh', fn: 'loadRemindersActive' }],
      completed: [{ label: 'Refresh', fn: 'loadRemindersCompleted' }],
      add:       [{ label: 'Add',     fn: 'submitReminder' }],
    },
  },
  environment: {
    label:   'Environment',
    icon:    '🌿',
    tabs: [
      { id: 'definitions', label: 'Definitions' },
      { id: 'secure',      label: 'Secure Vars' },
      { id: 'set',         label: 'Set Variable' },
    ],
    actions: {
      definitions: [{ label: 'Refresh', fn: 'loadEnvDefinitions' }],
      secure:      [{ label: 'Refresh', fn: 'loadEnvSecure' }],
      set:         [{ label: 'Set',     fn: 'submitEnvSet' }],
    },
  },
  blogger: {
    label:   'Blogger',
    icon:    '✍️',
    tabs: [
      { id: 'info',    label: 'Blog Info' },
      { id: 'posts',   label: 'Posts' },
      { id: 'publish', label: 'Publish' },
    ],
    actions: {
      info:    [{ label: 'Refresh', fn: 'loadBloggerInfo' }],
      posts:   [{ label: 'Refresh', fn: 'loadBloggerPosts' }],
      publish: [{ label: 'Publish', fn: 'submitBloggerPublish' }],
    },
  },
};

// ─── State ───────────────────────────────────────────────────────────────────
let currentTool = '';
let currentTab  = '';

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  applyStoredTheme();
  const bodyTool = document.body.dataset.activeTool || 'logging';
  const bodyTab  = document.body.dataset.activeTab  || '';
  switchTool(bodyTool, bodyTab, true);
  loadBadges();
});

// ─── Sidebar ─────────────────────────────────────────────────────────────────
function openSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('sidebar-backdrop').classList.add('open');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-backdrop').classList.remove('open');
}

// ─── Settings ────────────────────────────────────────────────────────────────
function toggleSettings() {
  document.getElementById('settings-overlay').classList.toggle('hidden');
}
function setTheme(val) {
  document.documentElement.dataset.theme = val;
  localStorage.setItem('mgmt_theme', val);
}
function applyStoredTheme() {
  const saved = localStorage.getItem('mgmt_theme') || 'dark';
  document.documentElement.dataset.theme = saved;
  const sel = document.getElementById('theme-select');
  if (sel) sel.value = saved;
}

// ─── Tool Switcher ────────────────────────────────────────────────────────────
function switchTool(toolId, tabId, skipClose) {
  if (!TOOLS[toolId]) return;
  if (!skipClose) closeSidebar();

  currentTool = toolId;
  const def = TOOLS[toolId];
  const resolvedTab = tabId || def.tabs[0].id;
  currentTab = resolvedTab;

  // Update sidebar active state
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.tool === toolId);
  });

  // Update header title
  document.getElementById('app-title').textContent = def.label;

  // Build subnav tabs
  renderSubnav(toolId, resolvedTab);

  // Hide splash, render panel
  const splash = document.getElementById('splash');
  if (splash) splash.style.display = 'none';
  renderTabContent(toolId, resolvedTab);

  // Push history
  history.replaceState({}, '', `/${toolId}/${resolvedTab}`);
}

// ─── Subnav Builder ───────────────────────────────────────────────────────────
function renderSubnav(toolId, activeTab) {
  const def = TOOLS[toolId];
  const subnav  = document.getElementById('tool-subnav');
  const tabsEl  = document.getElementById('subnav-tabs');
  const actionsEl = document.getElementById('subnav-actions');

  // Tabs
  tabsEl.innerHTML = def.tabs.map(t =>
    `<button class="tab-btn${t.id === activeTab ? ' active' : ''}"
      onclick="switchTab('${t.id}')">${t.label}</button>`
  ).join('');

  // Actions for active tab
  const tabActions = (def.actions || {})[activeTab] || [];
  actionsEl.innerHTML = tabActions.map(a =>
    `<button class="action-btn" onclick="${a.fn}()">${a.label}</button>`
  ).join('');

  subnav.classList.remove('hidden');
}

function switchTab(tabId) {
  currentTab = tabId;
  // Update tab active class
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.toggle('active', b.textContent.trim() === TOOLS[currentTool].tabs.find(t => t.id === tabId)?.label);
  });
  // Rebuild actions
  const def = TOOLS[currentTool];
  const actionsEl = document.getElementById('subnav-actions');
  const tabActions = (def.actions || {})[tabId] || [];
  actionsEl.innerHTML = tabActions.map(a =>
    `<button class="action-btn" onclick="${a.fn}()">${a.label}</button>`
  ).join('');
  renderTabContent(currentTool, tabId);
  history.replaceState({}, '', `/${currentTool}/${tabId}`);
}

// ─── Main Content Router ──────────────────────────────────────────────────────
function renderTabContent(toolId, tabId) {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading…</div>`;

  const router = {
    logging:     { read: loadLoggingFeed,     write: renderLoggingWrite },
    reports:     { entries: loadReportsEntries, categories: loadReportsCategories, search: renderReportsSearch },
    notes:       { list: loadNotesList, categories: loadNotesCategories, new: renderNotesNew, search: renderNotesSearch },
    jobs:        { active: loadJobsActive, completed: loadJobsCompleted, maintenance: loadJobsMaintenance, search: renderJobsSearch },
    reminders:   { active: loadRemindersActive, completed: loadRemindersCompleted, add: renderReminderAdd },
    environment: { definitions: loadEnvDefinitions, secure: loadEnvSecure, set: renderEnvSet },
    blogger:     { info: loadBloggerInfo, posts: loadBloggerPosts, publish: renderBloggerPublish },
  };

  const fn = router[toolId]?.[tabId];
  if (fn) fn();
  else main.innerHTML = `<div class="empty-state">Panel "${toolId}/${tabId}" not found.</div>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// LOGGING
// ═══════════════════════════════════════════════════════════════════════════════
async function loadLoggingFeed() {
  const main = document.getElementById('app-main');
  const limit = document.getElementById('log-limit-setting')?.value || 50;
  main.innerHTML = `<div class="loading-state">Loading log feed…</div>`;
  const data = await api('/api/logging/read', { limit });
  main.innerHTML = `
    <div class="section-hdr"><h2>Log Feed</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(empty)')}</div>`;
}

function renderLoggingWrite() {
  document.getElementById('app-main').innerHTML = `
    <div class="section-hdr"><h2>Write Log Entry</h2></div>
    <div class="card">
      <div class="form-row"><label>Message</label>
        <textarea id="log-msg" placeholder="Log message…" rows="3"></textarea></div>
      <div class="form-row"><label>Level</label>
        <select id="log-level">
          <option>INFO</option><option>WARNING</option><option>ERROR</option><option>DEBUG</option>
        </select></div>
      <div class="form-row"><label>Priority (1-4)</label>
        <input type="number" id="log-pri" value="2" min="1" max="4"></div>
      <div class="form-row"><label>Category</label>
        <input type="text" id="log-cat" value="operational"></div>
    </div>`;
}

async function submitLogEntry() {
  const message  = document.getElementById('log-msg')?.value?.trim();
  const level    = document.getElementById('log-level')?.value;
  const priority = document.getElementById('log-pri')?.value;
  const category = document.getElementById('log-cat')?.value;
  if (!message) return toast('Message is required', 'error');
  const res = await apiPost('/api/logging/write', { message, level, priority, category });
  toast(res.ok ? 'Log entry saved' : (res.error || 'Failed'), res.ok ? 'ok' : 'error');
  if (res.ok) renderLoggingWrite();
}

// ═══════════════════════════════════════════════════════════════════════════════
// REPORTS
// ═══════════════════════════════════════════════════════════════════════════════
async function loadReportsEntries() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading entries…</div>`;
  const data = await api('/api/reports/list');
  main.innerHTML = `
    <div class="section-hdr"><h2>Report Entries</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(empty)')}</div>`;
}

async function loadReportsCategories() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading categories…</div>`;
  const data = await api('/api/reports/categories');
  main.innerHTML = `
    <div class="section-hdr"><h2>Categories</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(empty)')}</div>`;
}

function renderReportsSearch() {
  document.getElementById('app-main').innerHTML = `
    <div class="section-hdr"><h2>Search Reports</h2></div>
    <div class="search-row">
      <input type="text" id="reports-q" placeholder="Search term…" onkeydown="if(event.key==='Enter')runReportsSearch()">
      <button onclick="runReportsSearch()">Search</button>
    </div>
    <div id="reports-results"></div>`;
}

async function runReportsSearch() {
  const q = document.getElementById('reports-q')?.value?.trim();
  if (!q) return;
  document.getElementById('reports-results').innerHTML = `<div class="loading-state">Searching…</div>`;
  const data = await api('/api/reports/search', { q });
  document.getElementById('reports-results').innerHTML =
    `<div class="cli-output">${escHtml(data.output || data.error || '(no results)')}</div>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// NOTES
// ═══════════════════════════════════════════════════════════════════════════════
async function loadNotesList() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading notes…</div>`;
  const data = await api('/api/notes/list');
  main.innerHTML = `
    <div class="section-hdr"><h2>All Notes</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(no notes)')}</div>`;
}

async function loadNotesCategories() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading categories…</div>`;
  const data = await api('/api/notes/categories');
  main.innerHTML = `
    <div class="section-hdr"><h2>Categories</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(empty)')}</div>`;
}

function renderNotesNew() {
  document.getElementById('app-main').innerHTML = `
    <div class="section-hdr"><h2>New Note</h2></div>
    <div class="card">
      <div class="form-row"><label>Title</label>
        <input type="text" id="note-title" placeholder="Note title…"></div>
      <div class="form-row"><label>Category</label>
        <input type="text" id="note-cat" placeholder="Category name…"></div>
      <div class="form-row"><label>Content</label>
        <textarea id="note-content" rows="6" placeholder="Note content…"></textarea></div>
    </div>`;
}

async function submitNewNote() {
  const title   = document.getElementById('note-title')?.value?.trim();
  const content = document.getElementById('note-content')?.value?.trim();
  const category = document.getElementById('note-cat')?.value?.trim();
  if (!title || !content) return toast('Title and content required', 'error');
  const res = await apiPost('/api/notes/create', { title, content, category });
  toast(res.ok ? 'Note saved' : (res.error || 'Failed'), res.ok ? 'ok' : 'error');
  if (res.ok) renderNotesNew();
}

function renderNotesSearch() {
  document.getElementById('app-main').innerHTML = `
    <div class="section-hdr"><h2>Search Notes</h2></div>
    <div class="search-row">
      <input type="text" id="notes-q" placeholder="Search…" onkeydown="if(event.key==='Enter')runNotesSearch()">
      <button onclick="runNotesSearch()">Search</button>
    </div>
    <div id="notes-results"></div>`;
}

async function runNotesSearch() {
  const q = document.getElementById('notes-q')?.value?.trim();
  if (!q) return;
  document.getElementById('notes-results').innerHTML = `<div class="loading-state">Searching…</div>`;
  const data = await api('/api/notes/search', { q });
  document.getElementById('notes-results').innerHTML =
    `<div class="cli-output">${escHtml(data.output || data.error || '(no results)')}</div>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// JOBS
// ═══════════════════════════════════════════════════════════════════════════════
async function loadJobsActive() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading active jobs…</div>`;
  const data = await api('/api/jobs/list');
  main.innerHTML = `
    <div class="section-hdr"><h2>Active Jobs</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(no active jobs)')}</div>`;
}

async function loadJobsCompleted() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading completed jobs…</div>`;
  const data = await api('/api/jobs/completed');
  main.innerHTML = `
    <div class="section-hdr"><h2>Completed Jobs</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(none)')}</div>`;
}

async function loadJobsMaintenance() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading maintenance jobs…</div>`;
  const data = await api('/api/jobs/maintenance');
  main.innerHTML = `
    <div class="section-hdr"><h2>Maintenance Jobs</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(none)')}</div>`;
}

function renderJobsSearch() {
  document.getElementById('app-main').innerHTML = `
    <div class="section-hdr"><h2>Search Jobs</h2></div>
    <div class="search-row">
      <input type="text" id="jobs-q" placeholder="Search term…" onkeydown="if(event.key==='Enter')runJobsSearch()">
      <button onclick="runJobsSearch()">Search</button>
    </div>
    <div id="jobs-results"></div>`;
}

async function runJobsSearch() {
  const q = document.getElementById('jobs-q')?.value?.trim();
  if (!q) return;
  document.getElementById('jobs-results').innerHTML = `<div class="loading-state">Searching…</div>`;
  const data = await api('/api/jobs/search', { q });
  document.getElementById('jobs-results').innerHTML =
    `<div class="cli-output">${escHtml(data.output || data.error || '(no results)')}</div>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// REMINDERS
// ═══════════════════════════════════════════════════════════════════════════════
async function loadRemindersActive() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading reminders…</div>`;
  const data = await api('/api/reminders/list');
  const reminders = data.data?.active_reminders || [];

  if (!reminders.length) {
    main.innerHTML = `<div class="section-hdr"><h2>Active Reminders</h2></div><div class="empty-state">No active reminders.</div>`;
    return;
  }
  main.innerHTML = `
    <div class="section-hdr"><h2>Active Reminders (${reminders.length})</h2></div>
    ${reminders.map(r => `
      <div class="reminder-item" id="rem-${r.reminder_id}">
        <span class="priority-pill ${r.priority}">${r.priority.toUpperCase()}</span>
        <span class="reminder-text">${escHtml(r.reminder_text)}</span>
        <div class="reminder-actions">
          <button onclick="doneReminder('${r.reminder_id}')">Done</button>
          <button onclick="deleteReminder('${r.reminder_id}')">Delete</button>
        </div>
      </div>`).join('')}`;

  // Badge
  setBadge('reminders', reminders.length);
}

async function loadRemindersCompleted() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading history…</div>`;
  const data = await api('/api/reminders/list');
  const reminders = data.data?.completed_reminders || [];
  main.innerHTML = `
    <div class="section-hdr"><h2>Completed Reminders (${reminders.length})</h2></div>
    ${!reminders.length ? '<div class="empty-state">No history.</div>' :
      reminders.map(r => `
        <div class="reminder-item done">
          <span class="priority-pill ${r.priority || 'normal'}">${(r.priority || 'normal').toUpperCase()}</span>
          <span class="reminder-text">${escHtml(r.reminder_text)}</span>
          <span class="card-meta">${r.completion_date || ''}</span>
        </div>`).join('')}`;
}

function renderReminderAdd() {
  document.getElementById('app-main').innerHTML = `
    <div class="section-hdr"><h2>Add Reminder</h2></div>
    <div class="card">
      <div class="form-row"><label>Reminder text</label>
        <input type="text" id="rem-text" placeholder="What to remember…"></div>
      <div class="form-row"><label>Priority</label>
        <select id="rem-priority">
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select></div>
    </div>`;
}

async function submitReminder() {
  const text     = document.getElementById('rem-text')?.value?.trim();
  const priority = document.getElementById('rem-priority')?.value;
  if (!text) return toast('Reminder text required', 'error');
  const res = await apiPost('/api/reminders/add', { text, priority });
  toast(res.ok ? 'Reminder added' : (res.error || 'Failed'), res.ok ? 'ok' : 'error');
  if (res.ok) renderReminderAdd();
}

async function doneReminder(id) {
  const res = await apiPost('/api/reminders/done', { id });
  toast(res.ok ? 'Marked done' : (res.error || 'Failed'), res.ok ? 'ok' : 'error');
  if (res.ok) loadRemindersActive();
}

async function deleteReminder(id) {
  const res = await apiPost('/api/reminders/delete', { id });
  toast(res.ok ? 'Deleted' : (res.error || 'Failed'), res.ok ? 'ok' : 'error');
  if (res.ok) loadRemindersActive();
}

// ═══════════════════════════════════════════════════════════════════════════════
// ENVIRONMENT
// ═══════════════════════════════════════════════════════════════════════════════
async function loadEnvDefinitions() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading definitions…</div>`;
  const data = await api('/api/environment/list', { store: 'definitions' });
  main.innerHTML = `
    <div class="section-hdr"><h2>Definitions</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(empty)')}</div>`;
}

async function loadEnvSecure() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading secure vars…</div>`;
  const data = await api('/api/environment/list', { store: 'secure' });
  main.innerHTML = `
    <div class="section-hdr"><h2>Secure Variables</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(empty)')}</div>`;
}

function renderEnvSet() {
  document.getElementById('app-main').innerHTML = `
    <div class="section-hdr"><h2>Set Variable</h2></div>
    <div class="card">
      <div class="form-row"><label>Variable name</label>
        <input type="text" id="env-name" placeholder="VAR_NAME"></div>
      <div class="form-row"><label>Value</label>
        <input type="text" id="env-value" placeholder="value"></div>
      <div class="form-row"><label>Type</label>
        <select id="env-type">
          <option value="string">string</option>
          <option value="Path">Path</option>
          <option value="secret">secret</option>
          <option value="boolean">boolean</option>
          <option value="integer">integer</option>
        </select></div>
      <div class="form-row"><label>Description</label>
        <input type="text" id="env-desc" placeholder="Optional description"></div>
      <div class="form-row">
        <label style="flex-direction:row;align-items:center;gap:8px">
          <input type="checkbox" id="env-secure"> Store in secure env
        </label>
      </div>
    </div>`;
}

async function submitEnvSet() {
  const name   = document.getElementById('env-name')?.value?.trim();
  const value  = document.getElementById('env-value')?.value?.trim();
  const type   = document.getElementById('env-type')?.value;
  const desc   = document.getElementById('env-desc')?.value?.trim();
  const secure = document.getElementById('env-secure')?.checked;
  if (!name || !value) return toast('Name and value required', 'error');
  const res = await apiPost('/api/environment/set', { name, value, type, desc, secure });
  toast(res.ok ? `${name} set` : (res.error || 'Failed'), res.ok ? 'ok' : 'error');
  if (res.ok) loadEnvDefinitions();
}

// ═══════════════════════════════════════════════════════════════════════════════
// BLOGGER
// ═══════════════════════════════════════════════════════════════════════════════
async function loadBloggerInfo() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading blog info…</div>`;
  const data = await api('/api/blogger/info');
  main.innerHTML = `
    <div class="section-hdr"><h2>Blog Info</h2></div>
    <div class="cli-output">${escHtml(data.output || data.error || '(unavailable)')}</div>`;
}

async function loadBloggerPosts() {
  const main = document.getElementById('app-main');
  main.innerHTML = `<div class="loading-state">Loading posts…</div>`;
  const data = await api('/api/blogger/posts', { limit: 20 });

  // Parse the CLI output lines into structured rows
  const rawLines = (data.output || '').split('\n');
  const postLines = rawLines.filter(l => /^\s+\[\d+\]/.test(l));
  const datelines = rawLines.filter(l => /^\s+\d{4}-\d{2}-\d{2}/.test(l));

  if (!postLines.length) {
    main.innerHTML = `
      <div class="section-hdr"><h2>Posts</h2></div>
      <div class="cli-output">${escHtml(data.output || data.error || '(no posts)')}</div>`;
    return;
  }

  const rows = postLines.map((line, i) => {
    const numMatch   = line.match(/\[(\d+)\]/);
    const titleMatch = line.match(/\]\s+(.+)$/);
    const dateLine   = datelines[i] || '';
    const dateMatch  = dateLine.match(/(\d{4}-\d{2}-\d{2})/);
    const idMatch    = dateLine.match(/ID:\s*(\d+)/);
    return {
      num:   numMatch?.[1]  || i + 1,
      title: titleMatch?.[1]?.trim() || line.trim(),
      date:  dateMatch?.[1] || '',
      id:    idMatch?.[1]   || '',
    };
  });

  main.innerHTML = `
    <div class="section-hdr"><h2>Recent Posts (${rows.length})</h2></div>
    ${rows.map(p => `
      <div class="post-row">
        <span class="post-num">${p.num}</span>
        <span class="post-title">${escHtml(p.title)}</span>
        <span class="post-date">${p.date}</span>
        ${p.id ? `<button class="post-del" title="Delete post" onclick="deleteBlogPost('${p.id}', this)">🗑</button>` : ''}
      </div>`).join('')}`;
}

async function deleteBlogPost(id, btn) {
  if (!confirm(`Delete post ${id}?`)) return;
  btn.textContent = '…';
  const res = await apiPost('/api/blogger/delete', { id });
  toast(res.ok ? 'Post deleted' : (res.error || 'Failed'), res.ok ? 'ok' : 'error');
  if (res.ok) loadBloggerPosts();
}

function renderBloggerPublish() {
  document.getElementById('app-main').innerHTML = `
    <div class="section-hdr"><h2>Publish to Blogger</h2></div>
    <div class="card">
      <div class="form-row"><label>File path (.md or .html)</label>
        <input type="text" id="pub-file" placeholder="/path/to/document.md"></div>
      <div class="form-row"><label>Post title (optional)</label>
        <input type="text" id="pub-title" placeholder="Leave empty to auto-detect"></div>
      <div class="form-row"><label>Labels (comma-separated)</label>
        <input type="text" id="pub-labels" placeholder="BEJSON, Tech"></div>
      <div class="form-row">
        <label style="flex-direction:row;align-items:center;gap:8px">
          <input type="checkbox" id="pub-style"> Apply BECSS Tri-Color styling
        </label>
      </div>
      <div class="form-row"><label>Theme</label>
        <select id="pub-theme"><option value="light">Light</option><option value="dark">Dark</option></select></div>
      <div class="form-row">
        <label style="flex-direction:row;align-items:center;gap:8px">
          <input type="checkbox" id="pub-draft"> Save as draft
        </label>
      </div>
    </div>
    <div id="pub-result"></div>`;
}

async function submitBloggerPublish() {
  const file   = document.getElementById('pub-file')?.value?.trim();
  const title  = document.getElementById('pub-title')?.value?.trim();
  const labels = (document.getElementById('pub-labels')?.value || '')
    .split(',').map(s => s.trim()).filter(Boolean);
  const style  = document.getElementById('pub-style')?.checked;
  const theme  = document.getElementById('pub-theme')?.value;
  const draft  = document.getElementById('pub-draft')?.checked;
  if (!file) return toast('File path required', 'error');
  document.getElementById('pub-result').innerHTML = `<div class="loading-state">Publishing…</div>`;
  const res = await apiPost('/api/blogger/publish', { file, title, labels, style, theme, draft });
  document.getElementById('pub-result').innerHTML =
    `<div class="cli-output">${escHtml(res.output || res.error || '')}</div>`;
  toast(res.ok ? 'Published!' : (res.error || 'Failed'), res.ok ? 'ok' : 'error');
}

// ═══════════════════════════════════════════════════════════════════════════════
// Badge Loader
// ═══════════════════════════════════════════════════════════════════════════════
async function loadBadges() {
  try {
    const data = await api('/api/reminders/list');
    const count = data.data?.active_reminders?.length || 0;
    setBadge('reminders', count);
  } catch (e) { /* silent */ }
}

function setBadge(tool, count) {
  const el = document.getElementById(`badge-${tool}`);
  if (!el) return;
  if (count > 0) {
    el.textContent = count;
    el.classList.add('visible');
  } else {
    el.classList.remove('visible');
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════════════
async function api(endpoint, params = {}) {
  const url = new URL(endpoint, location.origin);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const res = await fetch(url.toString());
  return res.json().catch(() => ({ ok: false, error: 'JSON parse error' }));
}

async function apiPost(endpoint, body = {}) {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json().catch(() => ({ ok: false, error: 'JSON parse error' }));
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

let toastTimer;
function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add('hidden'), 3000);
}
