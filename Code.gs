// ============================================================
// Code.gs — Flowdesk Backend API (v11 — anti-destruction + GCal delete propagation)
// ============================================================
// Notes content → Google Drive files (no 50K limit)
// Events ↔ Google Calendar (bidirectional sync, delete propagation)
// Groups/Tasks/Members: anti-destruction guard — empty payloads NEVER wipe cloud
// ============================================================

// ⚠️ CHANGE THESE to your own secrets!
const API_KEY = 'gBjEq2sv1LBnFPDs-eqg2wDrcp3BBMpjQGa5ZWUmw_E';
const PIN = 'taiwanno1';

// Folder in Google Drive to store note files
const DRIVE_FOLDER_NAME = 'Flowdesk_Notes';

// Google Calendar name — uses default calendar if empty
const GCAL_NAME = 'Flowdesk';

function checkAuth(e) {
  const key = (e && e.parameter && e.parameter.key) || '';
  return key === API_KEY || key === PIN;
}

function doGet(e) {
  const action = (e && e.parameter && e.parameter.action) || '';
  if (action === 'ping') return json({ ok: true, version: 11 });
  if (!checkAuth(e)) return json({ error: 'Unauthorized', code: 401 });
  if (action === 'init') return json(initSheet());
  if (action === 'getTasks') return json(getAllData());
  if (action === 'getTasksLight') return json(getAllDataLight());
  if (action === 'getNoteContent') {
    const noteId = (e.parameter && e.parameter.noteId) || '';
    return json(getNoteContentById(noteId));
  }
  if (action === 'syncAll') {
    try {
      const data = JSON.parse(e.parameter.data);
      return json(syncAll(data));
    } catch (err) {
      return json({ error: 'syncAll failed: ' + err.message });
    }
  }
  return json({ error: 'Unknown action: ' + action });
}

function doPost(e) {
  try {
    const paramKey = (e && e.parameter && e.parameter.key) || '';
    const body = JSON.parse(e.postData.contents);
    const bodyKey = body.key || '';
    if (paramKey !== API_KEY && paramKey !== PIN && bodyKey !== API_KEY && bodyKey !== PIN) {
      return json({ error: 'Unauthorized', code: 401 });
    }
    const action = body.action;
    if (action === 'syncAll') return json(syncAll(body));
    return json({ error: 'Unknown action' });
  } catch (err) {
    return json({ error: err.message });
  }
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// ── Google Calendar helpers ──
function getFlowdeskCalendar() {
  // Try to find a calendar named GCAL_NAME
  if (GCAL_NAME) {
    const cals = CalendarApp.getCalendarsByName(GCAL_NAME);
    if (cals.length > 0) return cals[0];
    // Create it if it doesn't exist
    return CalendarApp.createCalendar(GCAL_NAME, { color: CalendarApp.Color.BLUE });
  }
  return CalendarApp.getDefaultCalendar();
}

function syncEventToGCal(ev, existingGcalId) {
  const cal = getFlowdeskCalendar();
  const dateStr = ev.date || '';
  if (!dateStr) return '';

  try {
    // Use noon to avoid DST boundary surprises around midnight
    const eventDate = new Date(dateStr + 'T12:00:00');
    let gcalEvent = null;

    // Try to update existing
    if (existingGcalId) {
      try { gcalEvent = cal.getEventById(existingGcalId); } catch(e) { gcalEvent = null; }
    }

    if (gcalEvent) {
      // Update existing event
      gcalEvent.setTitle(ev.title || 'Untitled');
      if (ev.allDay) {
        gcalEvent.setAllDayDate(eventDate);
      } else {
        const start = parseTime(dateStr, ev.startTime || '09:00');
        const end = parseTime(dateStr, ev.endTime || '10:00');
        gcalEvent.setTime(start, end);
      }
      // Update description if present
      if (typeof ev.description === 'string') {
        try { gcalEvent.setDescription(ev.description); } catch(e) {}
      }
      return existingGcalId;
    } else {
      // Create new event
      if (ev.allDay) {
        gcalEvent = cal.createAllDayEvent(ev.title || 'Untitled', eventDate);
      } else {
        const start = parseTime(dateStr, ev.startTime || '09:00');
        const end = parseTime(dateStr, ev.endTime || '10:00');
        gcalEvent = cal.createEvent(ev.title || 'Untitled', start, end);
      }
      // Tag it as Flowdesk event
      gcalEvent.setTag('flowdesk', 'true');
      gcalEvent.setTag('flowdesk_id', String(ev.id || ''));
      if (typeof ev.description === 'string' && ev.description) {
        try { gcalEvent.setDescription(ev.description); } catch(e) {}
      }
      return gcalEvent.getId();
    }
  } catch (e) {
    Logger.log('syncEventToGCal error: ' + e.message);
    return existingGcalId || '';
  }
}

function deleteGCalEvent(gcalId) {
  if (!gcalId) return false;
  try {
    const cal = getFlowdeskCalendar();
    const gev = cal.getEventById(gcalId);
    if (gev) {
      gev.deleteEvent();
      return true;
    }
  } catch (e) {
    Logger.log('deleteGCalEvent error for ' + gcalId + ': ' + e.message);
  }
  return false;
}

function parseTime(dateStr, timeStr) {
  const parts = (timeStr || '09:00').split(':');
  const h = parseInt(parts[0]) || 9;
  const m = parseInt(parts[1]) || 0;
  const d = new Date(dateStr + 'T00:00:00');
  d.setHours(h, m, 0, 0);
  return d;
}

function pullGCalEvents() {
  // Pull events from Google Calendar that are NOT already tracked by Flowdesk
  try {
    const cal = getFlowdeskCalendar();
    const now = new Date();
    const start = new Date(now.getTime() - 90 * 86400000);  // 90 days ago
    const end = new Date(now.getTime() + 365 * 86400000);   // 1 year ahead
    const gcalEvents = cal.getEvents(start, end);
    const pulled = [];
    const tz = Session.getScriptTimeZone();

    gcalEvents.forEach(ge => {
      const flowdeskTag = ge.getTag('flowdesk');
      if (flowdeskTag === 'true') return; // Skip events we pushed — avoid duplicates

      const isAllDay = ge.isAllDayEvent();
      const startDate = isAllDay ? ge.getAllDayStartDate() : ge.getStartTime();
      const endDate = isAllDay ? ge.getAllDayEndDate() : ge.getEndTime();

      // Use full GCal ID hash to avoid any potential collision from truncation
      const fullId = ge.getId();
      const shortId = fullId.replace(/@.*/, '');

      pulled.push({
        id: 'gcal_' + shortId,
        gcalId: fullId,
        title: ge.getTitle() || 'Untitled',
        date: Utilities.formatDate(startDate, tz, 'yyyy-MM-dd'),
        startTime: isAllDay ? '' : Utilities.formatDate(startDate, tz, 'HH:mm'),
        endTime: isAllDay ? '' : Utilities.formatDate(endDate, tz, 'HH:mm'),
        color: '#0073ea',
        allDay: isAllDay,
        description: (function(){ try { return ge.getDescription() || ''; } catch(e){ return ''; } })(),
        fromGCal: true
      });
    });

    return pulled;
  } catch (e) {
    Logger.log('pullGCalEvents error: ' + e.message);
    return [];
  }
}

// ── Drive helpers ──
function getNotesFolder() {
  const folders = DriveApp.getFoldersByName(DRIVE_FOLDER_NAME);
  if (folders.hasNext()) return folders.next();
  return DriveApp.createFolder(DRIVE_FOLDER_NAME);
}

function saveNoteToDrive(noteId, title, content, existingFileId) {
  const folder = getNotesFolder();
  if (existingFileId) {
    try {
      const file = DriveApp.getFileById(existingFileId);
      file.setContent(content || '');
      file.setName('note_' + noteId + '_' + (title || 'untitled').substring(0, 50));
      return existingFileId;
    } catch (e) { /* File not found — create new */ }
  }
  const fileName = 'note_' + noteId + '_' + (title || 'untitled').substring(0, 50);
  const file = folder.createFile(fileName, content || '', MimeType.PLAIN_TEXT);
  return file.getId();
}

function readNoteFromDrive(fileId) {
  if (!fileId) return '';
  try {
    return DriveApp.getFileById(fileId).getBlob().getDataAsString();
  } catch (e) {
    return '[Error reading note: ' + e.message + ']';
  }
}

function trashNoteDriveFile(fileId) {
  if (!fileId) return false;
  try {
    const file = DriveApp.getFileById(fileId);
    if (file) { file.setTrashed(true); return true; }
  } catch (e) {
    Logger.log('trashNoteDriveFile error: ' + e.message);
  }
  return false;
}

// ── Initialize Sheets ──
function initSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const headerStyle = { bg: '#292f4c', fg: '#fff' };

  let tasksSheet = ss.getSheetByName('Tasks');
  if (!tasksSheet) {
    tasksSheet = ss.insertSheet('Tasks');
    tasksSheet.appendRow(['id','groupId','name','status','priority','dueDate','timelineStart','timelineEnd','notes','createdAt','updatedAt']);
    tasksSheet.getRange(1,1,1,11).setFontWeight('bold').setBackground(headerStyle.bg).setFontColor(headerStyle.fg);
    tasksSheet.setFrozenRows(1);
    tasksSheet.setColumnWidths(1,11,140);
  }

  let groupsSheet = ss.getSheetByName('Groups');
  if (!groupsSheet) {
    groupsSheet = ss.insertSheet('Groups');
    groupsSheet.appendRow(['id','title','color','sortOrder']);
    groupsSheet.getRange(1,1,1,4).setFontWeight('bold').setBackground(headerStyle.bg).setFontColor(headerStyle.fg);
    groupsSheet.setFrozenRows(1);
    groupsSheet.appendRow(['g1','To-Do','#579bfc',1]);
    groupsSheet.appendRow(['g2','Completed','#00c875',2]);
  }

  let membersSheet = ss.getSheetByName('Members');
  if (!membersSheet) {
    membersSheet = ss.insertSheet('Members');
    membersSheet.appendRow(['name']);
    membersSheet.getRange(1,1).setFontWeight('bold');
    membersSheet.appendRow(['Kevin']);
  }

  // Events sheet — v9: added description column (11)
  let eventsSheet = ss.getSheetByName('Events');
  if (!eventsSheet) {
    eventsSheet = ss.insertSheet('Events');
    eventsSheet.appendRow(['id','title','date','startTime','endTime','color','allDay','createdAt','updatedAt','gcalId','description']);
    eventsSheet.getRange(1,1,1,11).setFontWeight('bold').setBackground(headerStyle.bg).setFontColor(headerStyle.fg);
    eventsSheet.setFrozenRows(1);
    eventsSheet.setColumnWidths(1,11,140);
  } else {
    // Migrate: add gcalId header if missing (col 10), description (col 11)
    const lastCol = Math.max(eventsSheet.getLastColumn(), 10);
    const headers = eventsSheet.getRange(1,1,1,lastCol).getValues()[0];
    if (headers[9] !== 'gcalId') {
      eventsSheet.getRange(1,10).setValue('gcalId').setFontWeight('bold').setBackground(headerStyle.bg).setFontColor(headerStyle.fg);
    }
    if (lastCol < 11 || headers[10] !== 'description') {
      eventsSheet.getRange(1,11).setValue('description').setFontWeight('bold').setBackground(headerStyle.bg).setFontColor(headerStyle.fg);
    }
  }

  let notesSheet = ss.getSheetByName('Notes');
  if (!notesSheet) {
    notesSheet = ss.insertSheet('Notes');
    notesSheet.appendRow(['id','title','driveFileId','pinned','folder','sortOrder','createdAt','updatedAt','tags','font','icon','cover']);
    notesSheet.getRange(1,1,1,12).setFontWeight('bold').setBackground(headerStyle.bg).setFontColor(headerStyle.fg);
    notesSheet.setFrozenRows(1);
    notesSheet.setColumnWidths(1,12,140);
  }

  const sheet1 = ss.getSheetByName('Sheet1');
  if (sheet1 && ss.getSheets().length > 1) ss.deleteSheet(sheet1);

  getNotesFolder();
  getFlowdeskCalendar(); // Ensure calendar exists

  return { success: true };
}

function ensureSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss.getSheetByName('Groups') || !ss.getSheetByName('Tasks') || !ss.getSheetByName('Events') || !ss.getSheetByName('Notes')) {
    initSheet();
  }
  return ss;
}

// ── Get All Data ──
function getAllData() {
  const ss = ensureSheets();

  // Groups
  const groupsSheet = ss.getSheetByName('Groups');
  const groups = [];
  if (groupsSheet && groupsSheet.getLastRow() > 1) {
    const gData = groupsSheet.getRange(2,1,groupsSheet.getLastRow()-1,4).getValues();
    gData.forEach(r => { if(r[0]) groups.push({id:r[0],title:r[1],color:r[2],sortOrder:r[3]}); });
  }
  groups.sort((a,b) => a.sortOrder - b.sortOrder);

  // Tasks
  const tasksSheet = ss.getSheetByName('Tasks');
  const tasks = [];
  if (tasksSheet && tasksSheet.getLastRow() > 1) {
    const tData = tasksSheet.getRange(2,1,tasksSheet.getLastRow()-1,11).getValues();
    tData.forEach(r => {
      if(r[0]) tasks.push({id:r[0],groupId:r[1],name:r[2],status:r[3],priority:r[4],
        dueDate:fmtDate(r[5]),timelineStart:fmtDate(r[6]),timelineEnd:fmtDate(r[7]),notes:r[8]});
    });
  }

  // Members
  const membersSheet = ss.getSheetByName('Members');
  const members = [];
  if (membersSheet && membersSheet.getLastRow() > 1) {
    membersSheet.getRange(2,1,membersSheet.getLastRow()-1,1).getValues().forEach(r => { if(r[0]) members.push(r[0]); });
  }

  // Events from Sheets
  const eventsSheet = ss.getSheetByName('Events');
  const events = [];
  const sheetEventIds = new Set();
  const knownGcalIds = new Set();
  if (eventsSheet && eventsSheet.getLastRow() > 1) {
    const cols = Math.min(eventsSheet.getLastColumn(), 11);
    const eData = eventsSheet.getRange(2,1,eventsSheet.getLastRow()-1,cols).getValues();
    eData.forEach(r => {
      if(r[0]) {
        sheetEventIds.add(String(r[0]));
        const gcalIdVal = cols >= 10 ? String(r[9]||'') : '';
        if (gcalIdVal) knownGcalIds.add(gcalIdVal);
        events.push({
          id:String(r[0]), title:r[1], date:fmtDate(r[2]),
          startTime:fmtTime(r[3]), endTime:fmtTime(r[4]),
          color:r[5]||'#0073ea', allDay:r[6]?true:false,
          gcalId: gcalIdVal,
          description: (cols >= 11 ? String(r[10]||'') : '')
        });
      }
    });
  }

  // Pull Google Calendar events (non-Flowdesk ones)
  const gcalEvents = pullGCalEvents();
  gcalEvents.forEach(ge => {
    // Skip if we already have this event (by id or gcalId)
    if (sheetEventIds.has(ge.id)) return;
    if (ge.gcalId && knownGcalIds.has(ge.gcalId)) return;
    events.push(ge);
  });

  // Notes
  const notesSheet = ss.getSheetByName('Notes');
  const notes = [];
  if (notesSheet && notesSheet.getLastRow() > 1) {
    const nCols = Math.min(notesSheet.getLastColumn(), 12);
    const nData = notesSheet.getRange(2,1,notesSheet.getLastRow()-1,nCols).getValues();
    nData.forEach(r => {
      if (r[0]) {
        const driveFileId = r[2] || '';
        const content = driveFileId ? readNoteFromDrive(driveFileId) : '';
        const tagsStr = nCols >= 9 ? String(r[8]||'') : '';
        notes.push({
          id: String(r[0]), title: r[1], content: content,
          pinned: r[3] ? true : false, folder: r[4] || '', sortOrder: r[5] || 0,
          createdAt: r[6] ? new Date(r[6]).toISOString() : '',
          updatedAt: r[7] ? new Date(r[7]).toISOString() : '',
          tags: tagsStr ? tagsStr.split(',') : [],
          font: nCols >= 10 ? String(r[9]||'sans') : 'sans',
          icon: nCols >= 11 ? String(r[10]||'') : '',
          cover: nCols >= 12 ? String(r[11]||'') : ''
        });
      }
    });
  }

  return {
    groups: groups.map(g => ({id:g.id, title:g.title, color:g.color, collapsed:false, tasks: tasks.filter(t=>t.groupId===g.id)})),
    members: members,
    events: events,
    notes: notes
  };
}

// ── Light pull: no note content (fast!) ──
function getAllDataLight() {
  const ss = ensureSheets();

  // Groups
  const groupsSheet = ss.getSheetByName('Groups');
  const groups = [];
  if (groupsSheet && groupsSheet.getLastRow() > 1) {
    const gData = groupsSheet.getRange(2,1,groupsSheet.getLastRow()-1,4).getValues();
    gData.forEach(r => { if(r[0]) groups.push({id:r[0],title:r[1],color:r[2],sortOrder:r[3]}); });
  }
  groups.sort((a,b) => a.sortOrder - b.sortOrder);

  // Tasks
  const tasksSheet = ss.getSheetByName('Tasks');
  const tasks = [];
  if (tasksSheet && tasksSheet.getLastRow() > 1) {
    const tData = tasksSheet.getRange(2,1,tasksSheet.getLastRow()-1,11).getValues();
    tData.forEach(r => {
      if(r[0]) tasks.push({id:r[0],groupId:r[1],name:r[2],status:r[3],priority:r[4],
        dueDate:fmtDate(r[5]),timelineStart:fmtDate(r[6]),timelineEnd:fmtDate(r[7]),notes:r[8]});
    });
  }

  // Members
  const membersSheet = ss.getSheetByName('Members');
  const members = [];
  if (membersSheet && membersSheet.getLastRow() > 1) {
    membersSheet.getRange(2,1,membersSheet.getLastRow()-1,1).getValues().forEach(r => { if(r[0]) members.push(r[0]); });
  }

  // Events (same as full version)
  const eventsSheet = ss.getSheetByName('Events');
  const events = [];
  const sheetEventIds = new Set();
  const knownGcalIds = new Set();
  if (eventsSheet && eventsSheet.getLastRow() > 1) {
    const cols = Math.min(eventsSheet.getLastColumn(), 11);
    const eData = eventsSheet.getRange(2,1,eventsSheet.getLastRow()-1,cols).getValues();
    eData.forEach(r => {
      if(r[0]) {
        sheetEventIds.add(String(r[0]));
        const gcalIdVal = cols >= 10 ? String(r[9]||'') : '';
        if (gcalIdVal) knownGcalIds.add(gcalIdVal);
        events.push({
          id:String(r[0]), title:r[1], date:fmtDate(r[2]),
          startTime:fmtTime(r[3]), endTime:fmtTime(r[4]),
          color:r[5]||'#0073ea', allDay:r[6]?true:false,
          gcalId: gcalIdVal,
          description: (cols >= 11 ? String(r[10]||'') : '')
        });
      }
    });
  }
  const gcalEvents = pullGCalEvents();
  gcalEvents.forEach(ge => {
    if (sheetEventIds.has(ge.id)) return;
    if (ge.gcalId && knownGcalIds.has(ge.gcalId)) return;
    events.push(ge);
  });

  // Notes — metadata only, NO content (this is what makes it fast)
  const notesSheet = ss.getSheetByName('Notes');
  const notes = [];
  if (notesSheet && notesSheet.getLastRow() > 1) {
    const nCols = Math.min(notesSheet.getLastColumn(), 12);
    const nData = notesSheet.getRange(2,1,notesSheet.getLastRow()-1,nCols).getValues();
    nData.forEach(r => {
      if (r[0]) {
        const tagsStr = nCols >= 9 ? String(r[8]||'') : '';
        notes.push({
          id: String(r[0]), title: r[1], driveFileId: r[2] || '',
          pinned: r[3] ? true : false, folder: r[4] || '', sortOrder: r[5] || 0,
          createdAt: r[6] ? new Date(r[6]).toISOString() : '',
          updatedAt: r[7] ? new Date(r[7]).toISOString() : '',
          tags: tagsStr ? tagsStr.split(',') : [],
          font: nCols >= 10 ? String(r[9]||'sans') : 'sans',
          icon: nCols >= 11 ? String(r[10]||'') : '',
          cover: nCols >= 12 ? String(r[11]||'') : ''
        });
      }
    });
  }

  return {
    groups: groups.map(g => ({id:g.id, title:g.title, color:g.color, collapsed:false, tasks: tasks.filter(t=>t.groupId===g.id)})),
    members: members,
    events: events,
    notes: notes
  };
}

// ── Get single note content by id ──
function getNoteContentById(noteId) {
  const ss = ensureSheets();
  const notesSheet = ss.getSheetByName('Notes');
  if (!notesSheet || notesSheet.getLastRow() < 2) return { error: 'Note not found' };
  const nCols = Math.min(notesSheet.getLastColumn(), 12);
  const nData = notesSheet.getRange(2,1,notesSheet.getLastRow()-1,nCols).getValues();
  for (let i = 0; i < nData.length; i++) {
    if (String(nData[i][0]) === String(noteId)) {
      const driveFileId = nData[i][2] || '';
      const content = driveFileId ? readNoteFromDrive(driveFileId) : '';
      const tagsStr = nCols >= 9 ? String(nData[i][8]||'') : '';
      return {
        id: String(nData[i][0]), title: nData[i][1], content: content,
        pinned: nData[i][3] ? true : false, folder: nData[i][4] || '',
        sortOrder: nData[i][5] || 0,
        tags: tagsStr ? tagsStr.split(',') : [],
        font: nCols >= 10 ? String(nData[i][9]||'sans') : 'sans',
        icon: nCols >= 11 ? String(nData[i][10]||'') : '',
        cover: nCols >= 12 ? String(nData[i][11]||'') : ''
      };
    }
  }
  return { error: 'Note not found' };
}

// ── Sync All ──
// v11 contract:
//   groups: [{id, title, color, tasks:[...]}]     — IF present AND non-empty, replaces ALL groups+tasks on cloud
//                                                   IF missing OR empty array, groups/tasks sheets are LEFT UNTOUCHED
//   members: [...]                                 — IF present AND non-empty, replaces members; else untouched
//   events: [...]                                  — MERGED with cloud (client wins for same ID); server-only events preserved
//   deletedEventIds: [...]                         — events NOT re-preserved, AND corresponding GCal events deleted
//   notes: [...]                                   — IF present AND non-empty, replaces notes (Drive files kept if no 'content' key)
//   deletedNoteIds: [...]                          — (v11) notes to hard-delete; their Drive files are trashed
function syncAll(fullData) {
  const ss = ensureSheets();
  const now = new Date().toISOString();

  // ── Groups ── (anti-destruction: only clear if payload is non-empty)
  const gs = ss.getSheetByName('Groups');
  if (!gs) return { error: 'Groups sheet not found' };
  const groupsPayload = Array.isArray(fullData.groups) ? fullData.groups : [];
  if (groupsPayload.length > 0) {
    if (gs.getLastRow() > 1) gs.getRange(2,1,gs.getLastRow()-1,4).clearContent();
    const groupsRows = groupsPayload.map((g, i) => [
      g.id || '', g.title || '', g.color || '#579bfc', i + 1
    ]);
    if (groupsRows.length > 0) {
      gs.getRange(2, 1, groupsRows.length, 4).setValues(groupsRows);
    }
  }

  // ── Tasks ── (anti-destruction: only rewrite when client actually sent groups)
  // Rationale: tasks live under groups; if client omitted groups, don't nuke tasks either
  const ts = ss.getSheetByName('Tasks');
  if (!ts) return { error: 'Tasks sheet not found' };
  if (groupsPayload.length > 0) {
    if (ts.getLastRow() > 1) ts.getRange(2,1,ts.getLastRow()-1,11).clearContent();
    const taskRows = [];
    groupsPayload.forEach(g => {
      (g.tasks || []).forEach(t => {
        taskRows.push([
          t.id || '', g.id || '', t.name || '', t.status || '', t.priority || '',
          t.dueDate || '', t.timelineStart || '', t.timelineEnd || '',
          t.notes || '', t.createdAt || now, now
        ]);
      });
    });
    if (taskRows.length > 0) {
      ts.getRange(2, 1, taskRows.length, 11).setValues(taskRows);
    }
  }

  // ── Members ── (already had anti-destruction; keep it)
  const ms = ss.getSheetByName('Members');
  if (ms && Array.isArray(fullData.members) && fullData.members.length > 0) {
    if (ms.getLastRow() > 1) ms.getRange(2,1,ms.getLastRow()-1,1).clearContent();
    const memberRows = fullData.members.map(m => [m]);
    ms.getRange(2, 1, memberRows.length, 1).setValues(memberRows);
  }

  // ── Events ── MERGE strategy + GCal delete propagation
  const es = ss.getSheetByName('Events');
  if (es) {
    // Read ALL existing server events into a map for merging
    const existingServerEvents = {};  // eventId → row array
    const existingGcalMap = {};       // eventId → gcalId
    if (es.getLastRow() > 1) {
      const cols = Math.min(es.getLastColumn(), 11);
      const existing = es.getRange(2,1,es.getLastRow()-1,cols).getValues();
      existing.forEach(r => {
        if (r[0]) {
          const eid = String(r[0]);
          existingServerEvents[eid] = r;
          if (cols >= 10 && r[9]) existingGcalMap[eid] = String(r[9]);
        }
      });
      es.getRange(2,1,es.getLastRow()-1,11).clearContent();
    }

    // Set of deleted IDs (propagate deletes to GCal)
    const deletedIds = new Set(
      (Array.isArray(fullData.deletedEventIds) ? fullData.deletedEventIds : []).map(String)
    );

    // 1) Delete GCal counterparts BEFORE rebuilding the sheet
    deletedIds.forEach(eid => {
      const gcalId = existingGcalMap[eid] || '';
      if (gcalId) deleteGCalEvent(gcalId);
    });

    // 2) Client events (client wins for matching IDs) — gather into buffer, write once
    const outRows = [];
    const clientEvents = Array.isArray(fullData.events) ? fullData.events : [];
    const clientEventIds = new Set();
    clientEvents.forEach(ev => clientEventIds.add(String(ev.id)));

    clientEvents.forEach((ev) => {
      const evId = String(ev.id);
      // Skip any client event the client ALSO marked for deletion (shouldn't happen but be safe)
      if (deletedIds.has(evId)) return;
      const isFromGCal = ev.fromGCal || evId.startsWith('gcal_');
      const existingGcalId = existingGcalMap[evId] || ev.gcalId || '';

      let gcalId = existingGcalId;
      if (!isFromGCal) {
        gcalId = syncEventToGCal(ev, existingGcalId);
      }

      const stFmt = fmtTime(ev.startTime);
      const etFmt = fmtTime(ev.endTime);
      outRows.push([
        evId, ev.title || '', ev.date || '', stFmt, etFmt,
        ev.color || '#0073ea', ev.allDay ? 1 : 0,
        ev.createdAt || now, now, gcalId, ev.description || ''
      ]);
    });

    // 3) Append server-only events (IDs not in client data, not deleted)
    Object.keys(existingServerEvents).forEach(eid => {
      if (clientEventIds.has(eid) || deletedIds.has(eid)) return;
      const r = existingServerEvents[eid];
      const stFmt = fmtTime(r[3]);
      const etFmt = fmtTime(r[4]);
      outRows.push([
        String(r[0]), r[1] || '', fmtDate(r[2]) || '', stFmt, etFmt,
        r[5] || '#0073ea', r[6] ? 1 : 0, r[7] || now, now,
        r[9] || '', (r.length > 10 ? r[10] : '') || ''
      ]);
    });

    // 4) Write everything at once
    if (outRows.length > 0) {
      es.getRange(2, 1, outRows.length, 11).setValues(outRows);
      // Force time columns to plain-text format so Sheets doesn't reformat "09:00" into a date
      es.getRange(2, 4, outRows.length, 2).setNumberFormat('@');
    }
  }

  // ── Notes ── delete first, then upsert
  const ns = ss.getSheetByName('Notes');
  if (ns) {
    // (a) Hard-delete notes listed in deletedNoteIds (trash Drive files too)
    const deletedNoteIds = new Set(
      (Array.isArray(fullData.deletedNoteIds) ? fullData.deletedNoteIds : []).map(String)
    );

    // Load existing notes → id-to-driveFileId map
    const existingNoteMap = {};  // noteId → driveFileId
    if (ns.getLastRow() > 1) {
      const existing = ns.getRange(2, 1, ns.getLastRow() - 1, 3).getValues();
      existing.forEach(r => {
        if (r[0]) existingNoteMap[String(r[0])] = String(r[2] || '');
      });
    }

    // Trash Drive files for deleted notes
    deletedNoteIds.forEach(nid => {
      const fid = existingNoteMap[nid];
      if (fid) trashNoteDriveFile(fid);
    });

    // (b) Upsert full notes payload (only if non-empty — anti-destruction)
    const notesPayload = Array.isArray(fullData.notes) ? fullData.notes : [];
    const hasDeletions = deletedNoteIds.size > 0;

    if (notesPayload.length > 0 || hasDeletions) {
      if (ns.getLastRow() > 1) ns.getRange(2,1,ns.getLastRow()-1,12).clearContent();
      const noteRows = [];
      notesPayload.forEach(n => {
        const noteId = String(n.id || '');
        if (!noteId || deletedNoteIds.has(noteId)) return;  // skip deleted
        const existingFileId = existingNoteMap[noteId] || '';
        let driveFileId = existingFileId;
        // Only write to Drive if content key is present (modified note)
        if ('content' in n) {
          driveFileId = saveNoteToDrive(noteId, n.title, n.content || '', existingFileId);
        }
        const tagsStr = Array.isArray(n.tags) ? n.tags.join(',') : (n.tags || '');
        noteRows.push([
          noteId, n.title || '', driveFileId, n.pinned ? 1 : 0,
          n.folder || '', n.sortOrder || 0, n.createdAt || now, now,
          tagsStr, n.font || 'sans', n.icon || '', n.cover || ''
        ]);
      });
      if (noteRows.length > 0) {
        ns.getRange(2, 1, noteRows.length, 12).setValues(noteRows);
      }
    }
  }

  return { success: true, timestamp: now, version: 11 };
}

function fmtDate(v) {
  if (!v) return '';
  if (v instanceof Date) return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  return String(v);
}

function fmtTime(v) {
  if (!v) return '';
  if (v instanceof Date) return Utilities.formatDate(v, Session.getScriptTimeZone(), 'HH:mm');
  const s = String(v);
  const m = s.match(/(\d{2}):(\d{2})/);
  return m ? m[1] + ':' + m[2] : s;
}
