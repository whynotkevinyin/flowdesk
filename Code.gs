// ============================================================
// Code.gs — Flowdesk Backend API (v5 - Drive-based Notes)
// ============================================================
// Notes content is stored in Google Drive files (no 50K limit).
// Google Sheets "Notes" sheet only holds metadata + driveFileId.
// ============================================================

// ⚠️ CHANGE THESE to your own secrets!
const API_KEY = 'gBjEq2sv1LBnFPDs-eqg2wDrcp3BBMpjQGa5ZWUmw_E';
const PIN = 'taiwanno1';

// Folder in Google Drive to store note files
const DRIVE_FOLDER_NAME = 'Flowdesk_Notes';

function checkAuth(e) {
  const key = (e && e.parameter && e.parameter.key) || '';
  return key === API_KEY || key === PIN;
}

function doGet(e) {
  const action = (e && e.parameter && e.parameter.action) || '';
  if (action === 'ping') return json({ ok: true, version: 5 });
  if (!checkAuth(e)) return json({ error: 'Unauthorized', code: 401 });
  if (action === 'init') return json(initSheet());
  if (action === 'getTasks') return json(getAllData());
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

// ── Get or create the Drive folder for notes ──
function getNotesFolder() {
  const folders = DriveApp.getFoldersByName(DRIVE_FOLDER_NAME);
  if (folders.hasNext()) return folders.next();
  return DriveApp.createFolder(DRIVE_FOLDER_NAME);
}

// ── Save note content to Drive, return file ID ──
function saveNoteToDrive(noteId, title, content, existingFileId) {
  const folder = getNotesFolder();

  // Try to update existing file
  if (existingFileId) {
    try {
      const file = DriveApp.getFileById(existingFileId);
      file.setContent(content || '');
      file.setName('note_' + noteId + '_' + (title || 'untitled').substring(0, 50));
      return existingFileId;
    } catch (e) {
      // File not found — create new one
    }
  }

  // Create new file
  const fileName = 'note_' + noteId + '_' + (title || 'untitled').substring(0, 50);
  const file = folder.createFile(fileName, content || '', MimeType.PLAIN_TEXT);
  return file.getId();
}

// ── Read note content from Drive ──
function readNoteFromDrive(fileId) {
  if (!fileId) return '';
  try {
    const file = DriveApp.getFileById(fileId);
    return file.getBlob().getDataAsString();
  } catch (e) {
    return '[Error reading note: ' + e.message + ']';
  }
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

  let eventsSheet = ss.getSheetByName('Events');
  if (!eventsSheet) {
    eventsSheet = ss.insertSheet('Events');
    eventsSheet.appendRow(['id','title','date','startTime','endTime','color','allDay','createdAt','updatedAt']);
    eventsSheet.getRange(1,1,1,9).setFontWeight('bold').setBackground(headerStyle.bg).setFontColor(headerStyle.fg);
    eventsSheet.setFrozenRows(1);
    eventsSheet.setColumnWidths(1,9,140);
  }

  // Notes sheet — v5: driveFileId instead of content
  let notesSheet = ss.getSheetByName('Notes');
  if (!notesSheet) {
    notesSheet = ss.insertSheet('Notes');
    notesSheet.appendRow(['id','title','driveFileId','pinned','folder','sortOrder','createdAt','updatedAt']);
    notesSheet.getRange(1,1,1,8).setFontWeight('bold').setBackground(headerStyle.bg).setFontColor(headerStyle.fg);
    notesSheet.setFrozenRows(1);
    notesSheet.setColumnWidths(1,8,140);
  }

  const sheet1 = ss.getSheetByName('Sheet1');
  if (sheet1 && ss.getSheets().length > 1) ss.deleteSheet(sheet1);

  // Ensure Drive folder exists
  getNotesFolder();

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

  // Events
  const eventsSheet = ss.getSheetByName('Events');
  const events = [];
  if (eventsSheet && eventsSheet.getLastRow() > 1) {
    const eData = eventsSheet.getRange(2,1,eventsSheet.getLastRow()-1,9).getValues();
    eData.forEach(r => {
      if(r[0]) events.push({id:String(r[0]), title:r[1], date:fmtDate(r[2]), startTime:r[3]||'', endTime:r[4]||'', color:r[5]||'#0073ea', allDay:r[6]?true:false});
    });
  }

  // Notes — read content from Drive files
  const notesSheet = ss.getSheetByName('Notes');
  const notes = [];
  if (notesSheet && notesSheet.getLastRow() > 1) {
    const nData = notesSheet.getRange(2,1,notesSheet.getLastRow()-1,8).getValues();
    nData.forEach(r => {
      if (r[0]) {
        const driveFileId = r[2] || '';
        const content = driveFileId ? readNoteFromDrive(driveFileId) : '';
        notes.push({
          id: String(r[0]), title: r[1], content: content,
          pinned: r[3] ? true : false, folder: r[4] || '', sortOrder: r[5] || 0
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

// ── Sync All ──
function syncAll(fullData) {
  const ss = ensureSheets();
  const now = new Date().toISOString();

  // Groups
  const gs = ss.getSheetByName('Groups');
  if (!gs) return { error: 'Groups sheet not found' };
  if (gs.getLastRow() > 1) gs.getRange(2,1,gs.getLastRow()-1,4).clearContent();
  (fullData.groups || []).forEach((g,i) => {
    gs.getRange(i+2,1,1,4).setValues([[g.id, g.title, g.color || '#579bfc', i+1]]);
  });

  // Tasks
  const ts = ss.getSheetByName('Tasks');
  if (!ts) return { error: 'Tasks sheet not found' };
  if (ts.getLastRow() > 1) ts.getRange(2,1,ts.getLastRow()-1,11).clearContent();
  let row = 2;
  (fullData.groups || []).forEach(g => {
    (g.tasks || []).forEach(t => {
      ts.getRange(row,1,1,11).setValues([[
        t.id, g.id, t.name||'', t.status||'', t.priority||'',
        t.dueDate||'', t.timelineStart||'', t.timelineEnd||'',
        t.notes||'', t.createdAt||now, now
      ]]);
      row++;
    });
  });

  // Members
  const ms = ss.getSheetByName('Members');
  if (ms && fullData.members && fullData.members.length > 0) {
    if (ms.getLastRow() > 1) ms.getRange(2,1,ms.getLastRow()-1,1).clearContent();
    fullData.members.forEach((m,i) => { ms.getRange(i+2,1).setValue(m); });
  }

  // Events
  const es = ss.getSheetByName('Events');
  if (es && fullData.events) {
    if (es.getLastRow() > 1) es.getRange(2,1,es.getLastRow()-1,9).clearContent();
    (fullData.events || []).forEach((ev,i) => {
      es.getRange(i+2,1,1,9).setValues([[
        ev.id, ev.title||'', ev.date||'', ev.startTime||'', ev.endTime||'',
        ev.color||'#0073ea', ev.allDay?1:0, ev.createdAt||now, now
      ]]);
    });
  }

  // Notes — save content to Drive, store fileId in sheet
  // IMPORTANT: only overwrite if the client actually sent notes (non-empty array)
  // to prevent a client with no local notes from wiping the cloud copy.
  const ns = ss.getSheetByName('Notes');
  if (ns && fullData.notes && fullData.notes.length > 0) {
    // Read existing driveFileId mappings so we can update existing files
    const existingMap = {};  // noteId → driveFileId
    if (ns.getLastRow() > 1) {
      const existing = ns.getRange(2,1,ns.getLastRow()-1,3).getValues();
      existing.forEach(r => { if (r[0] && r[2]) existingMap[String(r[0])] = String(r[2]); });
      ns.getRange(2,1,ns.getLastRow()-1,8).clearContent();
    }

    (fullData.notes || []).forEach((n,i) => {
      const noteId = String(n.id);
      const existingFileId = existingMap[noteId] || '';
      const driveFileId = saveNoteToDrive(noteId, n.title, n.content || '', existingFileId);
      ns.getRange(i+2,1,1,8).setValues([[
        noteId, n.title||'', driveFileId, n.pinned?1:0,
        n.folder||'', n.sortOrder||0, n.createdAt||now, now
      ]]);
    });
  }

  return { success: true, timestamp: now };
}

function fmtDate(v) {
  if (!v) return '';
  if (v instanceof Date) return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  return String(v);
}
