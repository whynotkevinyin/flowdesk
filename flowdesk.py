#!/usr/bin/env python3
"""
Flowdesk - Task Management Desktop App
PyQt6 + SQLite Architecture with Google Sheets Sync
Calendar + Rich-Text Notes (Notion-like)
"""

import sys
import os
import json
import sqlite3
import urllib.request
import urllib.parse
try:
    import requests as _requests
except ImportError:
    _requests = None
import threading
import calendar as cal_mod
from datetime import datetime, date, timedelta

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLineEdit, QLabel, QComboBox, QProgressBar,
    QMenu, QMenuBar, QToolBar, QStatusBar, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QTextEdit,
    QDateEdit, QSlider, QCheckBox, QSplitter, QFrame,
    QScrollArea, QGridLayout, QFileDialog, QInputDialog,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem,
    QAbstractItemView, QSpacerItem, QSizePolicy, QTreeWidget,
    QTreeWidgetItem, QListWidget, QListWidgetItem, QStackedWidget,
    QTimeEdit, QColorDialog
)
from PyQt6.QtCore import (
    Qt, QSize, QDate, QTime, QTimer, pyqtSignal, QMimeData, QPoint
)
from PyQt6.QtGui import (
    QColor, QPalette, QFont, QIcon, QAction, QPainter,
    QBrush, QPen, QDrag, QPixmap, QTextCharFormat, QTextListFormat,
    QTextBlockFormat, QTextCursor, QSyntaxHighlighter,
    QTextDocument
)


# ─── Constants ───────────────────────────────────────────────
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flowdesk.db")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flowdesk_config.json")
SYNC_URL = ""  # User fills this in via File > Set Sync URL...

STATUSES = ["Not Started", "Working on it", "Waiting for review", "On Hold", "Stuck", "Done"]
STATUS_COLORS = {
    "Not Started":        "#797e93",
    "Working on it":      "#0073ea",
    "Waiting for review": "#fdab3d",
    "On Hold":            "#a25ddc",
    "Stuck":              "#e2445c",
    "Done":               "#00c875",
}

PRIORITIES = ["Critical", "High", "Medium", "Low"]
PRIORITY_COLORS = {
    "Critical": "#e2445c",
    "High":     "#fc5a5a",
    "Medium":   "#fdab3d",
    "Low":      "#66ccff",
}

GROUP_COLORS = [
    "#e2445c", "#e8830c", "#fdab3d", "#00c875",
    "#0073ea", "#579bfc", "#a25ddc", "#7f5347",
]

EVENT_COLORS = [
    "#0073ea", "#e8830c", "#00c875", "#e2445c",
    "#a25ddc", "#579bfc", "#fdab3d", "#7f5347",
]

LIGHT_THEME = {
    "bg":          "#fefcf3",
    "card_bg":     "#fffdf5",
    "header_bg":   "#f5f3ed",
    "header_fg":   "#3d3a33",
    "text":        "#3d3a33",
    "text_dim":    "#999999",
    "border":      "#e8e0c8",
    "section_bg":  "#f5f3ed",
    "accent":      "#0073ea",
    "shadow":      "rgba(0,0,0,0.06)",
    "toolbar_input_bg":      "rgba(0,0,0,0.05)",
    "toolbar_input_border":  "rgba(0,0,0,0.1)",
    "toolbar_input_color":   "#3d3a33",
    "toolbar_placeholder":   "rgba(0,0,0,0.4)",
    "toolbar_btn_hover":     "rgba(0,0,0,0.08)",
    "toolbar_btn_color":     "#3d3a33",
    "sync_btn_bg":           "rgba(0,0,0,0.06)",
    "sync_btn_hover":        "rgba(0,0,0,0.12)",
    "sync_btn_color":        "#3d3a33",
}

DARK_THEME = {
    "bg":          "#2c2c34",
    "card_bg":     "#323240",
    "header_bg":   "#1e1e28",
    "header_fg":   "#e8e8ec",
    "text":        "#e8e8ec",
    "text_dim":    "#888888",
    "border":      "#4a4a58",
    "section_bg":  "#3d3d46",
    "accent":      "#0073ea",
    "shadow":      "rgba(0,0,0,0.25)",
    "toolbar_input_bg":      "rgba(255,255,255,0.12)",
    "toolbar_input_border":  "rgba(255,255,255,0.15)",
    "toolbar_input_color":   "#ffffff",
    "toolbar_placeholder":   "rgba(255,255,255,0.5)",
    "toolbar_btn_hover":     "rgba(255,255,255,0.15)",
    "toolbar_btn_color":     "#ffffff",
    "sync_btn_bg":           "rgba(255,255,255,0.1)",
    "sync_btn_hover":        "rgba(255,255,255,0.2)",
    "sync_btn_color":        "#ffffff",
}


# ─── Stylesheets ─────────────────────────────────────────────
def build_global_qss(t):
    """Build a comprehensive global stylesheet for the given theme dict."""
    return f"""
        QMainWindow {{
            background-color: {t['bg']};
            color: {t['text']};
        }}
        QWidget {{
            color: {t['text']};
            font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }}
        QToolBar {{
            background-color: {t['header_bg']};
            border: none;
            border-bottom: 1px solid {t['border']};
            spacing: 4px;
            padding: 6px 8px;
            min-height: 40px;
        }}
        QToolBar QLabel {{
            color: {t['header_fg']};
        }}
        QStatusBar {{
            background-color: {t['section_bg']};
            border-top: 1px solid {t['border']};
            font-size: 11px;
        }}
        QTabWidget::pane {{
            border: none;
            background-color: {t['bg']};
        }}
        QTabWidget {{
            background-color: {t['bg']};
        }}
        QTabBar {{
            background-color: {t['bg']};
        }}
        QTabBar::tab {{
            background-color: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 8px 18px;
            font-weight: 600;
            font-size: 12px;
            color: {t['text_dim']};
        }}
        QTabBar::tab:selected {{
            color: {t['accent']};
            border-bottom-color: {t['accent']};
        }}
        QTabBar::tab:hover {{
            color: {t['text']};
        }}
        QMenu {{
            background-color: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 24px 6px 12px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: {t['section_bg']};
        }}
        QComboBox {{
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 4px 8px;
            background-color: {t['card_bg']};
        }}
        QLineEdit {{
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 4px 8px;
            background-color: {t['card_bg']};
        }}
        QTextEdit {{
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 4px 8px;
            background-color: {t['card_bg']};
        }}
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 8px;
        }}
        QScrollBar::handle:vertical {{
            background: {t['border']};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: 8px;
        }}
        QScrollBar::handle:horizontal {{
            background: {t['border']};
            border-radius: 4px;
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        QPushButton {{
            font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }}
        QDialog {{
            background-color: {t['bg']};
        }}
        QDialogButtonBox QPushButton {{
            padding: 8px 20px;
            border-radius: 6px;
            font-weight: 600;
            border: 1px solid {t['border']};
        }}
        QDialogButtonBox QPushButton:default {{
            background-color: {t['accent']};
            color: white;
            border: none;
        }}
        QListWidget {{
            border: 1px solid {t['border']};
            border-radius: 6px;
            background-color: {t['card_bg']};
            outline: none;
        }}
        QListWidget::item {{
            padding: 8px 12px;
            border-bottom: 1px solid {t['border']};
        }}
        QListWidget::item:selected {{
            background-color: rgba(0, 115, 234, 0.12);
        }}
    """


# ─── Database ────────────────────────────────────────────────
class Database:
    def __init__(self, db_path=DB_FILE):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS groups_ (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL DEFAULT 'New Group',
                color       TEXT    NOT NULL DEFAULT '#0073ea',
                sort_order  INTEGER NOT NULL DEFAULT 0,
                collapsed   INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id    INTEGER NOT NULL,
                name        TEXT    NOT NULL DEFAULT 'New Task',
                status      TEXT    NOT NULL DEFAULT 'Not Started',
                priority    TEXT    NOT NULL DEFAULT 'Medium',
                due_date    TEXT,
                timeline_start TEXT,
                timeline_end   TEXT,
                notes       TEXT    DEFAULT '',
                progress    INTEGER NOT NULL DEFAULT 0,
                sort_order  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (group_id) REFERENCES groups_(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS subtasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id     INTEGER NOT NULL,
                text        TEXT    NOT NULL,
                done        INTEGER NOT NULL DEFAULT 0,
                sort_order  INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS labels (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id     INTEGER NOT NULL,
                name        TEXT    NOT NULL,
                color       TEXT    NOT NULL DEFAULT '#0073ea',
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS comments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id     INTEGER NOT NULL,
                text        TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL DEFAULT 'New Event',
                description TEXT    DEFAULT '',
                event_date  TEXT    NOT NULL,
                start_time  TEXT    DEFAULT '09:00',
                end_time    TEXT    DEFAULT '10:00',
                color       TEXT    NOT NULL DEFAULT '#0073ea',
                all_day     INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL DEFAULT 'Untitled',
                content     TEXT    DEFAULT '',
                color       TEXT    NOT NULL DEFAULT '#0073ea',
                pinned      INTEGER NOT NULL DEFAULT 0,
                folder      TEXT    NOT NULL DEFAULT '',
                sort_order  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS note_tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id     INTEGER NOT NULL,
                task_id     INTEGER NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                UNIQUE(note_id, task_id)
            );

            CREATE TABLE IF NOT EXISTS sync_deletions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type   TEXT    NOT NULL,
                group_name  TEXT,
                task_name   TEXT,
                deleted_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()
        self._migrate()

    def _migrate(self):
        """Add columns that may not exist in older databases."""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(notes)").fetchall()}
        if "folder" not in cols:
            self.conn.execute("ALTER TABLE notes ADD COLUMN folder TEXT NOT NULL DEFAULT ''")
        if "sort_order" not in cols:
            self.conn.execute("ALTER TABLE notes ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
        self.conn.commit()

    # ── Groups ──
    def get_groups(self):
        return self.conn.execute(
            "SELECT * FROM groups_ ORDER BY sort_order, id"
        ).fetchall()

    def add_group(self, name="New Group", color="#0073ea"):
        max_order = self.conn.execute("SELECT COALESCE(MAX(sort_order),0) FROM groups_").fetchone()[0]
        cur = self.conn.execute(
            "INSERT INTO groups_(name, color, sort_order) VALUES (?, ?, ?)",
            (name, color, max_order + 1)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_group(self, gid, **kwargs):
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [gid]
        self.conn.execute(f"UPDATE groups_ SET {sets} WHERE id=?", vals)
        self.conn.commit()

    def delete_group(self, gid):
        # Record deletion for sync before actually deleting
        row = self.conn.execute("SELECT name FROM groups_ WHERE id=?", (gid,)).fetchone()
        if row:
            group_name = row["name"]
            # Also record all tasks in this group as deleted
            tasks = self.conn.execute("SELECT name FROM tasks WHERE group_id=?", (gid,)).fetchall()
            for t in tasks:
                self.conn.execute(
                    "INSERT INTO sync_deletions(item_type, group_name, task_name) VALUES ('task', ?, ?)",
                    (group_name, t["name"])
                )
            self.conn.execute(
                "INSERT INTO sync_deletions(item_type, group_name) VALUES ('group', ?)",
                (group_name,)
            )
        self.conn.execute("DELETE FROM groups_ WHERE id=?", (gid,))
        self.conn.commit()

    # ── Tasks ──
    def get_tasks(self, group_id=None):
        if group_id is not None:
            return self.conn.execute(
                "SELECT * FROM tasks WHERE group_id=? ORDER BY sort_order, id",
                (group_id,)
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM tasks ORDER BY sort_order, id"
        ).fetchall()

    def add_task(self, group_id, name="New Task"):
        max_order = self.conn.execute(
            "SELECT COALESCE(MAX(sort_order),0) FROM tasks WHERE group_id=?",
            (group_id,)
        ).fetchone()[0]
        cur = self.conn.execute(
            "INSERT INTO tasks(group_id, name, sort_order) VALUES (?, ?, ?)",
            (group_id, name, max_order + 1)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_task(self, tid, **kwargs):
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [tid]
        self.conn.execute(f"UPDATE tasks SET {sets} WHERE id=?", vals)
        self.conn.commit()

    def delete_task(self, tid):
        # Record deletion for sync
        row = self.conn.execute(
            "SELECT t.name as task_name, g.name as group_name FROM tasks t JOIN groups_ g ON t.group_id = g.id WHERE t.id=?",
            (tid,)
        ).fetchone()
        if row:
            self.conn.execute(
                "INSERT INTO sync_deletions(item_type, group_name, task_name) VALUES ('task', ?, ?)",
                (row["group_name"], row["task_name"])
            )
        self.conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
        self.conn.commit()

    def move_task(self, tid, new_group_id):
        self.conn.execute("UPDATE tasks SET group_id=? WHERE id=?", (new_group_id, tid))
        self.conn.commit()

    def get_tasks_by_date(self, date_str):
        return self.conn.execute(
            "SELECT * FROM tasks WHERE due_date=? ORDER BY sort_order, id",
            (date_str,)
        ).fetchall()

    # ── Subtasks ──
    def get_subtasks(self, task_id):
        return self.conn.execute(
            "SELECT * FROM subtasks WHERE task_id=? ORDER BY sort_order, id",
            (task_id,)
        ).fetchall()

    def add_subtask(self, task_id, text):
        cur = self.conn.execute(
            "INSERT INTO subtasks(task_id, text) VALUES (?, ?)",
            (task_id, text)
        )
        self.conn.commit()
        return cur.lastrowid

    def toggle_subtask(self, sid):
        self.conn.execute("UPDATE subtasks SET done = 1 - done WHERE id=?", (sid,))
        self.conn.commit()

    def delete_subtask(self, sid):
        self.conn.execute("DELETE FROM subtasks WHERE id=?", (sid,))
        self.conn.commit()

    # ── Comments ──
    def get_comments(self, task_id):
        return self.conn.execute(
            "SELECT * FROM comments WHERE task_id=? ORDER BY created_at DESC",
            (task_id,)
        ).fetchall()

    def add_comment(self, task_id, text):
        cur = self.conn.execute(
            "INSERT INTO comments(task_id, text) VALUES (?, ?)",
            (task_id, text)
        )
        self.conn.commit()
        return cur.lastrowid

    # ── Labels ──
    def get_labels(self, task_id):
        return self.conn.execute(
            "SELECT * FROM labels WHERE task_id=? ORDER BY id",
            (task_id,)
        ).fetchall()

    def add_label(self, task_id, name, color="#0073ea"):
        cur = self.conn.execute(
            "INSERT INTO labels(task_id, name, color) VALUES (?, ?, ?)",
            (task_id, name, color)
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_label(self, lid):
        self.conn.execute("DELETE FROM labels WHERE id=?", (lid,))
        self.conn.commit()

    # ── Events ──
    def get_events(self, date_str=None):
        if date_str:
            return self.conn.execute(
                "SELECT * FROM events WHERE event_date=? ORDER BY start_time",
                (date_str,)
            ).fetchall()
        return self.conn.execute("SELECT * FROM events ORDER BY event_date, start_time").fetchall()

    def get_events_range(self, start_date, end_date):
        return self.conn.execute(
            "SELECT * FROM events WHERE event_date >= ? AND event_date <= ? ORDER BY event_date, start_time",
            (start_date, end_date)
        ).fetchall()

    def add_event(self, title, event_date, start_time="09:00", end_time="10:00", color="#0073ea", all_day=0, description=""):
        cur = self.conn.execute(
            "INSERT INTO events(title, event_date, start_time, end_time, color, all_day, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, event_date, start_time, end_time, color, all_day, description)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_event(self, eid, **kwargs):
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [eid]
        self.conn.execute(f"UPDATE events SET {sets} WHERE id=?", vals)
        self.conn.commit()

    def delete_event(self, eid):
        self.conn.execute("DELETE FROM events WHERE id=?", (eid,))
        self.conn.commit()

    # ── Notes ──
    def get_notes(self):
        return self.conn.execute(
            "SELECT * FROM notes ORDER BY pinned DESC, folder, sort_order, updated_at DESC"
        ).fetchall()

    def get_note_folders(self):
        """Return distinct folder names (excluding empty = unfiled)."""
        rows = self.conn.execute(
            "SELECT DISTINCT folder FROM notes WHERE folder != '' ORDER BY folder"
        ).fetchall()
        return [r["folder"] for r in rows]

    def reorder_notes(self, note_ids):
        """Set sort_order based on position in the given id list."""
        for i, nid in enumerate(note_ids):
            self.conn.execute("UPDATE notes SET sort_order=? WHERE id=?", (i, nid))
        self.conn.commit()

    def add_note(self, title="Untitled", content="", color="#0073ea", folder=""):
        max_order = self.conn.execute("SELECT COALESCE(MAX(sort_order),0) FROM notes").fetchone()[0]
        cur = self.conn.execute(
            "INSERT INTO notes(title, content, color, folder, sort_order) VALUES (?, ?, ?, ?, ?)",
            (title, content, color, folder, max_order + 1)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_note(self, nid, **kwargs):
        kwargs["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [nid]
        self.conn.execute(f"UPDATE notes SET {sets} WHERE id=?", vals)
        self.conn.commit()

    def delete_note(self, nid):
        self.conn.execute("DELETE FROM notes WHERE id=?", (nid,))
        self.conn.commit()

    # ── Note-Task Links ──
    def get_note_tasks(self, note_id):
        return self.conn.execute(
            "SELECT t.* FROM tasks t JOIN note_tasks nt ON t.id = nt.task_id WHERE nt.note_id=?",
            (note_id,)
        ).fetchall()

    def get_task_notes(self, task_id):
        return self.conn.execute(
            "SELECT n.* FROM notes n JOIN note_tasks nt ON n.id = nt.note_id WHERE nt.task_id=?",
            (task_id,)
        ).fetchall()

    def link_note_task(self, note_id, task_id):
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO note_tasks(note_id, task_id) VALUES (?, ?)",
                (note_id, task_id)
            )
            self.conn.commit()
        except Exception:
            pass

    def unlink_note_task(self, note_id, task_id):
        self.conn.execute(
            "DELETE FROM note_tasks WHERE note_id=? AND task_id=?",
            (note_id, task_id)
        )
        self.conn.commit()

    # ── Sync Deletions ──
    def is_deleted(self, item_type, group_name, task_name=None):
        """Check if an item was locally deleted and shouldn't be re-created by sync."""
        if item_type == "group":
            row = self.conn.execute(
                "SELECT id FROM sync_deletions WHERE item_type='group' AND group_name=?",
                (group_name,)
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT id FROM sync_deletions WHERE item_type='task' AND group_name=? AND task_name=?",
                (group_name, task_name)
            ).fetchone()
        return row is not None

    def clear_sync_deletions(self):
        """Clear deletion records after successful push (remote is now in sync)."""
        self.conn.execute("DELETE FROM sync_deletions")
        self.conn.commit()

    def get_sync_deletions(self):
        return self.conn.execute("SELECT * FROM sync_deletions").fetchall()

    # ── Stats ──
    def get_stats(self):
        rows = self.conn.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status").fetchall()
        total = sum(r["cnt"] for r in rows)
        stat = {s: 0 for s in STATUSES}
        for r in rows:
            if r["status"] in stat:
                stat[r["status"]] = r["cnt"]
        progress = (stat["Done"] / total * 100) if total > 0 else 0
        overdue = self.conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE due_date < date('now') AND status != 'Done' AND due_date IS NOT NULL"
        ).fetchone()[0]
        return {"total": total, "by_status": stat, "progress": progress, "overdue": overdue}

    # ── Export / Import ──
    def export_json(self):
        data = {"groups": [], "exported_at": datetime.now().isoformat()}
        for g in self.get_groups():
            gd = dict(g)
            gd["tasks"] = []
            for t in self.get_tasks(g["id"]):
                td = dict(t)
                td["subtasks"] = [dict(s) for s in self.get_subtasks(t["id"])]
                td["comments"] = [dict(c) for c in self.get_comments(t["id"])]
                td["labels"]   = [dict(l) for l in self.get_labels(t["id"])]
                gd["tasks"].append(td)
            data["groups"].append(gd)
        return data

    def import_json(self, data):
        for gd in data.get("groups", []):
            gid = self.add_group(gd.get("name", "Imported"), gd.get("color", "#0073ea"))
            for td in gd.get("tasks", []):
                tid = self.add_task(gid, td.get("name", "Task"))
                self.update_task(tid,
                    status=td.get("status", "Not Started"),
                    priority=td.get("priority", "Medium"),
                    due_date=td.get("due_date"),
                    notes=td.get("notes", ""),
                    progress=td.get("progress", 0)
                )
                for s in td.get("subtasks", []):
                    sid = self.add_subtask(tid, s.get("text", ""))
                    if s.get("done"):
                        self.toggle_subtask(sid)
                for c in td.get("comments", []):
                    self.add_comment(tid, c.get("text", ""))
                for l in td.get("labels", []):
                    self.add_label(tid, l.get("name", ""), l.get("color", "#0073ea"))

    def close(self):
        self.conn.close()


# ─── Sync Manager ────────────────────────────────────────────
class SyncManager:
    """Handles sync with Google Apps Script + Google Sheets backend."""

    STATUS_OK = "ok"
    STATUS_ERROR = "error"
    STATUS_SYNCING = "syncing"
    STATUS_IDLE = "idle"
    STATUS_NO_URL = "no_url"

    def __init__(self, db, status_callback=None):
        self.db = db
        self.db_path = db.conn.execute("PRAGMA database_list").fetchone()[2]
        self.sync_url = ""
        self.api_key = ""
        self.status = self.STATUS_NO_URL
        self.last_error = ""
        self.status_callback = status_callback
        self._load_config()

    def _thread_db(self):
        return Database(self.db_path)

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.sync_url = cfg.get("sync_url", "")
                self.api_key = cfg.get("api_key", "")
                if self.sync_url:
                    self.status = self.STATUS_IDLE
            except Exception:
                pass

    def save_config(self):
        cfg = {"sync_url": self.sync_url, "api_key": self.api_key}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def set_url(self, url, api_key=""):
        self.sync_url = url.strip()
        self.api_key = api_key.strip()
        self.save_config()
        self.status = self.STATUS_IDLE if self.sync_url else self.STATUS_NO_URL
        self._notify()

    def _notify(self):
        if self.status_callback:
            self.status_callback(self.status, self.last_error)

    def _http_get(self, url):
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "Flowdesk/1.0")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _http_post(self, url, data_dict):
        """Push data via POST using requests (handles Google's 302 correctly)."""
        data_dict["action"] = "syncAll"
        data_dict["key"] = self.api_key
        if _requests:
            resp = _requests.post(url, json=data_dict, timeout=120)
            return resp.json()
        else:
            # Fallback: GET — strip note content to stay under URL limit
            lite = json.loads(json.dumps(data_dict))  # deep copy
            for n in lite.get("notes", []):
                n["content"] = n.get("content", "")[:200] + "..." if len(n.get("content", "")) > 200 else n.get("content", "")
            data_str = json.dumps(lite, ensure_ascii=False)
            encoded = urllib.parse.quote(data_str)
            key_param = urllib.parse.quote(self.api_key)
            full_url = f"{url}?action=syncAll&key={key_param}&data={encoded}"
            req = urllib.request.Request(full_url, method="GET")
            req.add_header("User-Agent", "Flowdesk/1.0")
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))

    def pull(self):
        if not self.sync_url:
            self.status = self.STATUS_NO_URL
            self._notify()
            return False
        self.status = self.STATUS_SYNCING
        self._notify()
        try:
            db = self._thread_db()
            key_param = f"&key={urllib.parse.quote(self.api_key)}" if self.api_key else ""
            url = f"{self.sync_url}?action=getTasks{key_param}"
            remote = self._http_get(url)
            if remote.get("code") == 401:
                raise Exception("Unauthorized — check your API Key")
            remote_groups = remote.get("groups", [])

            # Build set of remote group names and their task names
            remote_group_names = set()
            remote_task_keys = set()  # (group_name, task_name)
            for rg in remote_groups:
                rg_name = rg.get("title", rg.get("name", "Imported"))
                remote_group_names.add(rg_name)
                for rt in rg.get("tasks", []):
                    remote_task_keys.add((rg_name, rt.get("name", "Task")))

            local_groups = db.get_groups()
            local_group_map = {g["name"]: dict(g) for g in local_groups}

            # 1) Merge remote → local (skip locally deleted items)
            for rg in remote_groups:
                rg_name = rg.get("title", rg.get("name", "Imported"))
                rg_color = rg.get("color", "#0073ea")
                rg_collapsed = rg.get("collapsed", False)

                # Skip if this group was locally deleted
                if db.is_deleted("group", rg_name):
                    continue

                if rg_name in local_group_map:
                    gid = local_group_map[rg_name]["id"]
                    db.update_group(gid, color=rg_color, collapsed=int(bool(rg_collapsed)))
                else:
                    gid = db.add_group(rg_name, rg_color)

                local_tasks = db.get_tasks(gid)
                local_task_map = {t["name"]: dict(t) for t in local_tasks}

                for rt in rg.get("tasks", []):
                    rt_name = rt.get("name", "Task")
                    rt_status = rt.get("status", "Not Started")
                    rt_priority = rt.get("priority", "Medium")
                    rt_due = rt.get("dueDate", rt.get("due_date"))
                    rt_notes = rt.get("notes", "")
                    rt_progress = rt.get("progress", 0)

                    # Skip if this task was locally deleted
                    if db.is_deleted("task", rg_name, rt_name):
                        continue

                    if rt_name in local_task_map:
                        tid = local_task_map[rt_name]["id"]
                        db.update_task(tid, status=rt_status, priority=rt_priority,
                                       due_date=rt_due, notes=rt_notes,
                                       progress=int(rt_progress) if rt_progress else 0)
                    else:
                        tid = db.add_task(gid, rt_name)
                        db.update_task(tid, status=rt_status, priority=rt_priority,
                                       due_date=rt_due, notes=rt_notes,
                                       progress=int(rt_progress) if rt_progress else 0)

                # NOTE: Never delete local tasks/groups during pull.
                # Local is authoritative — pull only adds/updates.

            # ── Sync Events (Calendar) from remote ──
            remote_events = remote.get("events", [])
            if remote_events is not None:
                local_events = db.get_events()
                local_ev_titles = {ev["title"]: dict(ev) for ev in local_events}
                remote_ev_titles = set()
                for rev in remote_events:
                    t = rev.get("title", "")
                    remote_ev_titles.add(t)
                    if t in local_ev_titles:
                        lev = local_ev_titles[t]
                        db.update_event(lev["id"],
                            event_date=rev.get("date", ""),
                            start_time=rev.get("startTime", ""),
                            end_time=rev.get("endTime", ""),
                            color=rev.get("color", "#0073ea"),
                            all_day=1 if rev.get("allDay") else 0)
                    else:
                        db.add_event(t, rev.get("date", ""),
                            start_time=rev.get("startTime", "09:00"),
                            end_time=rev.get("endTime", "10:00"),
                            color=rev.get("color", "#0073ea"),
                            all_day=1 if rev.get("allDay") else 0)
                # NOTE: Never delete local events during pull.
                # Local is authoritative — pull only adds/updates.

            # ── Sync Notes from remote (add only, never delete local) ──
            remote_notes = remote.get("notes", [])
            if remote_notes:
                local_notes = db.get_notes()
                local_note_titles = {n["title"]: dict(n) for n in local_notes}
                for rn in remote_notes:
                    t = rn.get("title", "")
                    if not t or t in local_note_titles:
                        continue  # skip existing — local is authoritative
                    # Only add notes that don't exist locally
                    folder = rn.get("folder", "")
                    nid = db.add_note(t, rn.get("content", ""), folder=folder)
                    db.update_note(nid,
                        pinned=1 if rn.get("pinned") else 0,
                        sort_order=rn.get("sortOrder", rn.get("sort_order", 0)))

            db.conn.commit()
            db.conn.close()
            self.status = self.STATUS_OK
            self.last_error = ""
            self._notify()
            return True
        except Exception as e:
            self.status = self.STATUS_ERROR
            self.last_error = str(e)
            self._notify()
            return False

    def push(self):
        if not self.sync_url:
            self.status = self.STATUS_NO_URL
            self._notify()
            return False
        self.status = self.STATUS_SYNCING
        self._notify()
        try:
            db = self._thread_db()
            export = db.export_json()
            push_data = {"groups": []}
            for g in export.get("groups", []):
                gd = {
                    "id": g.get("id", ""), "title": g.get("name", ""),
                    "color": g.get("color", "#0073ea"),
                    "collapsed": bool(g.get("collapsed", 0)), "tasks": []
                }
                for t in g.get("tasks", []):
                    td = {
                        "id": t.get("id", ""), "groupId": g.get("id", ""),
                        "name": t.get("name", ""), "status": t.get("status", "Not Started"),
                        "priority": t.get("priority", "Medium"),
                        "dueDate": t.get("due_date", ""), "notes": t.get("notes", ""),
                        "progress": t.get("progress", 0),
                    }
                    gd["tasks"].append(td)
                push_data["groups"].append(gd)

            # Events (Calendar)
            push_data["events"] = []
            for ev in db.get_events():
                push_data["events"].append({
                    "id": str(ev["id"]), "title": ev["title"],
                    "date": ev["event_date"], "startTime": ev["start_time"],
                    "endTime": ev["end_time"], "color": ev["color"],
                    "allDay": bool(ev["all_day"]),
                })

            # Notes — full content sent; stored in Google Drive files (no size limit)
            push_data["notes"] = []
            for n in db.get_notes():
                nd = dict(n)
                push_data["notes"].append({
                    "id": str(nd["id"]), "title": nd["title"],
                    "content": nd.get("content", ""),
                    "pinned": bool(nd["pinned"]),
                    "folder": nd.get("folder", ""),
                    "sortOrder": nd.get("sort_order", 0),
                })

            result = self._http_post(self.sync_url, push_data)
            if result.get("code") == 401:
                raise Exception("Unauthorized — check your API Key")

            # Push succeeded — clear deletion records (remote now matches local)
            db.clear_sync_deletions()
            db.conn.close()
            self.status = self.STATUS_OK
            self.last_error = ""
            self._notify()
            return True
        except Exception as e:
            self.status = self.STATUS_ERROR
            self.last_error = str(e)
            self._notify()
            return False

    def sync(self):
        # Push first (local is authoritative), then pull to pick up remote-only items
        ok = self.push()
        if ok:
            ok = self.pull()
        return ok


# ─── Badge Widget ────────────────────────────────────────────
class BadgeWidget(QLabel):
    clicked = pyqtSignal()

    def __init__(self, text, color, min_w=90, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._min_w = min_w
        self.set_color(color)
        self.setFixedHeight(26)
        self.setMinimumWidth(min_w)

    def set_color(self, color):
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 13px;
                padding: 4px 14px;
                font-weight: 600;
                font-size: 11px;
                border: none;
            }}
            QLabel:hover {{
                background-color: {color};
                opacity: 0.85;
            }}
        """)

    def mousePressEvent(self, ev):
        self.clicked.emit()


# ─── Status/Priority Picker Dialog ──────────────────────────
class PickerDialog(QDialog):
    def __init__(self, title, options, colors, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(320)
        self.chosen = current

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        label = QLabel(title)
        label.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        layout.addWidget(label)

        grid = QGridLayout()
        grid.setSpacing(6)
        cols = 3
        for i, opt in enumerate(options):
            btn = QPushButton(opt)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            c = colors.get(opt, "#999")
            border = "2px solid #0073ea" if opt == current else "1px solid transparent"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c};
                    color: white;
                    border: {border};
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 11px;
                    padding: 2px 4px;
                }}
                QPushButton:hover {{ border: 2px solid rgba(255,255,255,0.4); }}
            """)
            btn.clicked.connect(lambda checked, o=opt: self._pick(o))
            grid.addWidget(btn, i // cols, i % cols)
        layout.addLayout(grid)

        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(30)
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)

    def _pick(self, option):
        self.chosen = option
        self.accept()


# ─── Event Edit Dialog ──────────────────────────────────────
class EventEditDialog(QDialog):
    def __init__(self, db, event_id=None, default_date=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.event_id = event_id

        if event_id:
            ev = dict(db.conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone())
            self.setWindowTitle("Edit Event")
        else:
            ev = {
                "title": "", "description": "",
                "event_date": default_date or date.today().isoformat(),
                "start_time": "09:00", "end_time": "10:00",
                "color": "#0073ea", "all_day": 0
            }
            self.setWindowTitle("New Event")

        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 14, 14, 14)

        form = QFormLayout()
        form.setSpacing(6)

        self.title_edit = QLineEdit(ev["title"])
        self.title_edit.setPlaceholderText("Event title...")
        form.addRow("Title:", self.title_edit)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.fromString(ev["event_date"], "yyyy-MM-dd"))
        form.addRow("Date:", self.date_edit)

        self.all_day_check = QCheckBox("All day")
        self.all_day_check.setChecked(bool(ev["all_day"]))
        self.all_day_check.stateChanged.connect(self._toggle_time)
        form.addRow("", self.all_day_check)

        time_row = QHBoxLayout()
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(QTime.fromString(ev["start_time"], "HH:mm"))
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setTime(QTime.fromString(ev["end_time"], "HH:mm"))
        self.time_label_start = QLabel("From:")
        self.time_label_end = QLabel("To:")
        time_row.addWidget(self.time_label_start)
        time_row.addWidget(self.start_time)
        time_row.addWidget(self.time_label_end)
        time_row.addWidget(self.end_time)
        form.addRow("Time:", time_row)

        # Color picker
        self._event_color = ev["color"]
        color_row = QHBoxLayout()
        for c in EVENT_COLORS:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            border = "2px solid white" if c == self._event_color else "1px solid transparent"
            btn.setStyleSheet(f"background-color: {c}; border: {border}; border-radius: 12px;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, col=c: self._set_color(col))
            color_row.addWidget(btn)
        color_row.addStretch()
        form.addRow("Color:", color_row)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Description (optional)...")
        self.desc_edit.setPlainText(ev.get("description", ""))
        self.desc_edit.setMaximumHeight(80)
        form.addRow("Notes:", self.desc_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        if event_id:
            del_btn = buttons.addButton("Delete", QDialogButtonBox.ButtonRole.DestructiveRole)
            del_btn.setStyleSheet("color: #e2445c;")
            del_btn.clicked.connect(self._delete)

        layout.addWidget(buttons)
        self._toggle_time()

    def _set_color(self, color):
        self._event_color = color

    def _toggle_time(self):
        hide = self.all_day_check.isChecked()
        self.start_time.setVisible(not hide)
        self.end_time.setVisible(not hide)
        self.time_label_start.setVisible(not hide)
        self.time_label_end.setVisible(not hide)

    def _save(self):
        title = self.title_edit.text().strip() or "Untitled Event"
        d = self.date_edit.date().toString("yyyy-MM-dd")
        st = self.start_time.time().toString("HH:mm")
        et = self.end_time.time().toString("HH:mm")
        ad = int(self.all_day_check.isChecked())
        desc = self.desc_edit.toPlainText()

        if self.event_id:
            self.db.update_event(self.event_id, title=title, event_date=d,
                                 start_time=st, end_time=et, color=self._event_color,
                                 all_day=ad, description=desc)
        else:
            self.db.add_event(title, d, st, et, self._event_color, ad, desc)
        self.accept()

    def _delete(self):
        if self.event_id:
            reply = QMessageBox.question(self, "Delete Event", "Delete this event?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.db.delete_event(self.event_id)
                self.accept()


# ─── Calendar Widget ─────────────────────────────────────────
class CalendarView(QWidget):
    """Month / Week / Day calendar view with events and task due dates."""

    def __init__(self, db, theme, parent=None):
        super().__init__(parent)
        self.db = db
        self.theme = theme
        self.current_date = date.today()
        self.view_mode = "month"  # month, week, day
        self._build()

    def set_theme(self, theme):
        self.theme = theme
        self._refresh()

    def _build(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 8, 12, 8)
        self.main_layout.setSpacing(8)

        # Navigation bar
        nav = QHBoxLayout()
        nav.setSpacing(8)

        self.prev_btn = QPushButton("\u25c0")
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.clicked.connect(self._prev)
        nav.addWidget(self.prev_btn)

        self.today_btn = QPushButton("Today")
        self.today_btn.setFixedHeight(32)
        self.today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.today_btn.clicked.connect(self._go_today)
        nav.addWidget(self.today_btn)

        self.next_btn = QPushButton("\u25b6")
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self._next)
        nav.addWidget(self.next_btn)

        self.date_label = QLabel()
        self.date_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        nav.addWidget(self.date_label)

        nav.addStretch()

        for mode, label in [("month", "Month"), ("week", "Week"), ("day", "Day")]:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("view_mode", mode)
            btn.clicked.connect(lambda checked, m=mode: self._set_mode(m))
            nav.addWidget(btn)

        add_btn = QPushButton("+ Event")
        add_btn.setFixedHeight(28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("QPushButton { background-color: #0073ea; color: white; border: none; border-radius: 6px; padding: 4px 12px; font-weight: 600; } QPushButton:hover { background-color: #0066d9; }")
        add_btn.clicked.connect(self._add_event)
        nav.addWidget(add_btn)

        self.main_layout.addLayout(nav)

        # Content area
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_scroll.setWidget(self.content_widget)
        self.main_layout.addWidget(self.content_scroll)

        self._refresh()

    def _refresh(self):
        t = self.theme
        # Style nav buttons
        btn_style = f"""
            QPushButton {{
                background-color: {t['section_bg']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
                color: {t['text']};
            }}
            QPushButton:hover {{ background-color: {t['border']}; }}
        """
        self.prev_btn.setStyleSheet(btn_style)
        self.next_btn.setStyleSheet(btn_style)
        self.today_btn.setStyleSheet(btn_style)
        self.date_label.setStyleSheet(f"color: {t['text']};")

        # Clear content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.view_mode == "month":
            self._render_month()
        elif self.view_mode == "week":
            self._render_week()
        else:
            self._render_day()

    def _render_month(self):
        t = self.theme
        d = self.current_date
        self.date_label.setText(f"{d.strftime('%B %Y')}")

        grid = QGridLayout()
        grid.setSpacing(1)

        # Day headers
        for i, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            lbl = QLabel(day_name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Inter", 10, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {t['text_dim']}; padding: 4px;")
            grid.addWidget(lbl, 0, i)

        # Calendar days
        first_day = date(d.year, d.month, 1)
        start_weekday = first_day.weekday()  # 0=Mon
        days_in_month = cal_mod.monthrange(d.year, d.month)[1]

        # Get events and tasks for this month
        month_start = first_day.isoformat()
        month_end = date(d.year, d.month, days_in_month).isoformat()
        events = self.db.get_events_range(month_start, month_end)
        all_tasks = self.db.get_tasks()

        # Build date->items mapping
        date_events = {}
        for ev in events:
            dd = ev["event_date"]
            date_events.setdefault(dd, []).append(("event", dict(ev)))
        for task in all_tasks:
            if task["due_date"] and month_start <= task["due_date"] <= month_end:
                date_events.setdefault(task["due_date"], []).append(("task", dict(task)))

        row = 1
        col = start_weekday
        for day_num in range(1, days_in_month + 1):
            cell = self._make_day_cell(day_num, d.year, d.month, date_events, t)
            grid.addWidget(cell, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

        wrapper = QWidget()
        wrapper.setLayout(grid)
        self.content_layout.addWidget(wrapper)
        self.content_layout.addStretch()

    def _make_day_cell(self, day_num, year, month, date_events, t):
        d_str = f"{year}-{month:02d}-{day_num:02d}"
        is_today = d_str == date.today().isoformat()

        cell = QFrame()
        cell.setMinimumHeight(80)
        cell.setStyleSheet(f"""
            QFrame {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 4px;
            }}
            QFrame:hover {{ border-color: {t['accent']}; }}
        """)
        cell.setCursor(Qt.CursorShape.PointingHandCursor)
        cell.mousePressEvent = lambda e, ds=d_str: self._day_clicked(ds)

        layout = QVBoxLayout(cell)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(1)

        # Day number
        day_lbl = QLabel(str(day_num))
        day_lbl.setFont(QFont("Inter", 11, QFont.Weight.Bold if is_today else QFont.Weight.Normal))
        if is_today:
            day_lbl.setStyleSheet(f"color: white; background-color: {t['accent']}; border-radius: 10px; padding: 1px 6px; border: none;")
            day_lbl.setFixedSize(22, 22)
            day_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            day_lbl.setStyleSheet(f"color: {t['text']}; border: none;")
        layout.addWidget(day_lbl)

        # Items for this day (max 3 shown)
        items = date_events.get(d_str, [])
        for i, (item_type, item) in enumerate(items[:3]):
            if item_type == "event":
                pill = QLabel(item["title"][:15])
                pill.setStyleSheet(f"""
                    background-color: {item['color']};
                    color: white; border-radius: 3px;
                    padding: 1px 4px; font-size: 9px;
                    font-weight: 600; border: none;
                """)
            else:
                status_color = STATUS_COLORS.get(item.get("status", ""), "#999")
                pill = QLabel(f"\u25cb {item['name'][:14]}")
                pill.setStyleSheet(f"""
                    color: {status_color};
                    font-size: 9px; font-weight: 500;
                    border: none; padding: 0 2px;
                """)
            layout.addWidget(pill)

        if len(items) > 3:
            more = QLabel(f"+{len(items) - 3} more")
            more.setStyleSheet(f"color: {t['text_dim']}; font-size: 8px; border: none;")
            layout.addWidget(more)

        layout.addStretch()
        return cell

    def _render_week(self):
        t = self.theme
        d = self.current_date
        # Find Monday of current week
        monday = d - timedelta(days=d.weekday())
        sunday = monday + timedelta(days=6)
        self.date_label.setText(f"{monday.strftime('%b %d')} - {sunday.strftime('%b %d, %Y')}")

        events = self.db.get_events_range(monday.isoformat(), sunday.isoformat())
        all_tasks = self.db.get_tasks()

        grid = QGridLayout()
        grid.setSpacing(2)

        # Time column + 7 day columns
        hours = list(range(7, 22))
        for col_idx in range(7):
            day = monday + timedelta(days=col_idx)
            is_today = day == date.today()
            header = QLabel(day.strftime("%a %d"))
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setFont(QFont("Inter", 10, QFont.Weight.Bold))
            bg = t['accent'] if is_today else "transparent"
            fg = "white" if is_today else t['text']
            header.setStyleSheet(f"color: {fg}; background-color: {bg}; border-radius: 4px; padding: 4px; border: none;")
            grid.addWidget(header, 0, col_idx + 1)

        for row_idx, hour in enumerate(hours):
            time_lbl = QLabel(f"{hour:02d}:00")
            time_lbl.setStyleSheet(f"color: {t['text_dim']}; font-size: 9px; border: none;")
            time_lbl.setFixedWidth(40)
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            grid.addWidget(time_lbl, row_idx + 1, 0)

            for col_idx in range(7):
                day = monday + timedelta(days=col_idx)
                d_str = day.isoformat()
                cell = QFrame()
                cell.setMinimumHeight(36)
                cell.setStyleSheet(f"background-color: {t['card_bg']}; border: 1px solid {t['border']}; border-radius: 2px;")
                cell.setCursor(Qt.CursorShape.PointingHandCursor)
                cell.mousePressEvent = lambda e, ds=d_str, h=hour: self._week_cell_clicked(ds, h)
                cell_layout = QVBoxLayout(cell)
                cell_layout.setContentsMargins(2, 1, 2, 1)
                cell_layout.setSpacing(0)

                # Find events at this hour
                for ev in events:
                    if ev["event_date"] == d_str:
                        try:
                            ev_hour = int(ev["start_time"].split(":")[0])
                        except Exception:
                            ev_hour = 9
                        if ev_hour == hour:
                            pill = QLabel(ev["title"][:12])
                            pill.setStyleSheet(f"background-color: {ev['color']}; color: white; border-radius: 2px; padding: 1px 3px; font-size: 8px; font-weight: 600; border: none;")
                            pill.setCursor(Qt.CursorShape.PointingHandCursor)
                            eid = ev["id"]
                            pill.mousePressEvent = lambda e, _eid=eid: self._edit_event(_eid)
                            cell_layout.addWidget(pill)

                # Find tasks due this day (show only in first hour slot)
                if hour == 7:
                    for task in all_tasks:
                        if task["due_date"] == d_str and task["status"] != "Done":
                            pill = QLabel(f"\u25cb {task['name'][:11]}")
                            sc = STATUS_COLORS.get(task["status"], "#999")
                            pill.setStyleSheet(f"color: {sc}; font-size: 8px; border: none;")
                            cell_layout.addWidget(pill)

                grid.addWidget(cell, row_idx + 1, col_idx + 1)

        wrapper = QWidget()
        wrapper.setLayout(grid)
        self.content_layout.addWidget(wrapper)
        self.content_layout.addStretch()

    def _render_day(self):
        t = self.theme
        d = self.current_date
        self.date_label.setText(d.strftime("%A, %B %d, %Y"))

        d_str = d.isoformat()
        events = self.db.get_events(d_str)
        tasks = self.db.get_tasks_by_date(d_str)

        layout = QVBoxLayout()
        layout.setSpacing(6)

        # Events
        ev_header = QLabel(f"\u25cf Events ({len(events)})")
        ev_header.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        ev_header.setStyleSheet(f"color: {t['text']}; border: none;")
        layout.addWidget(ev_header)

        if not events:
            no_ev = QLabel("No events for this day")
            no_ev.setStyleSheet(f"color: {t['text_dim']}; font-size: 11px; padding: 8px; border: none;")
            layout.addWidget(no_ev)

        for ev in events:
            ev = dict(ev)
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {t['card_bg']};
                    border-left: 4px solid {ev['color']};
                    border-radius: 6px;
                    border-top: 1px solid {t['border']};
                    border-right: 1px solid {t['border']};
                    border-bottom: 1px solid {t['border']};
                }}
                QFrame:hover {{ border-left-color: {t['accent']}; }}
            """)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            eid = ev["id"]
            card.mousePressEvent = lambda e, _eid=eid: self._edit_event(_eid)

            cl = QHBoxLayout(card)
            cl.setContentsMargins(10, 8, 10, 8)

            time_str = "All Day" if ev["all_day"] else f"{ev['start_time']} - {ev['end_time']}"
            time_lbl = QLabel(time_str)
            time_lbl.setStyleSheet(f"color: {t['text_dim']}; font-size: 11px; font-weight: 600; min-width: 100px; border: none;")
            cl.addWidget(time_lbl)

            title_lbl = QLabel(ev["title"])
            title_lbl.setFont(QFont("Inter", 12, QFont.Weight.Medium))
            title_lbl.setStyleSheet("border: none;")
            cl.addWidget(title_lbl)
            cl.addStretch()

            layout.addWidget(card)

        # Tasks due
        task_header = QLabel(f"\u25cb Tasks Due ({len(tasks)})")
        task_header.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        task_header.setStyleSheet(f"color: {t['text']}; border: none; margin-top: 10px;")
        layout.addWidget(task_header)

        if not tasks:
            no_t = QLabel("No tasks due this day")
            no_t.setStyleSheet(f"color: {t['text_dim']}; font-size: 11px; padding: 8px; border: none;")
            layout.addWidget(no_t)

        for task in tasks:
            task = dict(task)
            card = QFrame()
            sc = STATUS_COLORS.get(task["status"], "#999")
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {t['card_bg']};
                    border-left: 4px solid {sc};
                    border-radius: 6px;
                    border-top: 1px solid {t['border']};
                    border-right: 1px solid {t['border']};
                    border-bottom: 1px solid {t['border']};
                }}
            """)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(10, 6, 10, 6)

            name_lbl = QLabel(task["name"])
            name_lbl.setFont(QFont("Inter", 11))
            name_lbl.setStyleSheet("border: none;")
            cl.addWidget(name_lbl)

            badge = QLabel(task["status"])
            badge.setStyleSheet(f"background-color: {sc}; color: white; border-radius: 8px; padding: 2px 8px; font-size: 10px; font-weight: 600; border: none;")
            cl.addWidget(badge)
            cl.addStretch()

            layout.addWidget(card)

        layout.addStretch()
        wrapper = QWidget()
        wrapper.setLayout(layout)
        self.content_layout.addWidget(wrapper)

    def _set_mode(self, mode):
        self.view_mode = mode
        self._refresh()

    def _prev(self):
        if self.view_mode == "month":
            m = self.current_date.month - 1
            y = self.current_date.year
            if m < 1:
                m = 12
                y -= 1
            self.current_date = date(y, m, 1)
        elif self.view_mode == "week":
            self.current_date -= timedelta(days=7)
        else:
            self.current_date -= timedelta(days=1)
        self._refresh()

    def _next(self):
        if self.view_mode == "month":
            m = self.current_date.month + 1
            y = self.current_date.year
            if m > 12:
                m = 1
                y += 1
            self.current_date = date(y, m, 1)
        elif self.view_mode == "week":
            self.current_date += timedelta(days=7)
        else:
            self.current_date += timedelta(days=1)
        self._refresh()

    def _go_today(self):
        self.current_date = date.today()
        self._refresh()

    def _day_clicked(self, date_str):
        self.current_date = date.fromisoformat(date_str)
        self.view_mode = "day"
        self._refresh()

    def _week_cell_clicked(self, date_str, hour):
        dlg = EventEditDialog(self.db, default_date=date_str, parent=self)
        dlg.start_time.setTime(QTime(hour, 0))
        dlg.end_time.setTime(QTime(hour + 1, 0))
        if dlg.exec():
            self._refresh()

    def _add_event(self):
        dlg = EventEditDialog(self.db, default_date=self.current_date.isoformat(), parent=self)
        if dlg.exec():
            self._refresh()

    def _edit_event(self, eid):
        dlg = EventEditDialog(self.db, event_id=eid, parent=self)
        if dlg.exec():
            self._refresh()


# ─── Rich Text Note Editor ───────────────────────────────────
class RichTextEditor(QWidget):
    content_changed = pyqtSignal()

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._build()

    def set_theme(self, theme):
        self.theme = theme
        t = theme
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t['card_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.6;
            }}
        """)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Toolbar
        tb = QHBoxLayout()
        tb.setSpacing(2)

        btn_style = """
            QPushButton {
                border: none; border-radius: 4px;
                padding: 4px 8px; font-size: 12px;
                background: transparent;
            }
            QPushButton:hover { background-color: rgba(0,0,0,0.08); }
            QPushButton:checked { background-color: rgba(0,115,234,0.15); color: #0073ea; }
        """

        self.bold_btn = QPushButton("B")
        self.bold_btn.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(30, 28)
        self.bold_btn.setStyleSheet(btn_style)
        self.bold_btn.clicked.connect(self._toggle_bold)
        tb.addWidget(self.bold_btn)

        self.italic_btn = QPushButton("I")
        f = QFont("Inter", 12)
        f.setItalic(True)
        self.italic_btn.setFont(f)
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(30, 28)
        self.italic_btn.setStyleSheet(btn_style)
        self.italic_btn.clicked.connect(self._toggle_italic)
        tb.addWidget(self.italic_btn)

        self.underline_btn = QPushButton("U")
        fu = QFont("Inter", 12)
        fu.setUnderline(True)
        self.underline_btn.setFont(fu)
        self.underline_btn.setCheckable(True)
        self.underline_btn.setFixedSize(30, 28)
        self.underline_btn.setStyleSheet(btn_style)
        self.underline_btn.clicked.connect(self._toggle_underline)
        tb.addWidget(self.underline_btn)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedWidth(1)
        sep1.setStyleSheet("color: #ccc;")
        tb.addWidget(sep1)

        # Heading combo
        self.heading_combo = QComboBox()
        self.heading_combo.addItems(["Normal", "Heading 1", "Heading 2", "Heading 3"])
        self.heading_combo.setFixedHeight(28)
        self.heading_combo.setFixedWidth(110)
        self.heading_combo.currentIndexChanged.connect(self._set_heading)
        tb.addWidget(self.heading_combo)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFixedWidth(1)
        sep2.setStyleSheet("color: #ccc;")
        tb.addWidget(sep2)

        self.bullet_btn = QPushButton("\u2022 List")
        self.bullet_btn.setFixedHeight(28)
        self.bullet_btn.setStyleSheet(btn_style)
        self.bullet_btn.clicked.connect(self._toggle_bullet)
        tb.addWidget(self.bullet_btn)

        self.num_btn = QPushButton("1. List")
        self.num_btn.setFixedHeight(28)
        self.num_btn.setStyleSheet(btn_style)
        self.num_btn.clicked.connect(self._toggle_numbered)
        tb.addWidget(self.num_btn)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setFixedWidth(1)
        sep3.setStyleSheet("color: #ccc;")
        tb.addWidget(sep3)

        self.code_btn = QPushButton("{ }")
        self.code_btn.setFixedHeight(28)
        self.code_btn.setStyleSheet(btn_style)
        self.code_btn.clicked.connect(self._insert_code_block)
        tb.addWidget(self.code_btn)

        self.highlight_btn = QPushButton("\u270e Highlight")
        self.highlight_btn.setFixedHeight(28)
        self.highlight_btn.setStyleSheet(btn_style)
        self.highlight_btn.clicked.connect(self._toggle_highlight)
        tb.addWidget(self.highlight_btn)

        tb.addStretch()
        layout.addLayout(tb)

        # Editor
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        t = self.theme
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t['card_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
            }}
        """)
        self.editor.textChanged.connect(self.content_changed.emit)
        self.editor.cursorPositionChanged.connect(self._update_toolbar_state)
        layout.addWidget(self.editor)

    def _update_toolbar_state(self):
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        self.bold_btn.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.italic_btn.setChecked(fmt.fontItalic())
        self.underline_btn.setChecked(fmt.fontUnderline())

    def _toggle_bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.bold_btn.isChecked() else QFont.Weight.Normal)
        self._merge_format(fmt)

    def _toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_btn.isChecked())
        self._merge_format(fmt)

    def _toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.underline_btn.isChecked())
        self._merge_format(fmt)

    def _set_heading(self, idx):
        cursor = self.editor.textCursor()
        block_fmt = QTextBlockFormat()
        char_fmt = QTextCharFormat()
        if idx == 0:  # Normal
            char_fmt.setFontPointSize(13)
            char_fmt.setFontWeight(QFont.Weight.Normal)
        elif idx == 1:  # H1
            char_fmt.setFontPointSize(22)
            char_fmt.setFontWeight(QFont.Weight.Bold)
        elif idx == 2:  # H2
            char_fmt.setFontPointSize(18)
            char_fmt.setFontWeight(QFont.Weight.Bold)
        elif idx == 3:  # H3
            char_fmt.setFontPointSize(15)
            char_fmt.setFontWeight(QFont.Weight.Bold)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.mergeBlockFormat(block_fmt)
        cursor.mergeCharFormat(char_fmt)
        self.editor.setTextCursor(cursor)

    def _toggle_bullet(self):
        cursor = self.editor.textCursor()
        current_list = cursor.currentList()
        if current_list and current_list.format().style() == QTextListFormat.Style.ListDisc:
            # Remove list
            block_fmt = QTextBlockFormat()
            block_fmt.setIndent(0)
            cursor.mergeBlockFormat(block_fmt)
            if current_list:
                current_list.remove(cursor.block())
        else:
            list_fmt = QTextListFormat()
            list_fmt.setStyle(QTextListFormat.Style.ListDisc)
            cursor.createList(list_fmt)

    def _toggle_numbered(self):
        cursor = self.editor.textCursor()
        current_list = cursor.currentList()
        if current_list and current_list.format().style() == QTextListFormat.Style.ListDecimal:
            block_fmt = QTextBlockFormat()
            block_fmt.setIndent(0)
            cursor.mergeBlockFormat(block_fmt)
            if current_list:
                current_list.remove(cursor.block())
        else:
            list_fmt = QTextListFormat()
            list_fmt.setStyle(QTextListFormat.Style.ListDecimal)
            cursor.createList(list_fmt)

    def _insert_code_block(self):
        cursor = self.editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontFamily("Courier New")
        fmt.setBackground(QColor("#f0f0f0"))
        fmt.setFontPointSize(12)
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        else:
            cursor.insertText("code here", fmt)
        self.editor.setTextCursor(cursor)

    def _toggle_highlight(self):
        cursor = self.editor.textCursor()
        fmt = QTextCharFormat()
        current = cursor.charFormat()
        if current.background().color().name() == "#fff3bf":
            fmt.setBackground(QColor("transparent"))
        else:
            fmt.setBackground(QColor("#fff3bf"))
        self._merge_format(fmt)

    def _merge_format(self, fmt):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def get_html(self):
        return self.editor.toHtml()

    def set_html(self, html):
        self.editor.setHtml(html)

    def get_plain_text(self):
        return self.editor.toPlainText()


# ─── Notes Page ──────────────────────────────────────────────
class NotesPage(QWidget):
    def __init__(self, db, theme, parent=None):
        super().__init__(parent)
        self.db = db
        self.theme = theme
        self.current_note_id = None
        self.current_folder = None  # None = show all, "" = unfiled, "X" = folder X
        self._build()

    def set_theme(self, theme):
        self.theme = theme
        self.editor.set_theme(theme)
        self._refresh_folders()
        self._refresh_list()

    def _build(self):
        # Debounce timer for auto-save
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._do_save)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Splitter for resizable left/right panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.setStyleSheet("QSplitter::handle { background: #e8e0c8; } QSplitter::handle:hover { background: #0073ea; }")

        # Left panel - folder + note list
        left = QWidget()
        left.setMinimumWidth(180)
        left.setMaximumWidth(500)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        title = QLabel("Notes")
        title.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()

        # New folder button
        new_folder_btn = QPushButton("\U0001F4C1")
        new_folder_btn.setFixedSize(28, 28)
        new_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_folder_btn.setToolTip("New Folder")
        new_folder_btn.setStyleSheet("QPushButton { border: none; font-size: 14px; background: transparent; } QPushButton:hover { background: rgba(0,0,0,0.06); border-radius: 6px; }")
        new_folder_btn.clicked.connect(self._new_folder)
        header.addWidget(new_folder_btn)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("QPushButton { background-color: #0073ea; color: white; border: none; border-radius: 14px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #0066d9; }")
        add_btn.clicked.connect(self._new_note)
        header.addWidget(add_btn)
        left_layout.addLayout(header)

        # Folder bar
        self.folder_scroll = QScrollArea()
        self.folder_scroll.setWidgetResizable(True)
        self.folder_scroll.setFixedHeight(34)
        self.folder_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.folder_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.folder_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollArea > QWidget > QWidget { background: transparent; }")
        self.folder_container = QWidget()
        self.folder_bar = QHBoxLayout(self.folder_container)
        self.folder_bar.setContentsMargins(0, 0, 0, 0)
        self.folder_bar.setSpacing(4)
        self.folder_scroll.setWidget(self.folder_container)
        left_layout.addWidget(self.folder_scroll)

        # Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search notes...")
        self.search.setFixedHeight(28)
        self.search.textChanged.connect(self._refresh_list)
        left_layout.addWidget(self.search)

        # Note list (drag-drop enabled)
        self.note_list = QListWidget()
        self.note_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.note_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.note_list.currentRowChanged.connect(self._on_note_selected)
        self.note_list.model().rowsMoved.connect(self._on_rows_moved)
        left_layout.addWidget(self.note_list)

        splitter.addWidget(left)

        # Right panel - editor
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 8, 12, 8)
        right_layout.setSpacing(6)

        # Note title + folder selector row
        title_row = QHBoxLayout()
        self.note_title = QLineEdit()
        self.note_title.setPlaceholderText("Note title...")
        self.note_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        self.note_title.setStyleSheet("border: none; background: transparent; padding: 4px;")
        self.note_title.textChanged.connect(self._save_current)
        title_row.addWidget(self.note_title)

        # Folder combo for current note
        self.folder_combo = QComboBox()
        self.folder_combo.setFixedWidth(130)
        self.folder_combo.setFixedHeight(26)
        self.folder_combo.setStyleSheet("QComboBox { font-size: 11px; padding: 2px 6px; border-radius: 4px; }")
        self.folder_combo.setToolTip("Move to folder")
        self.folder_combo.currentTextChanged.connect(self._on_folder_changed_for_note)
        title_row.addWidget(self.folder_combo)

        self.pin_btn = QPushButton("\u2606")
        self.pin_btn.setFixedSize(28, 28)
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.setStyleSheet("border: none; font-size: 16px; background: transparent;")
        self.pin_btn.clicked.connect(self._toggle_pin)
        title_row.addWidget(self.pin_btn)

        self.del_btn = QPushButton("\u2715")
        self.del_btn.setFixedSize(28, 28)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setStyleSheet("border: none; font-size: 14px; color: #e2445c; background: transparent;")
        self.del_btn.clicked.connect(self._delete_note)
        title_row.addWidget(self.del_btn)

        right_layout.addLayout(title_row)

        # Linked tasks
        self.linked_tasks_widget = QWidget()
        lt_layout = QHBoxLayout(self.linked_tasks_widget)
        lt_layout.setContentsMargins(4, 0, 4, 0)
        lt_layout.setSpacing(4)
        lt_label = QLabel("Linked Tasks:")
        lt_label.setStyleSheet("font-size: 10px; font-weight: 600; color: #999; border: none;")
        lt_layout.addWidget(lt_label)
        self.linked_tasks_area = QHBoxLayout()
        self.linked_tasks_area.setSpacing(4)
        lt_layout.addLayout(self.linked_tasks_area)
        lt_layout.addStretch()

        link_btn = QPushButton("+ Link Task")
        link_btn.setFixedHeight(22)
        link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        link_btn.setStyleSheet("QPushButton { background: transparent; color: #0073ea; border: 1px dashed #0073ea; border-radius: 4px; padding: 2px 8px; font-size: 10px; } QPushButton:hover { background: rgba(0,115,234,0.1); }")
        link_btn.clicked.connect(self._link_task)
        lt_layout.addWidget(link_btn)

        right_layout.addWidget(self.linked_tasks_widget)

        # Rich text editor
        self.editor = RichTextEditor(self.theme)
        self.editor.content_changed.connect(self._save_current)
        right_layout.addWidget(self.editor)

        # Metadata
        self.meta_label = QLabel()
        self.meta_label.setStyleSheet("color: #999; font-size: 10px; border: none;")
        right_layout.addWidget(self.meta_label)

        splitter.addWidget(right)
        splitter.setSizes([280, 700])  # default sizes
        layout.addWidget(splitter)

        self._refresh_folders()
        self._refresh_list()
        self._set_editor_enabled(False)

    # ── Folder management ──
    def _refresh_folders(self):
        """Rebuild the folder button bar."""
        while self.folder_bar.count():
            item = self.folder_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        folders = self.db.get_note_folders()
        t = self.theme

        def make_btn(label, folder_val, icon=""):
            active = self.current_folder == folder_val
            btn = QPushButton(f"{icon} {label}".strip())
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            bg = t.get("accent", "#0073ea") if active else "transparent"
            fg = "white" if active else t.get("text", "#3d3a33")
            border = "none" if active else f"1px solid {t.get('border', '#e8e0c8')}"
            btn.setStyleSheet(f"QPushButton {{ background: {bg}; color: {fg}; border: {border}; border-radius: 13px; padding: 2px 10px; font-size: 11px; font-weight: 600; }} QPushButton:hover {{ background: {t.get('accent', '#0073ea')}; color: white; }}")
            btn.clicked.connect(lambda: self._select_folder(folder_val))
            return btn

        self.folder_bar.addWidget(make_btn("All", None, ""))
        for f in folders:
            btn = make_btn(f, f, "\U0001F4C1")
            # Right-click to rename/delete folder
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, fn=f, b=btn: self._folder_context_menu(fn, b, pos))
            self.folder_bar.addWidget(btn)
        self.folder_bar.addStretch()

        # Update folder combo in editor
        self._refresh_folder_combo()

    def _refresh_folder_combo(self):
        """Update the folder dropdown in the editor."""
        self.folder_combo.blockSignals(True)
        self.folder_combo.clear()
        self.folder_combo.addItem("(No Folder)")
        for f in self.db.get_note_folders():
            self.folder_combo.addItem(f"\U0001F4C1 {f}")
        self.folder_combo.addItem("+ New Folder...")
        self.folder_combo.blockSignals(False)

    def _select_folder(self, folder_val):
        self.current_folder = folder_val
        self._refresh_folders()
        self._refresh_list()

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            # Just select it — it will be created when a note is assigned to it
            self.current_folder = name.strip()
            self._refresh_folders()
            self._refresh_list()

    def _folder_context_menu(self, folder_name, btn, pos):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        rename_act = menu.addAction("Rename Folder")
        delete_act = menu.addAction("Delete Folder")
        action = menu.exec(btn.mapToGlobal(pos))
        if action == rename_act:
            new_name, ok = QInputDialog.getText(self, "Rename Folder", "New name:", text=folder_name)
            if ok and new_name.strip() and new_name.strip() != folder_name:
                self.db.conn.execute("UPDATE notes SET folder=? WHERE folder=?", (new_name.strip(), folder_name))
                self.db.conn.commit()
                if self.current_folder == folder_name:
                    self.current_folder = new_name.strip()
                self._refresh_folders()
                self._refresh_list()
        elif action == delete_act:
            reply = QMessageBox.question(self, "Delete Folder",
                f"Move all notes in '{folder_name}' to unfiled?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.db.conn.execute("UPDATE notes SET folder='' WHERE folder=?", (folder_name,))
                self.db.conn.commit()
                if self.current_folder == folder_name:
                    self.current_folder = None
                self._refresh_folders()
                self._refresh_list()

    def _on_folder_changed_for_note(self, text):
        """When user changes folder via the combo box in the editor."""
        if not self.current_note_id:
            return
        if text == "+ New Folder...":
            name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
            if ok and name.strip():
                self.db.update_note(self.current_note_id, folder=name.strip())
                self._refresh_folders()
                self._refresh_list()
            else:
                # Reset combo to current value
                self._sync_folder_combo()
            return
        folder_val = "" if text == "(No Folder)" else text.replace("\U0001F4C1 ", "")
        self.db.update_note(self.current_note_id, folder=folder_val)
        self._refresh_folders()
        self._refresh_list()

    def _sync_folder_combo(self):
        """Set the folder combo to match the current note's folder."""
        if not self.current_note_id:
            return
        note = self.db.conn.execute("SELECT folder FROM notes WHERE id=?", (self.current_note_id,)).fetchone()
        if not note:
            return
        folder = note["folder"]
        self.folder_combo.blockSignals(True)
        if folder:
            target = f"\U0001F4C1 {folder}"
            idx = self.folder_combo.findText(target)
            if idx >= 0:
                self.folder_combo.setCurrentIndex(idx)
        else:
            self.folder_combo.setCurrentIndex(0)
        self.folder_combo.blockSignals(False)

    # ── Drag reorder ──
    def _on_rows_moved(self, *args):
        """After drag-drop reorder, persist the new order to DB."""
        new_order = []
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            nid = item.data(Qt.ItemDataRole.UserRole)
            if nid is not None:
                new_order.append(nid)
        if new_order:
            self.db.reorder_notes(new_order)
            # Update cache to match new order
            id_to_note = {n["id"]: n for n in self._notes_cache}
            self._notes_cache = [id_to_note[nid] for nid in new_order if nid in id_to_note]

    def _set_editor_enabled(self, enabled):
        self.note_title.setEnabled(enabled)
        self.editor.editor.setEnabled(enabled)
        self.pin_btn.setEnabled(enabled)
        self.del_btn.setEnabled(enabled)
        self.folder_combo.setEnabled(enabled)
        self.linked_tasks_widget.setVisible(enabled)
        if not enabled:
            self.note_title.clear()
            self.editor.set_html("")
            self.meta_label.setText("Select or create a note")

    def _refresh_list(self):
        self.note_list.blockSignals(True)
        self.note_list.clear()
        search = self.search.text().lower() if hasattr(self, 'search') else ""
        notes = self.db.get_notes()
        self._notes_cache = []
        for n in notes:
            n = dict(n)
            # Filter by folder
            if self.current_folder is not None:
                if n.get("folder", "") != self.current_folder:
                    continue
            # Filter by search
            if search and search not in n["title"].lower() and search not in n.get("content", "").lower():
                continue
            self._notes_cache.append(n)
            pin = "\u2605 " if n["pinned"] else ""
            folder_tag = f"[{n['folder']}] " if n.get("folder") and self.current_folder is None else ""
            item = QListWidgetItem(f"{pin}{folder_tag}{n['title']}")
            updated = n["updated_at"][:16] if n.get("updated_at") else ""
            item.setToolTip(f"Folder: {n.get('folder') or '(none)'}  |  Updated: {updated}")
            item.setData(Qt.ItemDataRole.UserRole, n["id"])
            self.note_list.addItem(item)
        self.note_list.blockSignals(False)

        # Re-select current note
        if self.current_note_id:
            for i in range(self.note_list.count()):
                if self.note_list.item(i).data(Qt.ItemDataRole.UserRole) == self.current_note_id:
                    self.note_list.setCurrentRow(i)
                    break

    def _on_note_selected(self, row):
        if row < 0 or row >= len(self._notes_cache):
            self._set_editor_enabled(False)
            self.current_note_id = None
            return

        note = self._notes_cache[row]
        self.current_note_id = note["id"]
        self._set_editor_enabled(True)

        self.note_title.blockSignals(True)
        self.note_title.setText(note["title"])
        self.note_title.blockSignals(False)

        self.editor.editor.blockSignals(True)
        self.editor.set_html(note.get("content", ""))
        self.editor.editor.blockSignals(False)

        self.pin_btn.setText("\u2605" if note["pinned"] else "\u2606")
        self.meta_label.setText(f"Created: {note['created_at'][:16]}  |  Updated: {note['updated_at'][:16]}")

        self._sync_folder_combo()
        self._refresh_linked_tasks()

    def _refresh_linked_tasks(self):
        # Clear existing
        while self.linked_tasks_area.count():
            item = self.linked_tasks_area.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.current_note_id:
            return

        linked = self.db.get_note_tasks(self.current_note_id)
        for task in linked:
            task = dict(task)
            sc = STATUS_COLORS.get(task["status"], "#999")
            chip = QPushButton(f"\u25cb {task['name'][:20]}  \u2715")
            chip.setFixedHeight(20)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setStyleSheet(f"QPushButton {{ background-color: {sc}; color: white; border: none; border-radius: 10px; padding: 2px 8px; font-size: 9px; font-weight: 600; }} QPushButton:hover {{ opacity: 0.8; }}")
            tid = task["id"]
            nid = self.current_note_id
            chip.clicked.connect(lambda checked, _nid=nid, _tid=tid: self._unlink_task(_nid, _tid))
            self.linked_tasks_area.addWidget(chip)

    def _save_current(self):
        """Debounced save - waits 500ms after last keystroke."""
        if not self.current_note_id:
            return
        self._save_timer.start()

    def _do_save(self):
        """Actually save to DB and update list item text."""
        if not self.current_note_id:
            return
        title = self.note_title.text().strip() or "Untitled"
        content = self.editor.get_html()
        self.db.update_note(self.current_note_id, title=title, content=content)

        # Update the left-side list item text without triggering full refresh
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == self.current_note_id:
                note = self.db.conn.execute("SELECT pinned, folder FROM notes WHERE id=?", (self.current_note_id,)).fetchone()
                pin = "\u2605 " if note and note["pinned"] else ""
                folder_tag = f"[{note['folder']}] " if note and note["folder"] and self.current_folder is None else ""
                item.setText(f"{pin}{folder_tag}{title}")
                break

        # Also update the cache
        for i, n in enumerate(self._notes_cache):
            if n["id"] == self.current_note_id:
                self._notes_cache[i]["title"] = title
                self._notes_cache[i]["content"] = content
                break

    def _new_note(self):
        folder = self.current_folder if self.current_folder is not None else ""
        nid = self.db.add_note("Untitled", "", EVENT_COLORS[len(self.db.get_notes()) % len(EVENT_COLORS)], folder=folder)
        self.current_note_id = nid
        self._refresh_folders()
        self._refresh_list()
        target_row = -1
        for i in range(self.note_list.count()):
            if self.note_list.item(i).data(Qt.ItemDataRole.UserRole) == nid:
                target_row = i
                break
        if target_row >= 0:
            self.note_list.setCurrentRow(target_row)
            self._on_note_selected(target_row)
        self.note_title.setFocus()
        self.note_title.selectAll()

    def _toggle_pin(self):
        if not self.current_note_id:
            return
        note = dict(self.db.conn.execute("SELECT * FROM notes WHERE id=?", (self.current_note_id,)).fetchone())
        new_pin = 0 if note["pinned"] else 1
        self.db.update_note(self.current_note_id, pinned=new_pin)
        self.pin_btn.setText("\u2605" if new_pin else "\u2606")
        self._refresh_list()

    def _delete_note(self):
        if not self.current_note_id:
            return
        reply = QMessageBox.question(self, "Delete Note", "Delete this note?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_note(self.current_note_id)
            self.current_note_id = None
            self._set_editor_enabled(False)
            self._refresh_folders()
            self._refresh_list()

    def _link_task(self):
        if not self.current_note_id:
            return
        all_tasks = self.db.get_tasks()
        linked_ids = {t["id"] for t in self.db.get_note_tasks(self.current_note_id)}
        available = [t for t in all_tasks if t["id"] not in linked_ids]
        if not available:
            QMessageBox.information(self, "Link Task", "No unlinked tasks available.")
            return
        names = [f"{t['name']} ({t['status']})" for t in available]
        chosen, ok = QInputDialog.getItem(self, "Link Task", "Select a task:", names, 0, False)
        if ok:
            idx = names.index(chosen)
            self.db.link_note_task(self.current_note_id, available[idx]["id"])
            self._refresh_linked_tasks()

    def _unlink_task(self, note_id, task_id):
        self.db.unlink_note_task(note_id, task_id)
        self._refresh_linked_tasks()


# ─── Task Edit Dialog ────────────────────────────────────────
class TaskEditDialog(QDialog):
    def __init__(self, db, task_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.task_id = task_id
        task = dict(self.db.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

        self.setWindowTitle(f"Edit Task: {task['name']}")
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 14, 14, 14)

        form = QFormLayout()
        form.setSpacing(6)

        self.name_edit = QLineEdit(task["name"])
        form.addRow("Task Name:", self.name_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItems(STATUSES)
        self.status_combo.setCurrentText(task["status"])
        form.addRow("Status:", self.status_combo)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(PRIORITIES)
        self.priority_combo.setCurrentText(task["priority"])
        form.addRow("Priority:", self.priority_combo)

        self.due_edit = QDateEdit()
        self.due_edit.setCalendarPopup(True)
        if task["due_date"]:
            self.due_edit.setDate(QDate.fromString(task["due_date"], "yyyy-MM-dd"))
        else:
            self.due_edit.setDate(QDate.currentDate())
        self.due_check = QCheckBox("Set due date")
        self.due_check.setChecked(bool(task["due_date"]))
        due_row = QHBoxLayout()
        due_row.addWidget(self.due_check)
        due_row.addWidget(self.due_edit)
        form.addRow("Due Date:", due_row)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(task["progress"])
        self.progress_label = QLabel(f"{task['progress']}%")
        self.progress_label.setFixedWidth(36)
        self.progress_slider.valueChanged.connect(
            lambda v: self.progress_label.setText(f"{v}%")
        )
        prog_row = QHBoxLayout()
        prog_row.addWidget(self.progress_slider)
        prog_row.addWidget(self.progress_label)
        form.addRow("Progress:", prog_row)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(task.get("notes", ""))
        self.notes_edit.setMaximumHeight(80)
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        # ── Linked Notes ──
        notes_label = QLabel("Linked Notes")
        notes_label.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        layout.addWidget(notes_label)

        linked_notes = self.db.get_task_notes(task_id)
        if linked_notes:
            for n in linked_notes:
                n = dict(n)
                lbl = QLabel(f"\u2022 {n['title']}")
                lbl.setStyleSheet("font-size: 11px; padding: 2px 0;")
                layout.addWidget(lbl)
        else:
            lbl = QLabel("No linked notes")
            lbl.setStyleSheet("font-size: 11px; color: #999; padding: 2px 0;")
            layout.addWidget(lbl)

        # ── Subtasks ──
        sub_label = QLabel("Subtasks")
        sub_label.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        layout.addWidget(sub_label)

        self.subtask_list = QVBoxLayout()
        self.subtask_list.setSpacing(2)
        self._load_subtasks()
        layout.addLayout(self.subtask_list)

        sub_add_row = QHBoxLayout()
        self.subtask_input = QLineEdit()
        self.subtask_input.setPlaceholderText("Add subtask...")
        sub_add_btn = QPushButton("+ Add")
        sub_add_btn.setFixedHeight(28)
        sub_add_btn.clicked.connect(self._add_subtask)
        self.subtask_input.returnPressed.connect(self._add_subtask)
        sub_add_row.addWidget(self.subtask_input)
        sub_add_row.addWidget(sub_add_btn)
        layout.addLayout(sub_add_row)

        # ── Comments ──
        cmt_label = QLabel("Comments")
        cmt_label.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        layout.addWidget(cmt_label)

        self.comment_list = QVBoxLayout()
        self.comment_list.setSpacing(2)
        self._load_comments()
        layout.addLayout(self.comment_list)

        comment_row = QHBoxLayout()
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Add comment...")
        comment_btn = QPushButton("Post")
        comment_btn.setFixedHeight(28)
        comment_btn.clicked.connect(self._add_comment)
        self.comment_input.returnPressed.connect(self._add_comment)
        comment_row.addWidget(self.comment_input)
        comment_row.addWidget(comment_btn)
        layout.addLayout(comment_row)

        # ── Buttons ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_subtasks(self):
        while self.subtask_list.count():
            item = self.subtask_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for s in self.db.get_subtasks(self.task_id):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            cb = QCheckBox(s["text"])
            cb.setChecked(bool(s["done"]))
            sid = s["id"]
            cb.stateChanged.connect(lambda state, _sid=sid: self._toggle_subtask(_sid))
            del_btn = QPushButton("\u00d7")
            del_btn.setFixedSize(22, 22)
            del_btn.setStyleSheet("border: none; color: #e2445c; font-size: 14px; font-weight: bold;")
            del_btn.clicked.connect(lambda checked, _sid=sid: self._del_subtask(_sid))
            row_layout.addWidget(cb)
            row_layout.addStretch()
            row_layout.addWidget(del_btn)
            self.subtask_list.addWidget(row_widget)

    def _add_subtask(self):
        text = self.subtask_input.text().strip()
        if text:
            self.db.add_subtask(self.task_id, text)
            self.subtask_input.clear()
            self._load_subtasks()

    def _toggle_subtask(self, sid):
        self.db.toggle_subtask(sid)

    def _del_subtask(self, sid):
        self.db.delete_subtask(sid)
        self._load_subtasks()

    def _load_comments(self):
        while self.comment_list.count():
            item = self.comment_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for c in self.db.get_comments(self.task_id):
            lbl = QLabel(f"[{c['created_at'][:16]}]  {c['text']}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 11px; padding: 3px 0; border-bottom: 1px solid rgba(128,128,128,0.2);")
            self.comment_list.addWidget(lbl)

    def _add_comment(self):
        text = self.comment_input.text().strip()
        if text:
            self.db.add_comment(self.task_id, text)
            self.comment_input.clear()
            self._load_comments()

    def _save(self):
        due = None
        if self.due_check.isChecked():
            due = self.due_edit.date().toString("yyyy-MM-dd")
        self.db.update_task(self.task_id,
            name=self.name_edit.text(),
            status=self.status_combo.currentText(),
            priority=self.priority_combo.currentText(),
            due_date=due,
            progress=self.progress_slider.value(),
            notes=self.notes_edit.toPlainText()
        )
        self.accept()


# ─── Group Table Widget ──────────────────────────────────────
class GroupTableWidget(QWidget):
    task_changed = pyqtSignal()

    def __init__(self, db, group, theme, search_text="", parent=None):
        super().__init__(parent)
        self.db = db
        self.group = dict(group)
        self.theme = theme
        self.search_text = search_text
        self.collapsed = bool(group["collapsed"])
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        t = self.theme

        # ── Header ──
        header_widget = QWidget()
        header_widget.setFixedHeight(40)
        header = QHBoxLayout(header_widget)
        header.setContentsMargins(10, 0, 10, 0)
        header.setSpacing(6)

        color_bar = QFrame()
        color_bar.setFixedSize(4, 22)
        color_bar.setStyleSheet(f"background-color: {self.group['color']}; border-radius: 2px; border: none;")
        header.addWidget(color_bar)

        self.arrow = QPushButton("\u25bc" if not self.collapsed else "\u25b6")
        self.arrow.setFixedSize(20, 20)
        self.arrow.setStyleSheet(f"border: none; color: {t['text']}; font-size: 10px; background: transparent;")
        self.arrow.setCursor(Qt.CursorShape.PointingHandCursor)
        self.arrow.clicked.connect(self._toggle_collapse)
        header.addWidget(self.arrow)

        title = QLabel(self.group["name"])
        title.setFont(QFont("Inter", 13, QFont.Weight.Bold))
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setStyleSheet("border: none; background: transparent;")
        title.mousePressEvent = lambda e: self._rename_group()
        header.addWidget(title)

        tasks = self.db.get_tasks(self.group["id"])
        count_lbl = QLabel(str(len(tasks)))
        count_lbl.setFixedSize(24, 18)
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_lbl.setStyleSheet(f"background-color: {t['border']}; border-radius: 9px; font-size: 10px; font-weight: 600; border: none; color: {t['text']};")
        header.addWidget(count_lbl)

        done = sum(1 for tk in tasks if tk["status"] == "Done")
        pct = int(done / len(tasks) * 100) if tasks else 0
        prog = QProgressBar()
        prog.setValue(pct)
        prog.setFixedSize(90, 6)
        prog.setTextVisible(False)
        prog.setStyleSheet(f"""
            QProgressBar {{ border: none; border-radius: 3px; background-color: {t['border']}; }}
            QProgressBar::chunk {{ background-color: {self.group['color']}; border-radius: 3px; }}
        """)
        header.addWidget(prog)
        pct_label = QLabel(f"{pct}%")
        pct_label.setStyleSheet(f"font-size: 10px; color: {t['text_dim']}; border: none; background: transparent;")
        header.addWidget(pct_label)

        header.addStretch()

        color_btn = QPushButton()
        color_btn.setFixedSize(18, 18)
        color_btn.setStyleSheet(f"QPushButton {{ background-color: {self.group['color']}; border: 1px solid {t['border']}; border-radius: 3px; }} QPushButton:hover {{ border-color: {t['accent']}; }}")
        color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        color_btn.clicked.connect(self._pick_color)
        header.addWidget(color_btn)

        del_btn = QPushButton("\u00d7")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet("color: #e2445c; font-size: 14px; font-weight: bold; border: none; background: transparent;")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(self._delete_group)
        header.addWidget(del_btn)

        header_widget.setStyleSheet(f"background-color: {t['section_bg']}; border: none; border-radius: 0;")
        layout.addWidget(header_widget)

        # ── Table ──
        self.table_container = QWidget()
        table_layout = QVBoxLayout(self.table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self.table = QTableWidget()
        cols = ["", "Task Name", "Status", "Priority", "Due Date", "Progress", "Notes"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 36)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 120)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self._edit_task)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)

        if self.search_text:
            tasks = [tk for tk in tasks if self.search_text in tk["name"].lower()]

        self._populate_table(tasks)

        row_count = self.table.rowCount()
        header_h = self.table.horizontalHeader().height()
        rows_h = sum(self.table.rowHeight(r) for r in range(row_count))
        self.table.setFixedHeight(header_h + rows_h + 2)

        table_layout.addWidget(self.table)

        add_btn = QPushButton("+ Add task")
        add_btn.setFixedHeight(28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{ text-align: left; padding: 0 10px; border: none; border-top: 1px dashed {t['border']}; background-color: transparent; color: {t['accent']}; font-weight: 500; font-size: 11px; }}
            QPushButton:hover {{ background-color: {t['section_bg']}; }}
        """)
        add_btn.clicked.connect(self._add_task)
        table_layout.addWidget(add_btn)

        layout.addWidget(self.table_container)

        if self.collapsed:
            self.table_container.hide()

        self.table.setStyleSheet(f"""
            QTableWidget {{ border: none; background-color: {t['card_bg']}; alternate-background-color: {t['card_bg']}; gridline-color: transparent; font-size: 13px; outline: none; }}
            QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid {t['border']}; }}
            QTableWidget::item:selected {{ background-color: rgba(0, 115, 234, 0.10); }}
            QHeaderView::section {{ background-color: {t['section_bg']}; border: none; border-bottom: 2px solid {t['border']}; padding: 6px 8px; font-weight: 700; font-size: 11px; color: {t['text_dim']}; text-transform: uppercase; letter-spacing: 0.5px; }}
        """)

        self.setStyleSheet(f"GroupTableWidget {{ background-color: {t['card_bg']}; border: 1px solid {t['border']}; border-radius: 10px; }}")

    def _populate_table(self, tasks):
        t = self.theme
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            task = dict(task)
            self.table.setRowHeight(row, 44)

            cb = QCheckBox()
            cb.setChecked(task["status"] == "Done")
            tid = task["id"]
            cb.stateChanged.connect(lambda state, _tid=tid: self._toggle_done(_tid, state))
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, cb_widget)

            name_item = QTableWidgetItem(task["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, task["id"])
            f = QFont("Inter", 13, QFont.Weight.Medium)
            if task["status"] == "Done":
                f.setStrikeOut(True)
                name_item.setForeground(QColor(t["text_dim"]))
            name_item.setFont(f)
            self.table.setItem(row, 1, name_item)

            badge = BadgeWidget(task["status"], STATUS_COLORS.get(task["status"], "#999"), min_w=110)
            badge.clicked.connect(lambda _tid=tid: self._pick_status(_tid))
            self.table.setCellWidget(row, 2, badge)

            pbadge = BadgeWidget(task["priority"], PRIORITY_COLORS.get(task["priority"], "#999"), min_w=90)
            pbadge.clicked.connect(lambda _tid=tid: self._pick_priority(_tid))
            self.table.setCellWidget(row, 3, pbadge)

            due = task["due_date"] or "\u2014"
            due_item = QTableWidgetItem(due)
            due_item.setFont(QFont("Inter", 11))
            if task["due_date"] and task["status"] != "Done":
                try:
                    d = date.fromisoformat(task["due_date"])
                    if d < date.today():
                        due_item.setForeground(QColor("#e2445c"))
                        due_item.setFont(QFont("Inter", 11, QFont.Weight.Bold))
                except Exception:
                    pass
            self.table.setItem(row, 4, due_item)

            prog_widget = QWidget()
            prog_layout = QHBoxLayout(prog_widget)
            prog_layout.setContentsMargins(4, 0, 4, 0)
            prog_layout.setSpacing(6)
            prog = QProgressBar()
            prog.setValue(task["progress"])
            prog.setFixedHeight(6)
            prog.setTextVisible(False)
            prog.setStyleSheet(f"""
                QProgressBar {{ border: none; border-radius: 3px; background-color: {t['border']}; }}
                QProgressBar::chunk {{ background-color: {t['accent']}; border-radius: 3px; }}
            """)
            prog_label = QLabel(f"{task['progress']}%")
            prog_label.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {t['text_dim']}; border: none;")
            prog_label.setFixedWidth(30)
            prog_layout.addWidget(prog, 1)
            prog_layout.addWidget(prog_label, 0)
            self.table.setCellWidget(row, 5, prog_widget)

            notes_item = QTableWidgetItem(task.get("notes", "")[:60])
            notes_item.setForeground(QColor(t["text_dim"]))
            notes_item.setFont(QFont("Inter", 11))
            self.table.setItem(row, 6, notes_item)

    def _toggle_collapse(self):
        self.collapsed = not self.collapsed
        self.arrow.setText("\u25b6" if self.collapsed else "\u25bc")
        self.table_container.setVisible(not self.collapsed)
        self.db.update_group(self.group["id"], collapsed=int(self.collapsed))

    def _rename_group(self):
        name, ok = QInputDialog.getText(self, "Rename Group", "Group name:", text=self.group["name"])
        if ok and name.strip():
            self.db.update_group(self.group["id"], name=name.strip())
            self.task_changed.emit()

    def _pick_color(self):
        dlg = PickerDialog("Select Group Color", GROUP_COLORS,
                           {c: c for c in GROUP_COLORS}, self.group["color"], self)
        if dlg.exec():
            self.db.update_group(self.group["id"], color=dlg.chosen)
            self.task_changed.emit()

    def _delete_group(self):
        reply = QMessageBox.question(self, "Delete Group",
            f"Delete group '{self.group['name']}' and all its tasks?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_group(self.group["id"])
            self.task_changed.emit()

    def _add_task(self):
        self.db.add_task(self.group["id"])
        self.task_changed.emit()

    def _toggle_done(self, tid, state):
        new_status = "Done" if state else "Not Started"
        self.db.update_task(tid, status=new_status)
        self.task_changed.emit()

    def _pick_status(self, tid):
        task = dict(self.db.conn.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone())
        dlg = PickerDialog("Select Status", STATUSES, STATUS_COLORS, task["status"], self)
        if dlg.exec():
            self.db.update_task(tid, status=dlg.chosen)
            self.task_changed.emit()

    def _pick_priority(self, tid):
        task = dict(self.db.conn.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone())
        dlg = PickerDialog("Select Priority", PRIORITIES, PRIORITY_COLORS, task["priority"], self)
        if dlg.exec():
            self.db.update_task(tid, priority=dlg.chosen)
            self.task_changed.emit()

    def _edit_task(self, index):
        row = index.row()
        item = self.table.item(row, 1)
        if item:
            tid = item.data(Qt.ItemDataRole.UserRole)
            dlg = TaskEditDialog(self.db, tid, self)
            if dlg.exec():
                self.task_changed.emit()

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 1)
        if not item:
            return
        tid = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)
        edit_action = menu.addAction("Edit Task")
        menu.addSeparator()
        del_action = menu.addAction("Delete Task")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == edit_action:
            dlg = TaskEditDialog(self.db, tid, self)
            if dlg.exec():
                self.task_changed.emit()
        elif action == del_action:
            self.db.delete_task(tid)
            self.task_changed.emit()


# ─── Kanban Card ─────────────────────────────────────────────
class KanbanCard(QFrame):
    def __init__(self, task, theme, parent=None):
        super().__init__(parent)
        self.task = dict(task)
        self.theme = theme
        self.setFrameStyle(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.setStyleSheet(f"""
            KanbanCard {{ background-color: {theme['card_bg']}; border: 1px solid {theme['border']}; border-radius: 6px; }}
            KanbanCard:hover {{ border-color: {theme['accent']}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(10, 8, 10, 8)

        name = QLabel(self.task["name"])
        name.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        name.setWordWrap(True)
        name.setStyleSheet("border: none;")
        layout.addWidget(name)

        meta = QHBoxLayout()
        meta.setSpacing(4)
        if self.task["due_date"]:
            due = QLabel(self.task['due_date'])
            due.setStyleSheet(f"color: {theme['text_dim']}; font-size: 10px; border: none;")
            meta.addWidget(due)
        meta.addStretch()
        priority_dot = QFrame()
        priority_dot.setFixedSize(8, 8)
        priority_dot.setStyleSheet(f"background-color: {PRIORITY_COLORS.get(self.task['priority'], '#999')}; border-radius: 4px; border: none;")
        meta.addWidget(priority_dot)
        layout.addLayout(meta)

        if self.task["progress"] > 0:
            prog = QProgressBar()
            prog.setValue(self.task["progress"])
            prog.setFixedHeight(4)
            prog.setTextVisible(False)
            prog.setStyleSheet(f"""
                QProgressBar {{ border: none; border-radius: 2px; background-color: {theme['border']}; }}
                QProgressBar::chunk {{ background-color: {theme['accent']}; border-radius: 2px; }}
            """)
            layout.addWidget(prog)


# ─── Kanban Column ───────────────────────────────────────────
class KanbanColumn(QFrame):
    task_moved = pyqtSignal(int, str)

    def __init__(self, status, tasks, theme, parent=None):
        super().__init__(parent)
        self.status = status
        self.theme = theme
        self.setAcceptDrops(True)
        self.setMinimumWidth(200)

        self.setStyleSheet(f"KanbanColumn {{ background-color: {theme['section_bg']}; border-radius: 8px; border: none; }}")

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        header.setSpacing(6)
        title = QLabel(status)
        title.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        title.setStyleSheet("border: none;")
        header.addWidget(title)

        count = QLabel(str(len(tasks)))
        count.setStyleSheet(f"background-color: {STATUS_COLORS.get(status, '#999')}; color: white; border-radius: 8px; padding: 1px 6px; font-size: 10px; font-weight: 600; border: none;")
        header.addWidget(count)
        header.addStretch()
        layout.addLayout(header)

        for task in tasks:
            card = KanbanCard(task, theme)
            layout.addWidget(card)

        layout.addStretch()

    def dragEnterEvent(self, ev):
        ev.acceptProposedAction()

    def dropEvent(self, ev):
        data = ev.mimeData()
        if data.hasText():
            tid = int(data.text())
            self.task_moved.emit(tid, self.status)


# ─── Sync Indicator Widget ──────────────────────────────────
class SyncIndicator(QPushButton):
    def __init__(self, parent=None):
        super().__init__("Sync", parent)
        self._status = SyncManager.STATUS_NO_URL
        self._theme = LIGHT_THEME
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def set_theme(self, theme):
        self._theme = theme
        self._update_style()

    def set_status(self, status):
        self._status = status
        self._update_style()

    def _update_style(self):
        colors = {
            SyncManager.STATUS_NO_URL: "#888888",
            SyncManager.STATUS_IDLE: "#888888",
            SyncManager.STATUS_SYNCING: "#fdab3d",
            SyncManager.STATUS_OK: "#00c875",
            SyncManager.STATUS_ERROR: "#e2445c",
        }
        dot_color = colors.get(self._status, "#888888")
        t = self._theme
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['sync_btn_bg']};
                color: {t['sync_btn_color']};
                border: none;
                border-radius: 6px;
                padding: 4px 14px 4px 24px;
                font-weight: 500;
                font-size: 12px;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {t['sync_btn_hover']};
            }}
        """)
        self.setText("Sync")
        self._dot_color = dot_color

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(self._dot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(10, (self.height() - 8) // 2, 8, 8)
        painter.end()


# ─── Main Window ─────────────────────────────────────────────
class FlowdeskApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.dark_mode = False
        self.theme = LIGHT_THEME
        self.search_text = ""

        # Sync
        self.sync_manager = SyncManager(self.db, self._on_sync_status)

        self.setWindowTitle("Flowdesk")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._setup_menu()
        self._setup_toolbar()
        self._setup_ui()
        self._setup_statusbar()
        self._apply_theme()
        self._refresh()

        # Seed a default group if empty
        if not self.db.get_groups():
            self.db.add_group("Todo", "#e2445c")
            self._refresh()

    def _add_action(self, menu, text, slot, shortcut=None):
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(shortcut)
        menu.addAction(action)
        return action

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self._add_action(file_menu, "New Group", self._new_group, "Ctrl+G")
        self._add_action(file_menu, "New Task", self._new_task_global, "Ctrl+N")
        self._add_action(file_menu, "New Event", self._new_event, "Ctrl+E")
        self._add_action(file_menu, "New Note", self._new_note, "Ctrl+Shift+N")
        file_menu.addSeparator()
        self._add_action(file_menu, "Set Sync URL...", self._set_sync_url)
        self._add_action(file_menu, "Sync Now", self._do_sync, "Ctrl+S")
        file_menu.addSeparator()
        self._add_action(file_menu, "Export JSON...", self._export)
        self._add_action(file_menu, "Import JSON...", self._import)
        file_menu.addSeparator()
        self._add_action(file_menu, "Quit", self.close, "Ctrl+Q")

        view_menu = menubar.addMenu("&View")
        self._add_action(view_menu, "Toggle Dark Mode", self._toggle_dark, "Ctrl+D")
        self._add_action(view_menu, "Expand All Groups", self._expand_all)
        self._add_action(view_menu, "Collapse All Groups", self._collapse_all)

    def _setup_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        tb.addWidget(QLabel("  "))

        new_task_btn = QPushButton("+ New Task")
        new_task_btn.setFixedHeight(28)
        new_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #0073ea; color: white;
                border: none; border-radius: 6px;
                padding: 4px 12px; font-weight: 600; font-size: 11px;
            }
            QPushButton:hover { background-color: #0066d9; }
        """)
        new_task_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_task_btn.clicked.connect(self._new_task_global)
        tb.addWidget(new_task_btn)

        tb.addWidget(QLabel("  "))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("  Search tasks...")
        self.search_input.setFixedWidth(220)
        self.search_input.setFixedHeight(28)
        self.search_input.textChanged.connect(self._on_search)
        tb.addWidget(self.search_input)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setStyleSheet("background: transparent; border: none;")
        tb.addWidget(spacer)

        # Sync indicator
        self.sync_indicator = SyncIndicator()
        self.sync_indicator.clicked.connect(self._do_sync)
        self._on_sync_status(self.sync_manager.status, "")
        tb.addWidget(self.sync_indicator)

        tb.addWidget(QLabel("  "))

        self.dark_btn = QPushButton("\u263d")
        self.dark_btn.setFixedSize(28, 28)
        self.dark_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dark_btn.clicked.connect(self._toggle_dark)
        tb.addWidget(self.dark_btn)

        tb.addWidget(QLabel("  "))

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Summary bar
        self.summary_bar = QWidget()
        self.summary_bar.setFixedHeight(34)
        self.summary_layout = QHBoxLayout(self.summary_bar)
        self.summary_layout.setContentsMargins(12, 0, 12, 0)
        self.summary_layout.setSpacing(16)
        self.summary_labels = {}
        for key in ["Total", "Done", "Working", "Stuck", "Overdue", "Progress"]:
            lbl = QLabel(f"{key}: 0")
            lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
            self.summary_layout.addWidget(lbl)
            self.summary_labels[key] = lbl
        self.summary_layout.addStretch()
        main_layout.addWidget(self.summary_bar)

        # Tab widget - now with 4 tabs
        self.tabs = QTabWidget()

        # Table view
        self.table_scroll = QScrollArea()
        self.table_scroll.setWidgetResizable(True)
        self.table_content = QWidget()
        self.table_layout = QVBoxLayout(self.table_content)
        self.table_layout.setSpacing(12)
        self.table_layout.setContentsMargins(16, 14, 16, 20)
        self.table_scroll.setWidget(self.table_content)
        self.tabs.addTab(self.table_scroll, "Table")

        # Kanban view
        self.kanban_scroll = QScrollArea()
        self.kanban_scroll.setWidgetResizable(True)
        self.kanban_content = QWidget()
        self.kanban_layout = QHBoxLayout(self.kanban_content)
        self.kanban_layout.setSpacing(10)
        self.kanban_layout.setContentsMargins(10, 10, 10, 10)
        self.kanban_scroll.setWidget(self.kanban_content)
        self.tabs.addTab(self.kanban_scroll, "Kanban")

        # Calendar view
        self.calendar_view = CalendarView(self.db, self.theme)
        self.tabs.addTab(self.calendar_view, "Calendar")

        # Notes view
        self.notes_page = NotesPage(self.db, self.theme)
        self.tabs.addTab(self.notes_page, "Notes")

        main_layout.addWidget(self.tabs)

    def _setup_statusbar(self):
        self.statusBar().showMessage("Ready")

    def _refresh(self):
        self._update_summary()
        self._render_table()
        self._render_kanban()
        if hasattr(self, 'calendar_view'):
            self.calendar_view._refresh()
        # Don't refresh notes list while user is actively editing
        # (it would steal focus / disrupt typing)

    def _update_summary(self):
        stats = self.db.get_stats()
        t = self.theme
        self.summary_labels["Total"].setText(f"Total: {stats['total']}")
        self.summary_labels["Total"].setStyleSheet(f"font-size: 12px; font-weight: 600; color: {t['text']};")
        self.summary_labels["Done"].setText(f"Done: {stats['by_status']['Done']}")
        self.summary_labels["Done"].setStyleSheet("font-size: 12px; font-weight: 600; color: #00c875;")
        self.summary_labels["Working"].setText(f"Working: {stats['by_status']['Working on it']}")
        self.summary_labels["Working"].setStyleSheet("font-size: 12px; font-weight: 600; color: #0073ea;")
        self.summary_labels["Stuck"].setText(f"Stuck: {stats['by_status']['Stuck']}")
        self.summary_labels["Stuck"].setStyleSheet("font-size: 12px; font-weight: 600; color: #e2445c;")
        self.summary_labels["Overdue"].setText(f"Overdue: {stats['overdue']}")
        self.summary_labels["Overdue"].setStyleSheet("font-size: 12px; font-weight: 600; color: #e2445c;")
        self.summary_labels["Progress"].setText(f"Progress: {stats['progress']:.0f}%")
        self.summary_labels["Progress"].setStyleSheet(f"font-size: 12px; font-weight: 600; color: {t['accent']};")

    def _render_table(self):
        while self.table_layout.count():
            item = self.table_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for group in self.db.get_groups():
            widget = GroupTableWidget(self.db, group, self.theme, self.search_text)
            widget.task_changed.connect(self._refresh)
            self.table_layout.addWidget(widget)

        add_group_btn = QPushButton("+ Add New Group")
        add_group_btn.setFixedHeight(32)
        add_group_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_group_btn.setStyleSheet(f"""
            QPushButton {{ padding: 0 12px; border: 1px dashed {self.theme['border']}; border-radius: 6px; color: {self.theme['accent']}; font-weight: 600; font-size: 11px; background: transparent; }}
            QPushButton:hover {{ background-color: {self.theme['section_bg']}; }}
        """)
        add_group_btn.clicked.connect(self._new_group)
        self.table_layout.addWidget(add_group_btn)
        self.table_layout.addStretch()

    def _render_kanban(self):
        while self.kanban_layout.count():
            item = self.kanban_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_tasks = self.db.get_tasks()
        for status in STATUSES:
            tasks = [t for t in all_tasks if t["status"] == status]
            if self.search_text:
                tasks = [t for t in tasks if self.search_text in t["name"].lower()]
            col = KanbanColumn(status, tasks, self.theme)
            col.task_moved.connect(self._move_task_status)
            self.kanban_layout.addWidget(col)

    def _move_task_status(self, tid, new_status):
        self.db.update_task(tid, status=new_status)
        self._refresh()

    def _new_group(self):
        name, ok = QInputDialog.getText(self, "New Group", "Group name:")
        if ok and name.strip():
            self.db.add_group(name.strip(), GROUP_COLORS[len(self.db.get_groups()) % len(GROUP_COLORS)])
            self._refresh()

    def _new_task_global(self):
        groups = self.db.get_groups()
        if not groups:
            self.db.add_group("Todo", "#e2445c")
            groups = self.db.get_groups()
        gid = groups[0]["id"]
        self.db.add_task(gid)
        self._refresh()

    def _new_event(self):
        dlg = EventEditDialog(self.db, parent=self)
        if dlg.exec():
            self._refresh()

    def _new_note(self):
        self.tabs.setCurrentWidget(self.notes_page)
        self.notes_page._new_note()

    def _on_search(self, text):
        self.search_text = text.lower()
        self._refresh()

    def _toggle_dark(self):
        self.dark_mode = not self.dark_mode
        self.theme = DARK_THEME if self.dark_mode else LIGHT_THEME
        self._apply_theme()
        self._refresh()

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(build_global_qss(t))

        # Central widget & scroll areas — force background propagation
        if hasattr(self, 'table_scroll'):
            self.table_scroll.setStyleSheet(f"QScrollArea {{ background-color: {t['bg']}; border: none; }}")
            self.table_scroll.viewport().setStyleSheet(f"background-color: {t['bg']};")
            self.table_content.setStyleSheet(f"background-color: {t['bg']};")
        if hasattr(self, 'kanban_scroll'):
            self.kanban_scroll.setStyleSheet(f"QScrollArea {{ background-color: {t['bg']}; border: none; }}")
            self.kanban_scroll.viewport().setStyleSheet(f"background-color: {t['bg']};")
            self.kanban_content.setStyleSheet(f"background-color: {t['bg']};")
        if self.centralWidget():
            self.centralWidget().setStyleSheet(f"background-color: {t['bg']};")

        self.summary_bar.setStyleSheet(f"background-color: {t['section_bg']}; border-bottom: 1px solid {t['border']};")
        # Toolbar search input
        if hasattr(self, 'search_input'):
            self.search_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {t['toolbar_input_bg']};
                    border: 1px solid {t['toolbar_input_border']};
                    border-radius: 6px; padding: 4px 10px;
                    font-size: 11px; color: {t['toolbar_input_color']};
                }}
                QLineEdit:focus {{ border-color: #0073ea; }}
                QLineEdit::placeholder {{ color: {t['toolbar_placeholder']}; }}
            """)
        # Dark mode toggle button
        if hasattr(self, 'dark_btn'):
            self.dark_btn.setStyleSheet(f"""
                QPushButton {{ border: none; font-size: 16px; color: {t['toolbar_btn_color']}; background: transparent; border-radius: 6px; }}
                QPushButton:hover {{ background-color: {t['toolbar_btn_hover']}; }}
            """)
        # Sync indicator
        if hasattr(self, 'sync_indicator'):
            self.sync_indicator.set_theme(t)
        if hasattr(self, 'calendar_view'):
            self.calendar_view.set_theme(t)
        if hasattr(self, 'notes_page'):
            self.notes_page.set_theme(t)

    def _expand_all(self):
        for g in self.db.get_groups():
            self.db.update_group(g["id"], collapsed=0)
        self._refresh()

    def _collapse_all(self):
        for g in self.db.get_groups():
            self.db.update_group(g["id"], collapsed=1)
        self._refresh()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", "flowdesk_export.json", "JSON (*.json)")
        if path:
            data = self.db.export_json()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.statusBar().showMessage(f"Exported to {path}", 3000)

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import JSON", "", "JSON (*.json)")
        if path:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.db.import_json(data)
            self._refresh()
            self.statusBar().showMessage(f"Imported from {path}", 3000)

    # ── Sync ──
    def _set_sync_url(self):
        current = self.sync_manager.sync_url
        url, ok = QInputDialog.getText(
            self, "Set Sync URL",
            "Enter Google Apps Script Web App URL:",
            text=current
        )
        if ok:
            current_key = self.sync_manager.api_key
            api_key, ok2 = QInputDialog.getText(
                self, "API Key",
                "Enter API Key (from Code.gs):\n(Leave empty to skip authentication)",
                text=current_key
            )
            if ok2:
                self.sync_manager.set_url(url, api_key)
            else:
                self.sync_manager.set_url(url)
            if url.strip():
                self.statusBar().showMessage("Sync URL & API Key saved", 3000)
            else:
                self.statusBar().showMessage("Sync URL cleared", 3000)

    def _do_sync(self):
        if not self.sync_manager.sync_url:
            self._set_sync_url()
            if not self.sync_manager.sync_url:
                return

        self.statusBar().showMessage("Syncing...")
        self.sync_indicator.set_status(SyncManager.STATUS_SYNCING)

        def _sync_thread():
            self.sync_manager.sync()

        t = threading.Thread(target=_sync_thread, daemon=True)
        t.start()

        def _check_done():
            if t.is_alive():
                QTimer.singleShot(200, _check_done)
            else:
                self._refresh()
                if self.sync_manager.status == SyncManager.STATUS_OK:
                    self.statusBar().showMessage("Sync complete", 3000)
                elif self.sync_manager.status == SyncManager.STATUS_ERROR:
                    self.statusBar().showMessage(f"Sync error: {self.sync_manager.last_error[:80]}", 5000)
                self.sync_indicator.set_status(self.sync_manager.status)

        QTimer.singleShot(200, _check_done)

    def _on_sync_status(self, status, error):
        QTimer.singleShot(0, lambda: self.sync_indicator.set_status(status))

    def closeEvent(self, event):
        self.db.close()
        event.accept()


# ─── Main ────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Inter", 12))
    app.setStyle("Fusion")

    window = FlowdeskApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
