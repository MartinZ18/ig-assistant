/**
 * Leads sink for ig-assistant. Deploy as a web app bound to a Google Sheet (see README.md).
 *
 * n8n POSTs JSON: { secret, channel, contact_id, username, message, timestamp }.
 * The secret travels in the body because Apps Script web apps cannot read request headers.
 * One row per contact per day: a repeat post only updates last_message / updated_at. The lock
 * serializes concurrent posts, which backs up the n8n lead claim (static data can lose updates).
 */

var SHEET_NAME = 'Leads';
var TIME_ZONE = 'America/Argentina/Mendoza';
var HEADERS = [
  'created_at', 'updated_at', 'channel', 'contact_id', 'username',
  'first_message', 'last_message', 'status'
];
var COL = {};
HEADERS.forEach(function (name, i) { COL[name] = i + 1; });
var MAX_TEXT = 2000;
// Rows read per getValues call when scanning back for today's leads.
var SCAN_CHUNK = 200;

function jsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function text(value) {
  return String(value === undefined || value === null ? '' : value).slice(0, MAX_TEXT);
}

// Values starting with = + - @ would be evaluated as formulas by Sheets; force plain text.
function safeCell(value) {
  return /^[=+\-@]/.test(value) ? "'" + value : value;
}

function getSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(HEADERS);
    sheet.setFrozenRows(1);
    // contact_id is a column of ids: keep it as text so long numbers are not rounded.
    sheet.getRange(1, COL.contact_id, sheet.getMaxRows(), 1).setNumberFormat('@');
  }
  return sheet;
}

function validate(data) {
  if (!data || typeof data !== 'object') return 'body must be a JSON object';
  var required = ['contact_id', 'channel', 'message'];
  for (var i = 0; i < required.length; i++) {
    var v = data[required[i]];
    if (v === undefined || v === null || String(v).trim() === '') {
      return 'missing field: ' + required[i];
    }
  }
  // username may be empty (Instagram users without a handle), but the key must be present.
  if (!('username' in data)) return 'missing field: username';
  return null;
}

function doPost(e) {
  var data;
  try {
    data = JSON.parse(e.postData.contents);
  } catch (err) {
    return jsonResponse({ ok: false, error: 'invalid json' });
  }

  var expected = PropertiesService.getScriptProperties().getProperty('LEADS_SECRET');
  if (!expected || !data || data.secret !== expected) {
    return jsonResponse({ ok: false, error: 'unauthorized' });
  }

  var problem = validate(data);
  if (problem) return jsonResponse({ ok: false, error: problem });

  var contactId = text(data.contact_id);
  var now = new Date();
  var today = Utilities.formatDate(now, TIME_ZONE, 'yyyy-MM-dd');

  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
  } catch (err) {
    return jsonResponse({ ok: false, error: 'busy' });
  }
  try {
    var sheet = getSheet();
    // Newest rows are at the bottom: scan back in chunks and stop at an older day, so the cost
    // depends on today's leads instead of the whole sheet.
    var end = sheet.getLastRow();
    var olderDay = false;
    while (end > 1 && !olderDay) {
      var start = Math.max(2, end - SCAN_CHUNK + 1);
      var rows = sheet.getRange(start, 1, end - start + 1, HEADERS.length).getValues();
      for (var i = rows.length - 1; i >= 0; i--) {
        var created = rows[i][COL.created_at - 1];
        var day = created instanceof Date
          ? Utilities.formatDate(created, TIME_ZONE, 'yyyy-MM-dd')
          : String(created).slice(0, 10);
        if (day < today) { olderDay = true; break; }
        if (day === today && String(rows[i][COL.contact_id - 1]) === contactId) {
          var row = start + i;
          sheet.getRange(row, COL.last_message).setValue(safeCell(text(data.message)));
          sheet.getRange(row, COL.updated_at).setValue(now);
          return jsonResponse({ ok: true, action: 'updated' });
        }
      }
      end = start - 1;
    }
    var message = safeCell(text(data.message));
    sheet.appendRow([
      now, now, text(data.channel), contactId, safeCell(text(data.username)),
      message, message, 'nuevo'
    ]);
    // appendRow may coerce the id to a number; rewrite it as text.
    var newRow = sheet.getLastRow();
    sheet.getRange(newRow, COL.contact_id).setNumberFormat('@').setValue(contactId);
    return jsonResponse({ ok: true, action: 'created' });
  } finally {
    lock.releaseLock();
  }
}

// A GET (for example opening the /exec URL in a browser) only confirms the deployment is alive.
function doGet() {
  return jsonResponse({ ok: true, service: 'ig-assistant-leads' });
}
