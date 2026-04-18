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
    Qt, QSize, QDate, QTime, QTimer, pyqtSignal, QMimeData, QPoint,
    QPropertyAnimation, QEasingCurve, QSettings
)
from PyQt6.QtGui import (
    QColor, QPalette, QFont, QIcon, QAction, QPainter,
    QBrush, QPen, QDrag, QPixmap, QTextCharFormat, QTextListFormat,
    QTextBlockFormat, QTextCursor, QSyntaxHighlighter,
    QTextDocument, QTextFrameFormat, QKeySequence, QShortcut
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

TAG_COLORS = [
    ('#E8F0FE', '#1967D2'), ('#FCE8E6', '#C5221F'), ('#E6F4EA', '#137333'),
    ('#FEF7E0', '#B06000'), ('#F3E8FD', '#7627BB'), ('#E0F7FA', '#00838F'),
]

FONT_FAMILIES = {
    'Sans-serif': '"Helvetica Neue", -apple-system, sans-serif',
    'Serif': 'Georgia, "Times New Roman", serif',
    'Monospace': '"SF Mono", Menlo, Consolas, monospace',
}

def get_tag_color(tag):
    """Return (bg_color, text_color) for a tag based on its name hash."""
    h = hash(tag) % len(TAG_COLORS)
    return TAG_COLORS[h]

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

# ─── 5-Skin System (mirrors web's PRISM_SKIN_MAP) ────────────────
# Each skin is a full theme dict compatible with build_global_qss() and every
# per-widget set_theme() call. isDark controls hover/input overlays so buttons
# read correctly on dark vs light backgrounds.
def _make_skin(bg, sidebar, text, text_dim, border, accent, card, card_hover, toolbar, is_dark):
    overlay_alpha = "255,255,255" if is_dark else "0,0,0"
    return {
        "bg":          bg,
        "card_bg":     card,
        "header_bg":   toolbar,
        "header_fg":   text,
        "text":        text,
        "text_dim":    text_dim,
        "border":      border,
        "section_bg":  sidebar,
        "accent":      accent,
        "shadow":      f"rgba(0,0,0,{'0.25' if is_dark else '0.06'})",
        "toolbar_input_bg":      f"rgba({overlay_alpha},{'0.12' if is_dark else '0.05'})",
        "toolbar_input_border":  f"rgba({overlay_alpha},{'0.15' if is_dark else '0.10'})",
        "toolbar_input_color":   text,
        "toolbar_placeholder":   f"rgba({overlay_alpha},{'0.50' if is_dark else '0.40'})",
        "toolbar_btn_hover":     f"rgba({overlay_alpha},{'0.15' if is_dark else '0.08'})",
        "toolbar_btn_color":     text,
        "sync_btn_bg":           f"rgba({overlay_alpha},{'0.10' if is_dark else '0.06'})",
        "sync_btn_hover":        f"rgba({overlay_alpha},{'0.20' if is_dark else '0.12'})",
        "sync_btn_color":        text,
        "_is_dark":    is_dark,
        "_accent_2":   accent,
    }

PRISM_SKIN   = _make_skin("#EEF0F5", "#F4F5F9", "#1B1D2B", "#6B6F82", "#E2E4EC", "#4A5CC9", "#FFFFFF", "#F4F5F9", "#F4F5F9", False)
ATLAS_SKIN   = _make_skin("#F4EFE7", "#F0EADF", "#2C2419", "#7A6F5F", "#E3DBCB", "#B24A2D", "#FBF7EF", "#F0EADF", "#F0EADF", False)
MISSION_SKIN = _make_skin("#141516", "#1B1D1F", "#E8E6E1", "#8A8680", "#2B2E31", "#E89A3C", "#222527", "#2B2E31", "#1B1D1F", True)
HORIZON_SKIN = _make_skin("#F0EDE6", "#E8E4DA", "#23302A", "#6B7A72", "#D8D3C7", "#7B9880", "#FAF8F3", "#E8E4DA", "#E8E4DA", False)
EMBER_SKIN   = _make_skin("#0F1512", "#141B17", "#E8E4DA", "#7E8A82", "#233028", "#5FB39A", "#1A221D", "#233028", "#141B17", True)

SKIN_THEMES = {
    "prism":   PRISM_SKIN,
    "atlas":   ATLAS_SKIN,
    "mission": MISSION_SKIN,
    "horizon": HORIZON_SKIN,
    "ember":   EMBER_SKIN,
}
SKIN_LABELS = {
    "prism":   ("Prism",   "Cool indigo bento",      "#4A5CC9"),
    "atlas":   ("Atlas",   "Warm paper, editorial",  "#B24A2D"),
    "mission": ("Mission", "Dark operator console",  "#E89A3C"),
    "horizon": ("Horizon", "Sage garden calm",       "#7B9880"),
    "ember":   ("Ember",   "Deep teal focus",        "#5FB39A"),
}
SKIN_ORDER = ["prism", "atlas", "mission", "horizon", "ember"]

# Keep legacy LIGHT/DARK aliases so any downstream code that references them
# stays in working order. Light = Prism (cool bento), Dark = Mission (operator).
LIGHT_THEME = PRISM_SKIN
DARK_THEME = MISSION_SKIN


# ─── Bento / Atlas editorial content ─────────────────────────
ATLAS_TAGLINES = [
    "Of ledgers, letters, and light.",
    "All the work that's fit to ship.",
    "Process, published daily.",
    "The unhurried edition.",
    "Bound by craft, carried by calendar.",
    "A folio of open loops.",
    "Type, time, and tasks in good order.",
]

ATLAS_QUOTES = [
    ("Discipline equals freedom.",                 "Jocko Willink"),
    ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
    ("Slow is smooth. Smooth is fast.",            "Military adage"),
    ("Simplicity is the ultimate sophistication.", "Leonardo da Vinci"),
    ("Make it work, make it right, make it fast.", "Kent Beck"),
    ("The best time to plant a tree was 20 years ago. The second best time is now.", "Folk wisdom"),
    ("Done is better than perfect.",               "Sheryl Sandberg"),
    ("What gets measured gets managed.",           "Peter Drucker"),
    ("Focus is saying no.",                         "Steve Jobs"),
    ("Perfection is the enemy of good.",            "Voltaire"),
    ("A goal without a plan is just a wish.",       "Antoine de Saint-Exupéry"),
]

# Hotkey legend rendered in the Bento Dashboard's hotkey tile.
HOTKEY_ROWS = [
    ("New task",     ["⌘", "N"]),
    ("Focus search", ["⌘", "K"]),
    ("Quick sync",   ["⌘", "/"]),
    ("Focus mode",   ["⌘", "⇧", "F"]),
    ("Cycle skin",   ["⌘", "⇧", "T"]),
    ("Jump: Home",   ["g", "h"]),
    ("Jump: Flows",  ["g", "f"]),
    ("Jump: Board",  ["g", "b"]),
]


def day_of_year(d=None):
    """1-indexed day of year for the given date (default today)."""
    if d is None:
        d = date.today()
    start = date(d.year, 1, 1)
    return (d - start).days + 1


def atlas_quote_of_day(d=None):
    """Deterministic quote rotation keyed by day of year."""
    idx = day_of_year(d) % len(ATLAS_QUOTES)
    return ATLAS_QUOTES[idx]


def atlas_tagline_of_day(d=None):
    idx = day_of_year(d) % len(ATLAS_TAGLINES)
    return ATLAS_TAGLINES[idx]


def serif_font_family(skin_name):
    """Return a serif family string for skins that want editorial type."""
    if skin_name in ("atlas", "ember"):
        return '"Spectral", "Source Serif Pro", "Georgia", "Times New Roman", serif'
    return '"Helvetica Neue", -apple-system, "Segoe UI", sans-serif'


def classify_event_glyph(title):
    """Return (glyph, kind) tuple used by Calendar/dashboard event rows."""
    t = (title or "").lower()
    import re
    if re.search(r"\b(focus|deep\s*work|writing|heads[-\s]?down)\b", t):
        return ("●", "focus")
    if re.search(r"\b(call|zoom|meet|hangout|sync|1:1|1-on-1|standup|stand-up)\b", t):
        return ("○", "call")
    return ("◆", "meeting")


def priority_to_token(priority):
    """Map a priority string to a (level, label) token used by the P0/P1/P2 UI."""
    if not priority:
        return None
    p = str(priority).strip().lower()
    if p in ("", "none", "—"):
        return None
    if p in ("critical", "urgent", "p0"):
        return ("p0", "P0")
    if p in ("high", "p1"):
        return ("p1", "P1")
    if p in ("medium", "med", "p2"):
        return ("p2", "P2")
    if p in ("low", "p3"):
        return ("p3", "P3")
    return ("p2", "P2")


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
                gcal_id     TEXT    DEFAULT '',
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

            CREATE TABLE IF NOT EXISTS activity_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         TEXT    NOT NULL DEFAULT (datetime('now')),
                kind       TEXT    NOT NULL,
                target     TEXT    NOT NULL DEFAULT '',
                detail     TEXT    NOT NULL DEFAULT ''
            );
        """)
        self.conn.commit()
        self._migrate()

    def _migrate(self):
        """Add columns that may not exist in older databases."""
        # Notes migrations
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(notes)").fetchall()}
        if "folder" not in cols:
            self.conn.execute("ALTER TABLE notes ADD COLUMN folder TEXT NOT NULL DEFAULT ''")
        if "sort_order" not in cols:
            self.conn.execute("ALTER TABLE notes ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
        if "tags" not in cols:
            self.conn.execute("ALTER TABLE notes ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
        if "font" not in cols:
            self.conn.execute("ALTER TABLE notes ADD COLUMN font TEXT NOT NULL DEFAULT 'Sans-serif'")
        if "icon" not in cols:
            self.conn.execute("ALTER TABLE notes ADD COLUMN icon TEXT NOT NULL DEFAULT ''")
        if "cover" not in cols:
            self.conn.execute("ALTER TABLE notes ADD COLUMN cover TEXT NOT NULL DEFAULT ''")
        # Events migrations
        ev_cols = {r[1] for r in self.conn.execute("PRAGMA table_info(events)").fetchall()}
        if "gcal_id" not in ev_cols:
            self.conn.execute("ALTER TABLE events ADD COLUMN gcal_id TEXT DEFAULT ''")
        if "description" not in ev_cols:
            self.conn.execute("ALTER TABLE events ADD COLUMN description TEXT DEFAULT ''")
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
        self._log_activity("ADD", name, f"group#{group_id}")
        return cur.lastrowid

    def update_task(self, tid, **kwargs):
        # Snapshot name + prior status so we can build readable activity rows.
        prior = self.conn.execute(
            "SELECT name, status FROM tasks WHERE id=?", (tid,)
        ).fetchone()
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [tid]
        self.conn.execute(f"UPDATE tasks SET {sets} WHERE id=?", vals)
        self.conn.commit()
        if prior is not None and "status" in kwargs:
            new_status = kwargs.get("status")
            if new_status != prior["status"]:
                kind = "DONE" if new_status == "Done" else ("STUCK" if new_status == "Stuck" else "MOVED")
                self._log_activity(kind, prior["name"] or "", f"{prior['status']}→{new_status}")

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
            self._log_activity("DEL", row["task_name"] or "", row["group_name"] or "")
        self.conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
        self.conn.commit()

    def move_task(self, tid, new_group_id):
        # Resolve names for activity log before mutating.
        row = self.conn.execute(
            "SELECT t.name as task_name, g.name as from_group FROM tasks t JOIN groups_ g ON t.group_id = g.id WHERE t.id=?",
            (tid,)
        ).fetchone()
        to_group = self.conn.execute(
            "SELECT name FROM groups_ WHERE id=?", (new_group_id,)
        ).fetchone()
        self.conn.execute("UPDATE tasks SET group_id=? WHERE id=?", (new_group_id, tid))
        self.conn.commit()
        if row and to_group:
            self._log_activity("FLOW", row["task_name"] or "", f"{row['from_group']}→{to_group['name']}")

    # ── Activity log ──
    def _log_activity(self, kind, target, detail=""):
        """Append an event to activity_log; trim to most recent 200 rows."""
        try:
            self.conn.execute(
                "INSERT INTO activity_log(kind, target, detail) VALUES (?, ?, ?)",
                (kind, target or "", detail or "")
            )
            # Trim — keep only the latest 200 rows.
            self.conn.execute(
                "DELETE FROM activity_log WHERE id NOT IN "
                "(SELECT id FROM activity_log ORDER BY id DESC LIMIT 200)"
            )
            self.conn.commit()
        except Exception:
            # Never let logging take down a mutation.
            pass

    def get_recent_activity(self, limit=12):
        rows = self.conn.execute(
            "SELECT ts, kind, target, detail FROM activity_log ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

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

    def add_event(self, title, event_date, start_time="09:00", end_time="10:00", color="#0073ea", all_day=0, description="", gcal_id=""):
        cur = self.conn.execute(
            "INSERT INTO events(title, event_date, start_time, end_time, color, all_day, description, gcal_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, event_date, start_time, end_time, color, all_day, description, gcal_id)
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
        # Track deleted event IDs for sync
        self._deleted_event_ids = getattr(self, '_deleted_event_ids', [])
        self._deleted_event_ids.append(str(eid))

    def get_deleted_event_ids(self):
        return getattr(self, '_deleted_event_ids', [])

    def clear_deleted_event_ids(self):
        self._deleted_event_ids = []

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

    def add_note(self, title="Untitled", content="", color="#0073ea", folder="", tags="", font="Sans-serif"):
        max_order = self.conn.execute("SELECT COALESCE(MAX(sort_order),0) FROM notes").fetchone()[0]
        cur = self.conn.execute(
            "INSERT INTO notes(title, content, color, folder, sort_order, tags, font) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, content, color, folder, max_order + 1, tags, font)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_note(self, nid, **kwargs):
        # Store as UTC with space separator to match SQLite's datetime('now') default
        # AND the format used by SyncManager._last_sync_time, so the
        # "modified since last sync" check stays apples-to-apples.
        kwargs["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [nid]
        self.conn.execute(f"UPDATE notes SET {sets} WHERE id=?", vals)
        self.conn.commit()

    def delete_note(self, nid):
        self.conn.execute("DELETE FROM notes WHERE id=?", (nid,))
        self.conn.commit()

    def get_all_tags(self):
        """Return all unique tags across all notes."""
        rows = self.conn.execute("SELECT tags FROM notes WHERE tags != ''").fetchall()
        tag_set = set()
        for r in rows:
            for tag in r["tags"].split(","):
                tag = tag.strip()
                if tag:
                    tag_set.add(tag)
        return sorted(tag_set)

    def get_notes_by_tag(self, tag):
        """Return notes that contain the given tag."""
        all_notes = self.get_notes()
        result = []
        for n in all_notes:
            tags = [t.strip() for t in n["tags"].split(",") if t.strip()] if n["tags"] else []
            if tag in tags:
                result.append(n)
        return result

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
                # Persisted last-sync timestamp — lets us skip un-modified notes
                # across app restarts (big speedup: avoids re-pushing 900KB every launch)
                self._last_sync_time = cfg.get("last_sync_time", "")
                if self.sync_url:
                    self.status = self.STATUS_IDLE
            except Exception:
                pass

    def save_config(self):
        cfg = {
            "sync_url": self.sync_url,
            "api_key": self.api_key,
            "last_sync_time": getattr(self, "_last_sync_time", ""),
        }
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
            resp = _requests.post(url, json=data_dict, timeout=300)
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
            url = f"{self.sync_url}?action=getTasksLight{key_param}"
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
                local_ev_ids = {str(ev["id"]): dict(ev) for ev in local_events}
                local_ev_titles = {ev["title"]: dict(ev) for ev in local_events}
                # Also index by gcal_id so we don't duplicate Google Calendar events
                local_gcal_ids = {}
                for ev in local_events:
                    gid = ev["gcal_id"] if "gcal_id" in ev.keys() else ""
                    if gid:
                        local_gcal_ids[gid] = dict(ev)

                for rev in remote_events:
                    t = rev.get("title", "")
                    rid = rev.get("id", "")
                    gcal_id = rev.get("gcalId", "")
                    # Parse time - handle ISO format from older Google Sheets data
                    def _parse_sync_time(val):
                        if not val: return ""
                        val = str(val)
                        import re
                        if re.match(r'^\d{2}:\d{2}$', val): return val
                        if "T" in val:
                            try:
                                from datetime import datetime as _dt
                                d = _dt.fromisoformat(val.replace("Z", "+00:00"))
                                local = d.astimezone()
                                return f"{local.hour:02d}:{local.minute:02d}"
                            except:
                                try: return val.split("T")[1][:5]
                                except: pass
                        return val
                    st = _parse_sync_time(rev.get("startTime", ""))
                    et = _parse_sync_time(rev.get("endTime", ""))

                    # Check if already exists locally (by id, gcal_id, or title)
                    existing = local_ev_ids.get(rid) or local_gcal_ids.get(gcal_id) or local_ev_titles.get(t)
                    r_desc = rev.get("description", "")
                    if existing:
                        # Preserve existing description if remote sent nothing
                        # (local is authoritative — never blank out a description that only lives locally)
                        existing_desc = existing.get("description", "") if hasattr(existing, "get") else ""
                        final_desc = r_desc if r_desc else existing_desc
                        db.update_event(existing["id"],
                            event_date=rev.get("date", ""),
                            start_time=st or existing.get("start_time", ""),
                            end_time=et or existing.get("end_time", ""),
                            color=rev.get("color", "#0073ea"),
                            all_day=1 if rev.get("allDay") else 0,
                            description=final_desc,
                            gcal_id=gcal_id)
                    else:
                        db.add_event(t, rev.get("date", ""),
                            start_time=st or "09:00",
                            end_time=et or "10:00",
                            color=rev.get("color", "#0073ea"),
                            all_day=1 if rev.get("allDay") else 0,
                            description=r_desc,
                            gcal_id=gcal_id)
                # NOTE: Never delete local events during pull.
                # Local is authoritative — pull only adds/updates.

            # ── Sync Notes from remote (add only, never delete local) ──
            # Light mode: notes have metadata only, fetch content on demand for new notes
            remote_notes = remote.get("notes", [])
            if remote_notes:
                local_notes = db.get_notes()
                local_note_titles = {n["title"]: dict(n) for n in local_notes}
                for rn in remote_notes:
                    t = rn.get("title", "")
                    if not t or t in local_note_titles:
                        continue  # skip existing — local is authoritative
                    # New note — fetch content from cloud
                    content = rn.get("content", "")
                    if not content and rn.get("id"):
                        try:
                            note_url = f"{self.sync_url}?action=getNoteContent&noteId={rn['id']}{key_param}"
                            note_data = self._http_get(note_url)
                            content = note_data.get("content", "")
                        except:
                            content = ""
                    folder = rn.get("folder", "")
                    tags = rn.get("tags", "")
                    font = rn.get("font", "Sans-serif")
                    nid = db.add_note(t, content, folder=folder, tags=tags, font=font)
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
                keys = ev.keys() if hasattr(ev, 'keys') else []
                push_data["events"].append({
                    "id": str(ev["id"]), "title": ev["title"],
                    "date": ev["event_date"], "startTime": ev["start_time"],
                    "endTime": ev["end_time"], "color": ev["color"],
                    "allDay": bool(ev["all_day"]),
                    "gcalId": ev["gcal_id"] if "gcal_id" in keys else "",
                    "description": ev["description"] if "description" in keys else "",
                })
            push_data["deletedEventIds"] = db.get_deleted_event_ids()

            # Notes — only send content for notes modified since last sync
            push_data["notes"] = []
            last_sync = getattr(self, '_last_sync_time', '')
            # Parse last_sync (stored as UTC "YYYY-MM-DD HH:MM:SS") into a datetime
            last_sync_dt = None
            if last_sync:
                try:
                    last_sync_dt = datetime.strptime(last_sync, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    last_sync_dt = None

            def _parse_updated_at(ts):
                """Parse any of these formats, treat the result as UTC:
                   "2026-04-17 12:03:14"              (new format & SQL default)
                   "2026-04-17T20:03:14.123456"       (legacy local-time ISO — mis-timed
                                                      but lexicographically sortable)
                   Returns a naive datetime, or None.
                """
                if not ts:
                    return None
                ts = str(ts).replace('T', ' ').strip()
                # If looks like legacy local-time (with microseconds), shift to UTC
                has_micros = '.' in ts
                for fmt in ("%Y-%m-%d %H:%M:%S.%f",
                            "%Y-%m-%d %H:%M:%S",
                            "%Y-%m-%d %H:%M"):
                    try:
                        dt = datetime.strptime(ts, fmt)
                        # Legacy rows used datetime.now() (local). Convert to UTC by
                        # subtracting the current local offset so the comparison with
                        # _last_sync_time (UTC) is meaningful. For new UTC rows
                        # (no microseconds, matches SQL default) don't shift.
                        if has_micros:
                            try:
                                local_offset = datetime.now().astimezone().utcoffset()
                                if local_offset:
                                    dt = dt - local_offset
                            except Exception:
                                pass
                        return dt
                    except ValueError:
                        continue
                return None

            for n in db.get_notes():
                nd = dict(n)
                note_updated = nd.get("updated_at", "")
                if last_sync_dt is None:
                    modified = True  # first-ever sync
                else:
                    nu_dt = _parse_updated_at(note_updated)
                    modified = (nu_dt is None) or (nu_dt > last_sync_dt)
                entry = {
                    "id": str(nd["id"]), "title": nd["title"],
                    "pinned": bool(nd["pinned"]),
                    "folder": nd.get("folder", ""),
                    "sortOrder": nd.get("sort_order", 0),
                    "tags": nd.get("tags", ""),
                    "font": nd.get("font", "Sans-serif"),
                }
                if modified:
                    entry["content"] = nd.get("content", "")
                # else: no content key → server skips Drive write
                push_data["notes"].append(entry)

            result = self._http_post(self.sync_url, push_data)
            if result.get("code") == 401:
                raise Exception("Unauthorized — check your API Key")
            if result.get("error"):
                raise Exception(f"Sync error: {result['error']}")

            # Push succeeded — record sync time and clear deletion records
            from datetime import datetime
            self._last_sync_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            # Persist so a restart doesn't force a full re-push of all notes
            self.save_config()
            db.clear_deleted_event_ids()
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

        # Auto-set end time = start + 1 hour when start changes
        self._auto_end = True
        self.start_time.timeChanged.connect(self._on_start_time_changed)

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

        btn_row = QHBoxLayout()
        if event_id:
            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet("color: #e2445c; padding: 6px 16px;")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(self._delete)
            btn_row.addWidget(del_btn)
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 6px 16px;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("padding: 6px 20px; background: #0073ea; color: white; border: none; border-radius: 6px; font-weight: bold;")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        save_btn.setDefault(True)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)
        self._toggle_time()

    def _set_color(self, color):
        self._event_color = color

    def _on_start_time_changed(self, new_time):
        if self._auto_end:
            self.end_time.setTime(new_time.addSecs(3600))

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
        for i, day_name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            lbl = QLabel(day_name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Inter", 10, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {t['text_dim']}; padding: 4px;")
            grid.addWidget(lbl, 0, i)

        # Calendar days
        first_day = date(d.year, d.month, 1)
        start_weekday = (first_day.weekday() + 1) % 7  # 0=Sun
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
                _glyph, _kind = classify_event_glyph(item.get("title", ""))
                pill = QLabel(f"{_glyph} {item['title'][:14]}")
                pill.setStyleSheet(f"""
                    background-color: {item['color']};
                    color: white; border-radius: 3px;
                    padding: 1px 4px; font-size: 9px;
                    font-weight: 600; border: none;
                """)
                pill.setCursor(Qt.CursorShape.PointingHandCursor)
                eid = item["id"]
                pill.mousePressEvent = lambda e, _eid=eid: self._edit_event(_eid)
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
            more.setCursor(Qt.CursorShape.PointingHandCursor)
            _d_str = d_str
            more.mousePressEvent = lambda e, ds=_d_str: self._go_to_day(ds)
            layout.addWidget(more)

        layout.addStretch()
        return cell

    def _render_week(self):
        t = self.theme
        d = self.current_date
        # Find Sunday of current week (week starts on Sunday)
        sunday_start = d - timedelta(days=(d.weekday() + 1) % 7)
        saturday_end = sunday_start + timedelta(days=6)
        self.date_label.setText(f"{sunday_start.strftime('%b %d')} - {saturday_end.strftime('%b %d, %Y')}")

        events = self.db.get_events_range(sunday_start.isoformat(), saturday_end.isoformat())
        all_tasks = self.db.get_tasks()

        grid = QGridLayout()
        grid.setSpacing(2)

        # Time column + 7 day columns
        hours = list(range(7, 22))
        for col_idx in range(7):
            day = sunday_start + timedelta(days=col_idx)
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
                day = sunday_start + timedelta(days=col_idx)
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
                            _ev_title = ev["title"] if "title" in ev.keys() else ""
                            _g, _k = classify_event_glyph(_ev_title)
                            pill = QLabel(f"{_g} {_ev_title[:11]}")
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

            _g, _k = classify_event_glyph(ev.get("title", ""))
            title_lbl = QLabel(f"{_g}  {ev['title']}")
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

    def _go_to_day(self, date_str):
        """Navigate to day view for a specific date."""
        from datetime import date as dt_date
        parts = date_str.split("-")
        if len(parts) == 3:
            self.current_date = dt_date(int(parts[0]), int(parts[1]), int(parts[2]))
        self._set_mode("day")

    def _edit_event(self, eid):
        dlg = EventEditDialog(self.db, event_id=eid, parent=self)
        if dlg.exec():
            self._refresh()


# ─── Rich Text Note Editor ───────────────────────────────────
class SlashCommandMenu(QListWidget):
    """Popup menu for slash commands, shown when user types '/' at line start."""
    command_selected = pyqtSignal(str)

    COMMANDS = [
        ("Text", "Plain text paragraph", "text"),
        ("Heading 1", "Large heading", "h1"),
        ("Heading 2", "Medium heading", "h2"),
        ("Heading 3", "Small heading", "h3"),
        ("Bullet List", "Unordered list", "bullet"),
        ("Numbered List", "Ordered list", "numbered"),
        ("To-do List", "Checklist with checkboxes", "checklist"),
        ("Quote", "Blockquote", "quote"),
        ("Divider", "Horizontal rule", "divider"),
        ("Code Block", "Monospace code", "code"),
        ("Callout", "Highlighted callout box", "callout"),
        ("Toggle", "Collapsible section", "toggle"),
        ("Table of Contents", "Auto-generated TOC", "toc"),
        ("Math Equation", "LaTeX formula", "math"),
        ("Bookmark", "Embed a link", "bookmark"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setFixedWidth(240)
        self.setMaximumHeight(300)
        self.setStyleSheet("""
            QListWidget {
                background: #ffffff; border: 1px solid #E3E2E0;
                border-radius: 8px; padding: 4px; font-size: 13px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 10px; border-radius: 4px; color: #37352F;
            }
            QListWidget::item:hover { background: #F7F6F3; }
            QListWidget::item:selected { background: #E8F0FE; color: #37352F; }
        """)
        self._all_commands = list(self.COMMANDS)
        self._populate("")
        self.itemClicked.connect(self._on_click)

    def _populate(self, filter_text):
        self.clear()
        ft = filter_text.lower()
        for label, desc, cmd_id in self._all_commands:
            if ft and ft not in label.lower() and ft not in desc.lower():
                continue
            item = QListWidgetItem(f"{label}\n{desc}")
            item.setData(Qt.ItemDataRole.UserRole, cmd_id)
            self.addItem(item)
        if self.count() > 0:
            self.setCurrentRow(0)
        visible_items = min(self.count(), 8)
        self.setFixedHeight(max(visible_items * 42 + 10, 52))

    def filter(self, text):
        self._populate(text)
        return self.count() > 0

    def _on_click(self, item):
        cmd = item.data(Qt.ItemDataRole.UserRole)
        if cmd:
            self.command_selected.emit(cmd)
            self.hide()

    def select_current(self):
        item = self.currentItem()
        if item:
            self._on_click(item)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.select_current()
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


class ImageDropTextEdit(QTextEdit):
    """QTextEdit subclass that handles image drag-drop and clipboard paste.

    Images (from files or clipboard) are converted to base64 data URIs
    and inserted inline so they are stored inside the note content.
    """

    MAX_IMAGE_WIDTH = 600  # pixels – resize if wider to keep notes manageable

    def canInsertFromMimeData(self, source):
        if source.hasImage() or source.hasUrls():
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        # 1) Clipboard image (e.g. screenshot Cmd+V)
        if source.hasImage():
            img = source.imageData()
            if img and not img.isNull():
                self._embed_qimage(img)
                return

        # 2) Dropped / pasted file URLs
        if source.hasUrls():
            handled = False
            for url in source.urls():
                path = url.toLocalFile()
                if path and any(path.lower().endswith(ext) for ext in
                                ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg')):
                    self._embed_image_file(path)
                    handled = True
            if handled:
                return

        # Fallback – let Qt handle text/HTML
        super().insertFromMimeData(source)

    def _embed_qimage(self, qimage):
        """Convert a QImage to base64 PNG and insert into the document."""
        from PyQt6.QtCore import QBuffer, QIODevice
        qimage = self._constrain_width(qimage)
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        qimage.save(buf, "PNG")
        b64 = bytes(buf.data().toBase64()).decode('ascii')
        self._insert_html_image(f"data:image/png;base64,{b64}")

    def _embed_image_file(self, filepath):
        """Read an image file, convert to base64 data URI, and insert."""
        import base64, mimetypes
        mime, _ = mimetypes.guess_type(filepath)
        if not mime:
            mime = "image/png"
        try:
            with open(filepath, 'rb') as f:
                raw = f.read()
            # Optionally constrain width
            img = QPixmap()
            img.loadFromData(raw)
            if not img.isNull() and img.width() > self.MAX_IMAGE_WIDTH:
                img = img.scaledToWidth(self.MAX_IMAGE_WIDTH, Qt.TransformationMode.SmoothTransformation)
                from PyQt6.QtCore import QBuffer, QIODevice
                buf = QBuffer()
                buf.open(QIODevice.OpenModeFlag.WriteOnly)
                img.save(buf, "PNG")
                raw = bytes(buf.data())
                mime = "image/png"
            b64 = base64.b64encode(raw).decode('ascii')
            self._insert_html_image(f"data:{mime};base64,{b64}")
        except Exception as e:
            cursor = self.textCursor()
            cursor.insertText(f"[Image error: {e}]")

    def _constrain_width(self, qimage):
        """Resize QImage if wider than MAX_IMAGE_WIDTH."""
        if qimage.width() > self.MAX_IMAGE_WIDTH:
            return qimage.scaledToWidth(self.MAX_IMAGE_WIDTH, Qt.TransformationMode.SmoothTransformation)
        return qimage

    def _insert_html_image(self, data_uri):
        """Insert an <img> tag with the given data URI at the cursor position."""
        cursor = self.textCursor()
        cursor.insertHtml(
            f'<br><img src="{data_uri}" style="max-width:100%;"><br>'
        )


class RichTextEditor(QWidget):
    """Notion-style rich text editor with toolbar, slash commands, and formatting.

    Provides bold/italic/underline/strikethrough, headings, lists, quotes,
    code blocks, callouts, dividers, highlight, and text color.
    Emits ``content_changed`` whenever the document is modified.
    """
    content_changed = pyqtSignal()

    TEXT_COLORS = {
        "Default": "",
        "Red": "#EB5757",
        "Blue": "#2F80ED",
        "Green": "#27AE60",
        "Orange": "#F2994A",
        "Purple": "#9B51E0",
    }

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._slash_active = False
        self._slash_filter = ""
        self._build()

    def set_theme(self, theme):
        """Apply the given theme dict to the editor and toolbar."""
        self.theme = theme
        t = theme
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t['card_bg']};
                color: {t['text']};
                border: none;
                border-radius: 8px;
                padding: 20px 28px;
                font-size: 14px;
                line-height: 1.7;
                selection-background-color: rgba(45,125,230,0.25);
            }}
        """)
        self.editor.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        self._update_toolbar_theme()

    def _update_toolbar_theme(self):
        t = self.theme
        is_dark = t.get('bg', '#fff')[1:3] < '80' if len(t.get('bg', '#fff')) > 3 else False
        hover_bg = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.06)"
        checked_bg = "rgba(0,115,234,0.18)"
        text_color = t.get('text', '#37352F')
        sep_color = t.get('border', '#E3E2E0')
        self._btn_style = f"""
            QPushButton {{
                border: none; border-radius: 4px;
                padding: 3px 7px; font-size: 12px;
                background: transparent; color: {text_color};
            }}
            QPushButton:hover {{ background-color: {hover_bg}; }}
            QPushButton:checked {{ background-color: {checked_bg}; color: #0073ea; }}
        """
        for btn in self._toolbar_buttons:
            btn.setStyleSheet(self._btn_style)
        # Restore the color button's special red "A" style
        if hasattr(self, 'color_btn'):
            hover_bg_css = hover_bg
            self.color_btn.setStyleSheet(f"""
                QPushButton {{
                    border: none; border-radius: 4px; padding: 3px 7px;
                    font-size: 12px; background: transparent; color: #EB5757;
                }}
                QPushButton:hover {{ background-color: {hover_bg_css}; }}
                QPushButton::menu-indicator {{ image: none; width: 0px; }}
            """)
        for sep in self._toolbar_seps:
            sep.setStyleSheet(f"background: {sep_color}; border: none;")
        toolbar_bg = '#252525' if is_dark else t.get('card_bg', '#fff')
        border = '#373737' if is_dark else t.get('border', '#E3E2E0')
        self.toolbar_frame.setStyleSheet(f"""
            QFrame#notionToolbar {{
                background: {toolbar_bg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 2px 4px;
            }}
        """)
        # Update the separator between toolbar and editor
        if hasattr(self, '_title_separator'):
            self._title_separator.setStyleSheet(f"background: {sep_color}; border: none;")

    def _make_sep(self):
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        sep.setStyleSheet("background: #E3E2E0; border: none;")
        self._toolbar_seps.append(sep)
        return sep

    def _make_btn(self, text, tooltip, checkable=False, width=28, bold=False, italic=False, underline=False, strikethrough=False):
        """Create a consistent 28x28 toolbar button with tooltip and optional formatting."""
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(width, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        f = QFont("Inter", 11)
        if bold:
            f.setBold(True)
        if italic:
            f.setItalic(True)
        if underline:
            f.setUnderline(True)
        if strikethrough:
            f.setStrikeOut(True)
        btn.setFont(f)
        btn.setCheckable(checkable)
        btn.setStyleSheet(self._btn_style)
        self._toolbar_buttons.append(btn)
        return btn

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._toolbar_buttons = []
        self._toolbar_seps = []
        self._btn_style = """
            QPushButton {
                border: none; border-radius: 4px;
                padding: 3px 7px; font-size: 12px;
                background: transparent; color: #37352F;
            }
            QPushButton:hover { background-color: rgba(0,0,0,0.06); }
            QPushButton:checked { background-color: rgba(0,115,234,0.18); color: #0073ea; }
        """

        # Toolbar frame (Notion-style)
        self.toolbar_frame = QFrame()
        self.toolbar_frame.setObjectName("notionToolbar")
        self.toolbar_frame.setStyleSheet("""
            QFrame#notionToolbar {
                background: #ffffff;
                border: 1px solid #E3E2E0;
                border-radius: 8px;
                padding: 2px 4px;
            }
        """)
        tb = QHBoxLayout(self.toolbar_frame)
        tb.setContentsMargins(6, 3, 6, 3)
        tb.setSpacing(2)

        # ── Text formatting: Bold | Italic | Underline | Strikethrough ──
        self.bold_btn = self._make_btn("B", "Bold (Ctrl+B)", checkable=True, bold=True)
        self.bold_btn.clicked.connect(self._toggle_bold)
        tb.addWidget(self.bold_btn)

        self.italic_btn = self._make_btn("I", "Italic (Ctrl+I)", checkable=True, italic=True)
        self.italic_btn.clicked.connect(self._toggle_italic)
        tb.addWidget(self.italic_btn)

        self.underline_btn = self._make_btn("U", "Underline (Ctrl+U)", checkable=True, underline=True)
        self.underline_btn.clicked.connect(self._toggle_underline)
        tb.addWidget(self.underline_btn)

        self.strike_btn = self._make_btn("S", "Strikethrough (Ctrl+Shift+X)", checkable=True, strikethrough=True)
        self.strike_btn.clicked.connect(self._toggle_strikethrough)
        tb.addWidget(self.strike_btn)

        tb.addWidget(self._make_sep())

        # ── Headings: H1 | H2 | H3 ──
        self.h1_btn = self._make_btn("H1", "Heading 1 (Ctrl+1)", width=30)
        self.h1_btn.clicked.connect(lambda: self._set_heading(1))
        tb.addWidget(self.h1_btn)

        self.h2_btn = self._make_btn("H2", "Heading 2 (Ctrl+2)", width=30)
        self.h2_btn.clicked.connect(lambda: self._set_heading(2))
        tb.addWidget(self.h2_btn)

        self.h3_btn = self._make_btn("H3", "Heading 3 (Ctrl+3)", width=30)
        self.h3_btn.clicked.connect(lambda: self._set_heading(3))
        tb.addWidget(self.h3_btn)

        tb.addWidget(self._make_sep())

        # ── Block types: Bullet | Numbered | Checklist | Quote | Code | Callout ──
        self.bullet_btn = self._make_btn("\u2022", "Bullet List (Ctrl+Shift+8)")
        self.bullet_btn.clicked.connect(self._toggle_bullet)
        tb.addWidget(self.bullet_btn)

        self.num_btn = self._make_btn("1.", "Numbered List (Ctrl+Shift+7)")
        self.num_btn.clicked.connect(self._toggle_numbered)
        tb.addWidget(self.num_btn)

        self.check_btn = self._make_btn("\u2611", "Checklist (Ctrl+Shift+9)")
        self.check_btn.clicked.connect(self._insert_checklist)
        tb.addWidget(self.check_btn)

        self.quote_btn = self._make_btn("\u275D", "Quote Block")
        self.quote_btn.clicked.connect(self._insert_quote)
        tb.addWidget(self.quote_btn)

        self.code_btn = self._make_btn("</>", "Code Block", width=32)
        self.code_btn.clicked.connect(self._insert_code_block)
        tb.addWidget(self.code_btn)

        self.table_btn = self._make_btn("\u229e", "Insert Table")
        self.table_btn.clicked.connect(self._insert_table)
        tb.addWidget(self.table_btn)

        self.callout_btn = self._make_btn("\u2139", "Callout")
        self.callout_btn.clicked.connect(self._insert_callout)
        tb.addWidget(self.callout_btn)

        tb.addWidget(self._make_sep())

        # ── Insert: Divider | Highlight | Text Color ──
        self.divider_btn = self._make_btn("\u2014", "Insert Divider")
        self.divider_btn.clicked.connect(self._insert_divider)
        tb.addWidget(self.divider_btn)

        self.highlight_btn = self._make_btn("\u2588", "Highlight (Ctrl+Shift+H)")
        self.highlight_btn.clicked.connect(self._toggle_highlight)
        tb.addWidget(self.highlight_btn)

        # ── Text color dropdown ──
        self.color_btn = QPushButton("A")
        self.color_btn.setToolTip("Text Color")
        self.color_btn.setFixedSize(28, 28)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.color_btn.setStyleSheet("""
            QPushButton {
                border: none; border-radius: 4px; padding: 3px 7px;
                font-size: 12px; background: transparent; color: #EB5757;
            }
            QPushButton:hover { background-color: rgba(0,0,0,0.06); }
            QPushButton::menu-indicator { image: none; width: 0px; }
        """)
        color_menu = QMenu(self)
        color_menu.setStyleSheet("""
            QMenu { background: #fff; border: 1px solid #E3E2E0; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 5px 16px; border-radius: 4px; font-size: 12px; color: #37352F; }
            QMenu::item:selected { background: #F7F6F3; }
        """)
        for name, color in self.TEXT_COLORS.items():
            action = color_menu.addAction(f"\u25CF {name}" if color else f"  {name}")
            if color:
                action.setData(color)
            else:
                action.setData("")
        color_menu.triggered.connect(self._apply_text_color)
        self.color_btn.setMenu(color_menu)
        self._toolbar_buttons.append(self.color_btn)
        tb.addWidget(self.color_btn)

        tb.addStretch()

        # Slash command hint
        slash_hint = QLabel("  Type / for commands")
        slash_hint.setStyleSheet("color: #B4B4B0; font-size: 11px; font-style: italic; border: none; background: transparent;")
        tb.addWidget(slash_hint)

        layout.addWidget(self.toolbar_frame)

        # ── Separator between toolbar and content ──
        self._title_separator = QFrame()
        self._title_separator.setFixedHeight(1)
        self._title_separator.setStyleSheet(f"background: {self.theme.get('border', '#E3E2E0')}; border: none;")
        layout.addWidget(self._title_separator)

        # ── Editor ──
        self.editor = ImageDropTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        t = self.theme
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t['card_bg']};
                color: {t['text']};
                border: none;
                border-radius: 8px;
                padding: 20px 28px;
                font-size: 14px;
                selection-background-color: rgba(45,125,230,0.25);
            }}
        """)
        self.editor.textChanged.connect(self.content_changed.emit)
        self.editor.cursorPositionChanged.connect(self._update_toolbar_state)
        self.editor.installEventFilter(self)
        layout.addWidget(self.editor)

        # Slash command popup
        self._slash_menu = SlashCommandMenu(self)
        self._slash_menu.command_selected.connect(self._execute_slash_command)
        self._slash_menu.hide()

    # ── Slash command support ──────────────────────────────────
    def eventFilter(self, obj, event):
        """Intercept key events in the editor to manage slash command popup."""
        if obj == self.editor and event.type() == event.Type.KeyPress:
            key = event.key()
            if self._slash_active:
                if key == Qt.Key.Key_Escape:
                    self._slash_active = False
                    self._slash_menu.hide()
                    return True
                elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._slash_menu.select_current()
                    self._slash_active = False
                    return True
                elif key == Qt.Key.Key_Up:
                    row = self._slash_menu.currentRow()
                    if row > 0:
                        self._slash_menu.setCurrentRow(row - 1)
                    return True
                elif key == Qt.Key.Key_Down:
                    row = self._slash_menu.currentRow()
                    if row < self._slash_menu.count() - 1:
                        self._slash_menu.setCurrentRow(row + 1)
                    return True
                elif key == Qt.Key.Key_Backspace:
                    if self._slash_filter:
                        self._slash_filter = self._slash_filter[:-1]
                        if not self._slash_menu.filter(self._slash_filter):
                            self._slash_active = False
                            self._slash_menu.hide()
                    else:
                        self._slash_active = False
                        self._slash_menu.hide()
                    return False  # let backspace propagate
                elif event.text() and event.text().isprintable():
                    self._slash_filter += event.text()
                    if not self._slash_menu.filter(self._slash_filter):
                        self._slash_active = False
                        self._slash_menu.hide()
                    return False  # let char propagate
                else:
                    self._slash_active = False
                    self._slash_menu.hide()
            else:
                if event.text() == "/":
                    cursor = self.editor.textCursor()
                    block_text = cursor.block().text()
                    pos_in_block = cursor.positionInBlock()
                    if pos_in_block == 0 or block_text[:pos_in_block].strip() == "":
                        self._slash_active = True
                        self._slash_filter = ""
                        self._slash_menu.filter("")
                        # Position the popup near the cursor
                        rect = self.editor.cursorRect()
                        global_pos = self.editor.mapToGlobal(rect.bottomLeft())
                        self._slash_menu.move(global_pos.x(), global_pos.y() + 4)
                        self._slash_menu.show()
        return super().eventFilter(obj, event)

    def _execute_slash_command(self, cmd):
        """Execute the chosen slash command by removing the '/' prefix and applying the block type."""
        cursor = self.editor.textCursor()
        block_start = cursor.block().position()
        block_text = cursor.block().text()
        # Find and remove the slash + filter text
        slash_pos = block_text.rfind("/")
        if slash_pos >= 0:
            cursor.setPosition(block_start + slash_pos)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            self.editor.setTextCursor(cursor)

        if cmd == "text":
            pass  # just clear the slash
        elif cmd == "h1":
            self._set_heading(1)
        elif cmd == "h2":
            self._set_heading(2)
        elif cmd == "h3":
            self._set_heading(3)
        elif cmd == "bullet":
            self._toggle_bullet()
        elif cmd == "numbered":
            self._toggle_numbered()
        elif cmd == "checklist":
            self._insert_checklist()
        elif cmd == "quote":
            self._insert_quote()
        elif cmd == "divider":
            self._insert_divider()
        elif cmd == "code":
            self._insert_code_block()
        elif cmd == "callout":
            self._insert_callout()
        elif cmd == "toggle":
            self._insert_toggle()
        elif cmd == "toc":
            self._insert_toc()
        elif cmd == "math":
            self._insert_math()
        elif cmd == "bookmark":
            self._insert_bookmark()

        self._slash_active = False
        self._slash_menu.hide()

    # ── Toolbar state sync ──────────────────────────────────────
    def _update_toolbar_state(self):
        """Sync toolbar button checked states with the current cursor format."""
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        self.bold_btn.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.italic_btn.setChecked(fmt.fontItalic())
        self.underline_btn.setChecked(fmt.fontUnderline())
        self.strike_btn.setChecked(fmt.fontStrikeOut())

    # ── Text formatting actions ──────────────────────────────────
    def _toggle_bold(self):
        """Toggle bold on the current selection or word."""
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

    def _toggle_strikethrough(self):
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(self.strike_btn.isChecked())
        self._merge_format(fmt)

    # ── Block formatting actions ─────────────────────────────────
    def _set_heading(self, idx):
        """Apply heading level (1-3) or reset to normal (0) on the current block."""
        cursor = self.editor.textCursor()
        block_fmt = QTextBlockFormat()
        char_fmt = QTextCharFormat()
        if idx == 0:  # Normal
            char_fmt.setFontPointSize(14)
            char_fmt.setFontWeight(QFont.Weight.Normal)
        elif idx == 1:  # H1
            char_fmt.setFontPointSize(24)
            char_fmt.setFontWeight(QFont.Weight.Bold)
        elif idx == 2:  # H2
            char_fmt.setFontPointSize(20)
            char_fmt.setFontWeight(QFont.Weight.Bold)
        elif idx == 3:  # H3
            char_fmt.setFontPointSize(16)
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

    def _insert_checklist(self):
        cursor = self.editor.textCursor()
        cursor.insertText("\u2610 ")
        self.editor.setTextCursor(cursor)

    def _insert_quote(self):
        cursor = self.editor.textCursor()
        block_fmt = QTextBlockFormat()
        block_fmt.setLeftMargin(20)
        char_fmt = QTextCharFormat()
        char_fmt.setForeground(QColor("#787774"))
        char_fmt.setFontItalic(True)
        char_fmt.setFontPointSize(14)
        # Insert a block with left border feel via margin + styling
        cursor.insertBlock(block_fmt, char_fmt)
        cursor.insertText("\u2503 ")
        self.editor.setTextCursor(cursor)

    def _insert_divider(self):
        cursor = self.editor.textCursor()
        cursor.insertBlock()
        cursor.insertHtml('<hr style="border: none; border-top: 1px solid #E3E2E0; margin: 12px 0;">')
        cursor.insertBlock()
        self.editor.setTextCursor(cursor)

    def _insert_code_block(self):
        """Insert a styled code block with language label."""
        from PyQt6.QtWidgets import QInputDialog
        lang, ok = QInputDialog.getItem(self, "Code Block", "Language:",
            ["python", "javascript", "html", "css", "sql", "bash", "json", "text"], 0, True)
        if not ok:
            return
        cursor = self.editor.textCursor()
        # Insert a formatted block
        block_fmt = QTextBlockFormat()
        block_fmt.setBackground(QColor("#1E1E1E"))
        block_fmt.setTopMargin(12)
        block_fmt.setBottomMargin(12)
        block_fmt.setLeftMargin(16)
        block_fmt.setRightMargin(16)

        char_fmt = QTextCharFormat()
        char_fmt.setFontFamily("SF Mono, Menlo, Consolas, monospace")
        char_fmt.setForeground(QColor("#E3E2E0"))
        char_fmt.setFontPointSize(12)

        # Language label in dimmer color
        label_fmt = QTextCharFormat(char_fmt)
        label_fmt.setForeground(QColor("#6A9955"))
        label_fmt.setFontPointSize(10)

        cursor.insertBlock(block_fmt, char_fmt)
        cursor.insertText(f"// {lang}\n", label_fmt)
        cursor.insertText("code here", char_fmt)
        self.editor.setTextCursor(cursor)

    def _insert_table(self):
        """Insert an editable table into the note."""
        from PyQt6.QtWidgets import QInputDialog
        rows, ok1 = QInputDialog.getInt(self, "Table", "Rows:", 3, 1, 20)
        if not ok1:
            return
        cols, ok2 = QInputDialog.getInt(self, "Table", "Columns:", 3, 1, 10)
        if not ok2:
            return

        cursor = self.editor.textCursor()
        table = cursor.insertTable(rows, cols)

        # Style the table
        fmt = table.format()
        fmt.setBorder(1)
        fmt.setBorderBrush(QColor("#E3E2E0"))
        fmt.setCellPadding(8)
        fmt.setCellSpacing(0)
        fmt.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_Solid)
        table.setFormat(fmt)

        # Style header row
        for col in range(cols):
            cell = table.cellAt(0, col)
            cf = cell.format()
            cf.setBackground(QColor("#F7F6F3"))
            cell.setFormat(cf)
            cur = cell.firstCursorPosition()
            cur.insertText(f"Header {col + 1}")

    def _insert_callout(self):
        cursor = self.editor.textCursor()
        block_fmt = QTextBlockFormat()
        block_fmt.setLeftMargin(16)
        block_fmt.setRightMargin(16)
        block_fmt.setTopMargin(8)
        block_fmt.setBottomMargin(8)
        char_fmt = QTextCharFormat()
        char_fmt.setBackground(QColor("#FFF8E1"))
        char_fmt.setFontPointSize(13)
        cursor.insertBlock(block_fmt, char_fmt)
        cursor.insertText("\U0001F4A1 ")
        self.editor.setTextCursor(cursor)

    def _insert_toggle(self):
        """Insert a toggle (collapsible) block using HTML in the rich text editor."""
        cursor = self.editor.textCursor()
        cursor.insertHtml(
            '<div style="margin:8px 0;padding:6px 10px;background:#F7F6F3;border-radius:4px;">'
            '<b>▶ Toggle heading</b><br>'
            '<span style="color:#6B6B6B;margin-left:20px;">Toggle content — type here</span>'
            '</div><br>'
        )
        self.editor.setTextCursor(cursor)

    def _insert_toc(self):
        """Insert a Table of Contents block based on current headings in the document."""
        cursor = self.editor.textCursor()
        doc = self.editor.document()
        headings = []
        block = doc.begin()
        while block.isValid():
            fmt = block.blockFormat()
            text = block.text().strip()
            if text:
                # Check heading level by font size
                cf = block.charFormat()
                pt = cf.fontPointSize()
                weight = cf.fontWeight()
                if pt >= 20 or (weight and weight >= 700 and pt >= 16):
                    headings.append(('h1', text))
                elif pt >= 16 or (weight and weight >= 600 and pt >= 14):
                    headings.append(('h2', text))
                elif pt >= 14 and weight and weight >= 600:
                    headings.append(('h3', text))
            block = block.next()

        toc_html = '<div style="background:#F7F6F3;border-radius:6px;padding:12px 16px;margin:8px 0;">'
        toc_html += '<div style="font-size:11px;font-weight:600;color:#91918E;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">Table of Contents</div>'
        if headings:
            for level, text in headings:
                indent = '0' if level == 'h1' else ('16' if level == 'h2' else '32')
                toc_html += f'<div style="padding:2px 0 2px {indent}px;font-size:13px;color:#2383E2;">{text}</div>'
        else:
            toc_html += '<div style="font-size:12px;color:#91918E;">No headings found yet.</div>'
        toc_html += '</div><br>'
        cursor.insertHtml(toc_html)
        self.editor.setTextCursor(cursor)

    def _insert_math(self):
        """Insert a math formula block (rendered as styled text)."""
        from PyQt6.QtWidgets import QInputDialog
        formula, ok = QInputDialog.getText(self, "Math Equation", "LaTeX formula:", text="E = mc²")
        if not ok or not formula:
            return
        cursor = self.editor.textCursor()
        cursor.insertHtml(
            f'<div style="background:#F7F6F3;border-radius:6px;padding:12px;margin:8px 0;text-align:center;'
            f'font-family:serif;font-size:18px;font-style:italic;">{formula}</div><br>'
        )
        self.editor.setTextCursor(cursor)

    def _insert_bookmark(self):
        """Insert a bookmark/URL embed block."""
        from PyQt6.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(self, "Bookmark", "Paste URL:")
        if not ok or not url.strip():
            return
        url = url.strip()
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).hostname or url
        except Exception:
            domain = url
        cursor = self.editor.textCursor()
        cursor.insertHtml(
            f'<div style="border:1px solid #E3E2E0;border-radius:6px;padding:10px 14px;margin:8px 0;">'
            f'<div style="font-size:13px;font-weight:500;">🔗 {domain}</div>'
            f'<div style="font-size:11px;color:#91918E;">{url}</div>'
            f'</div><br>'
        )
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

    def _apply_text_color(self, action):
        color = action.data()
        fmt = QTextCharFormat()
        if color:
            fmt.setForeground(QColor(color))
        else:
            fmt.setForeground(QColor(self.theme.get('text', '#37352F')))
        self._merge_format(fmt)

    def _merge_format(self, fmt):
        """Apply a character format to the current selection, or the word under cursor."""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def get_html(self):
        return self.editor.toHtml()

    def set_html(self, html):
        if not html:
            self.editor.setHtml("")
            return
        stripped = html.strip()
        # Qt's toHtml() always starts with <!DOCTYPE or <html — use that to
        # detect "already HTML" vs plain-text / Markdown content.
        is_html = stripped[:30].lower().startswith(("<!doctype", "<html", "<body"))
        if is_html:
            self.editor.setHtml(html)
        else:
            # Plain text — escape HTML entities and convert newlines to <br>
            import html as html_mod
            escaped = html_mod.escape(html)
            escaped = escaped.replace("\n", "<br>")
            self.editor.setHtml(escaped)

    def get_plain_text(self):
        return self.editor.toPlainText()


# ─── Dashboard Page ──────────────────────────────────────────
class DashboardPage(QWidget):
    """Visual overview dashboard with KPI cards, charts, and upcoming tasks."""

    def __init__(self, db, theme, parent=None, skin_name="prism"):
        super().__init__(parent)
        self.db = db
        self.theme = theme
        self.current_skin = skin_name
        self._build()

    def set_theme(self, theme, skin_name=None):
        self.theme = theme
        if skin_name is not None:
            self.current_skin = skin_name
        self.refresh()

    def _build(self):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.container = QWidget()
        self.main_vbox = QVBoxLayout(self.container)
        self.main_vbox.setSpacing(14)
        self.main_vbox.setContentsMargins(24, 20, 24, 20)
        self.scroll.setWidget(self.container)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                # setParent(None) removes the widget from the view synchronously
                # (deleteLater alone is async and leaves ghost widgets on screen
                # until the next event loop iteration).
                w.setParent(None)
                w.deleteLater()
            else:
                sub = item.layout()
                if sub is not None:
                    self._clear_layout(sub)
                    sub.deleteLater()

    def refresh(self):
        self._clear_layout(self.main_vbox)

        t = self.theme
        stats = self.db.get_stats()
        total = stats["total"]
        by_status = stats["by_status"]
        overdue = stats["overdue"]
        progress = stats["progress"]

        # Gather priority data
        prio_rows = self.db.conn.execute(
            "SELECT priority, COUNT(*) as cnt FROM tasks GROUP BY priority"
        ).fetchall()
        by_priority = {p: 0 for p in PRIORITIES}
        for r in prio_rows:
            if r["priority"] in by_priority:
                by_priority[r["priority"]] = r["cnt"]

        # Gather group data
        groups = self.db.get_groups()
        group_data = []
        for g in groups:
            tasks = self.db.get_tasks(g["id"])
            tasks = [dict(tt) for tt in tasks]
            done = sum(1 for tt in tasks if tt["status"] == "Done")
            group_data.append({
                "name": g["name"], "color": g["color"],
                "total": len(tasks), "done": done,
            })

        # Upcoming / overdue tasks
        upcoming_tasks = self.db.conn.execute(
            """SELECT t.name, t.status, t.priority, t.due_date, g.name as group_name, g.color as group_color
               FROM tasks t JOIN groups_ g ON t.group_id = g.id
               WHERE t.due_date IS NOT NULL AND t.due_date != '' AND t.status != 'Done'
               ORDER BY t.due_date ASC LIMIT 10"""
        ).fetchall()

        # Today's agenda — due today or currently working on it.
        today_str = date.today().strftime("%Y-%m-%d")
        agenda_rows = self.db.conn.execute(
            """SELECT t.name, t.status, t.priority, t.due_date, g.name as group_name, g.color as group_color
               FROM tasks t JOIN groups_ g ON t.group_id = g.id
               WHERE t.status != 'Done' AND (t.due_date = ? OR t.status = 'Working on it')
               ORDER BY
                 CASE t.status WHEN 'Working on it' THEN 0 ELSE 1 END,
                 CASE t.priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END,
                 t.name LIMIT 8""",
            (today_str,)
        ).fetchall()
        agenda_tasks = [dict(r) for r in agenda_rows]

        activity = self.db.get_recent_activity(limit=10)

        # ── Atlas masthead ──
        self.main_vbox.addWidget(self._masthead())

        # ── Row 0: KPI Cards (3 + 3) ──
        kpi_data = [
            ("Total Tasks", str(total), t["accent"]),
            ("Done", str(by_status.get("Done", 0)), "#00c875"),
            ("In Progress", str(by_status.get("Working on it", 0)), "#0073ea"),
            ("Stuck", str(by_status.get("Stuck", 0)), "#e2445c"),
            ("Overdue", str(overdue), "#e2445c" if overdue > 0 else "#797e93"),
            ("Completion", f"{progress:.0f}%", "#00c875" if progress >= 50 else "#fdab3d"),
        ]
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        for label, value, color in kpi_data:
            card = self._kpi_card(label, value, color)
            kpi_row.addWidget(card)
        self.main_vbox.addLayout(kpi_row)

        # ── Row 1: Status Donut + Priority Bars ──
        row1 = QHBoxLayout()
        row1.setSpacing(14)
        row1.addWidget(self._status_donut(by_status, total), 1)
        row1.addWidget(self._priority_bars(by_priority, total), 1)
        self.main_vbox.addLayout(row1)

        # ── Row 2: Group Progress + Upcoming Tasks ──
        row2 = QHBoxLayout()
        row2.setSpacing(14)
        row2.addWidget(self._group_progress(group_data), 1)
        row2.addWidget(self._upcoming_tasks(upcoming_tasks), 1)
        self.main_vbox.addLayout(row2)

        # ── Row 3: Today's Agenda (2x) + Quote (1x) ──
        row3 = QHBoxLayout()
        row3.setSpacing(14)
        row3.addWidget(self._today_agenda_card(agenda_tasks), 2)
        row3.addWidget(self._quote_card(), 1)
        self.main_vbox.addLayout(row3)

        # ── Row 4: Activity Log (2x) + Hotkey Legend (1x) ──
        row4 = QHBoxLayout()
        row4.setSpacing(14)
        row4.addWidget(self._activity_log_card(activity), 2)
        row4.addWidget(self._hotkey_legend_card(), 1)
        self.main_vbox.addLayout(row4)

        self.main_vbox.addStretch()

    # ── Bento tiles ──
    def _masthead(self):
        """Atlas-style editorial banner across the top of the dashboard."""
        t = self.theme
        is_serif_skin = self.current_skin in ("atlas", "ember")
        title_family = serif_font_family(self.current_skin) if is_serif_skin else '"Helvetica Neue", -apple-system, sans-serif'

        frame = QFrame()
        # Double border top/bottom to mimic the web masthead.
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border-top: 3px double {t['border']};
                border-bottom: 1px solid {t['border']};
                padding: 10px 2px 12px 2px;
            }}
            QLabel {{ border: none; padding: 0; background: transparent; }}
        """)
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(0, 10, 0, 12)
        vbox.setSpacing(2)

        issue = day_of_year()
        tagline = atlas_tagline_of_day()
        date_str = date.today().strftime("%A, %B %d, %Y")

        issue_lbl = QLabel(f"VOL. II  ·  ISSUE NO. {issue:03d}")
        issue_lbl.setStyleSheet(
            f"color: {t['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 2px;"
        )
        issue_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        vbox.addWidget(issue_lbl)

        title_lbl = QLabel("The Flowdesk Daily")
        title_size = 38 if is_serif_skin else 30
        weight = "700" if is_serif_skin else "800"
        title_lbl.setStyleSheet(
            f"color: {t['text']}; font-family: {title_family}; font-size: {title_size}px; "
            f"font-weight: {weight}; letter-spacing: -0.5px;"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        vbox.addWidget(title_lbl)

        meta_lbl = QLabel(f"{date_str}  ·  {tagline}")
        meta_lbl.setStyleSheet(
            f"color: {t['text_dim']}; font-size: 11px; font-style: italic;"
        )
        meta_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        vbox.addWidget(meta_lbl)

        return frame

    def _today_agenda_card(self, tasks):
        frame, layout = self._card_frame("Today's Agenda")
        t = self.theme

        if not tasks:
            empty = QLabel("No agenda items — enjoy the quiet.")
            empty.setStyleSheet(f"color: {t['text_dim']}; font-size: 12px; border: none;")
            layout.addWidget(empty)
            layout.addStretch()
            return frame

        is_atlas = self.current_skin == "atlas"
        num_family = serif_font_family(self.current_skin) if is_atlas else '"SF Mono", Menlo, monospace'

        for idx, task in enumerate(tasks, start=1):
            row = QHBoxLayout()
            row.setSpacing(10)

            # Numbered tag (serif-italic in Atlas, mono elsewhere).
            num = QLabel(f"{idx:02d}.")
            num.setFixedWidth(28)
            if is_atlas:
                num.setStyleSheet(
                    f"color: {t['accent']}; font-family: {num_family}; font-size: 15px; "
                    f"font-style: italic; border: none; padding: 0;"
                )
            else:
                num.setStyleSheet(
                    f"color: {t['text_dim']}; font-family: {num_family}; font-size: 11px; "
                    f"font-weight: 700; border: none; padding: 0;"
                )
            row.addWidget(num)

            name = QLabel(task.get("name") or "")
            name.setStyleSheet(
                f"color: {t['text']}; font-size: 13px; font-weight: 600; border: none; padding: 0;"
            )
            row.addWidget(name, 1)

            # Priority token (P0/P1/P2/P3).
            tok = priority_to_token(task.get("priority"))
            if tok is not None:
                level, label = tok
                prio_lbl = QLabel(label)
                prio_lbl.setFixedWidth(26)
                prio_color = {"p0": "#e2445c", "p1": "#fdab3d", "p2": "#0073ea", "p3": t['text_dim']}[level]
                prio_lbl.setStyleSheet(
                    f"color: {prio_color}; background: transparent; "
                    f"border: 1px solid {prio_color}; border-radius: 3px; "
                    f"font-family: 'SF Mono', Menlo, monospace; font-size: 9px; "
                    f"font-weight: 700; padding: 1px 4px; letter-spacing: 0.08em;"
                )
                prio_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                row.addWidget(prio_lbl)

            # Group chip
            grp = QLabel(task.get("group_name") or "")
            grp.setStyleSheet(
                f"color: white; background-color: {task.get('group_color') or '#999'}; "
                f"font-size: 10px; font-weight: 600; border-radius: 8px; "
                f"padding: 2px 8px; border: none;"
            )
            row.addWidget(grp)

            # Status dot
            status = task.get("status") or "Not Started"
            status_color = STATUS_COLORS.get(status, "#999")
            dot = QLabel("●")
            dot.setFixedWidth(14)
            dot.setStyleSheet(f"color: {status_color}; font-size: 12px; border: none; padding: 0;")
            dot.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(dot)

            layout.addLayout(row)

        layout.addStretch()
        return frame

    def _quote_card(self):
        """Daily-rotating Atlas-style pull quote."""
        t = self.theme
        text, author = atlas_quote_of_day()
        frame, layout = self._card_frame()

        serif = serif_font_family(self.current_skin)

        # Giant decorative quote mark.
        mark = QLabel('\u201C')
        mark.setStyleSheet(
            f"color: {t['accent']}; font-family: {serif}; font-size: 64px; "
            f"font-weight: 700; border: none; padding: 0; margin: -6px 0 -14px 0;"
        )
        layout.addWidget(mark)

        body = QLabel(text)
        body.setWordWrap(True)
        body.setStyleSheet(
            f"color: {t['text']}; font-family: {serif}; font-size: 16px; "
            f"font-style: italic; line-height: 140%; border: none; padding: 0;"
        )
        layout.addWidget(body)

        author_lbl = QLabel(f"— {author}")
        author_lbl.setStyleSheet(
            f"color: {t['text_dim']}; font-family: 'SF Mono', Menlo, monospace; "
            f"font-size: 11px; font-weight: 600; letter-spacing: 0.05em; border: none; "
            f"padding: 6px 0 0 0;"
        )
        layout.addWidget(author_lbl)

        layout.addStretch()
        return frame

    def _activity_log_card(self, entries):
        frame, layout = self._card_frame("Activity Log")
        t = self.theme

        if not entries:
            empty = QLabel("No activity yet — mutations will show up here.")
            empty.setStyleSheet(f"color: {t['text_dim']}; font-size: 12px; border: none;")
            layout.addWidget(empty)
            layout.addStretch()
            return frame

        kind_colors = {
            "ADD":   "#00c875",
            "DONE":  "#00c875",
            "STUCK": "#e2445c",
            "MOVED": "#0073ea",
            "FLOW":  "#a25ddc",
            "DEL":   "#e2445c",
        }

        for entry in entries:
            ts = (entry.get("ts") or "")[-8:-3]  # "HH:MM" from "YYYY-MM-DD HH:MM:SS"
            kind = entry.get("kind") or ""
            target = entry.get("target") or ""
            detail = entry.get("detail") or ""

            row = QHBoxLayout()
            row.setSpacing(10)

            ts_lbl = QLabel(ts or "")
            ts_lbl.setFixedWidth(46)
            ts_lbl.setStyleSheet(
                f"color: {t['text_dim']}; font-family: 'SF Mono', Menlo, monospace; "
                f"font-size: 11px; border: none; padding: 0;"
            )
            row.addWidget(ts_lbl)

            kind_lbl = QLabel(kind)
            kind_lbl.setFixedWidth(56)
            kcolor = kind_colors.get(kind, t['text_dim'])
            kind_lbl.setStyleSheet(
                f"color: {kcolor}; font-family: 'SF Mono', Menlo, monospace; "
                f"font-size: 10px; font-weight: 700; letter-spacing: 0.06em; "
                f"border: 1px solid {kcolor}; border-radius: 3px; padding: 1px 5px;"
            )
            kind_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(kind_lbl)

            target_lbl = QLabel(target)
            target_lbl.setStyleSheet(
                f"color: {t['text']}; font-size: 12px; font-weight: 600; border: none; padding: 0;"
            )
            row.addWidget(target_lbl, 1)

            if detail:
                detail_lbl = QLabel(f"→ {detail}")
                detail_lbl.setStyleSheet(
                    f"color: {t['text_dim']}; font-size: 11px; border: none; padding: 0;"
                )
                row.addWidget(detail_lbl)

            layout.addLayout(row)

        layout.addStretch()
        return frame

    def _hotkey_legend_card(self):
        frame, layout = self._card_frame("Hotkeys")
        t = self.theme

        for label, keys in HOTKEY_ROWS:
            row = QHBoxLayout()
            row.setSpacing(6)

            name = QLabel(label)
            name.setStyleSheet(
                f"color: {t['text_dim']}; font-size: 11px; border: none; padding: 0;"
            )
            row.addWidget(name, 1)

            for k in keys:
                key_lbl = QLabel(k)
                key_lbl.setStyleSheet(
                    f"color: {t['text']}; background-color: {t['section_bg']}; "
                    f"border: 1px solid {t['border']}; border-radius: 4px; "
                    f"font-family: 'SF Mono', Menlo, monospace; font-size: 10px; "
                    f"font-weight: 600; padding: 1px 5px; min-width: 14px;"
                )
                key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                row.addWidget(key_lbl)

            layout.addLayout(row)

        layout.addStretch()
        return frame

    def _card_frame(self, title=""):
        t = self.theme
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        if title:
            lbl = QLabel(title)
            lbl.setStyleSheet(f"color: {t['text']}; font-size: 14px; font-weight: 700; border: none; padding: 0;")
            layout.addWidget(lbl)
        return frame, layout

    def _kpi_card(self, label, value, color):
        t = self.theme
        frame = QFrame()
        frame.setFixedHeight(80)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 10px;
                border-left: 4px solid {color};
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(2)
        layout.addStretch()

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 800; border: none; padding: 0;")
        layout.addWidget(val_lbl)

        name_lbl = QLabel(label)
        name_lbl.setStyleSheet(f"color: {t['text_dim']}; font-size: 11px; font-weight: 600; border: none; padding: 0;")
        layout.addWidget(name_lbl)
        layout.addStretch()

        return frame

    def _status_donut(self, by_status, total):
        frame, layout = self._card_frame("Task Status Distribution")

        body = QHBoxLayout()
        body.setSpacing(20)

        # Donut chart widget (left)
        donut = _DonutChartWidget(by_status, STATUS_COLORS, total, self.theme)
        donut.setFixedSize(170, 170)
        body.addWidget(donut)

        # Legend (right, vertical)
        legend = QVBoxLayout()
        legend.setSpacing(6)
        legend.addStretch()
        for status, count in by_status.items():
            if count == 0:
                continue
            color = STATUS_COLORS.get(status, "#999")
            pair = QHBoxLayout()
            pair.setSpacing(6)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 12px; border: none; padding: 0;")
            dot.setFixedWidth(14)
            pair.addWidget(dot)
            pct = int(count / total * 100) if total > 0 else 0
            text = QLabel(f"{status}  {count} ({pct}%)")
            text.setStyleSheet(f"color: {self.theme['text']}; font-size: 12px; border: none; padding: 0;")
            pair.addWidget(text)
            pair.addStretch()
            legend.addLayout(pair)
        legend.addStretch()
        body.addLayout(legend, 1)

        layout.addLayout(body)
        return frame

    def _priority_bars(self, by_priority, total):
        frame, layout = self._card_frame("Priority Breakdown")
        t = self.theme
        for prio in ["Critical", "High", "Medium", "Low"]:
            count = by_priority.get(prio, 0)
            pct = int(count / total * 100) if total > 0 else 0
            color = PRIORITY_COLORS.get(prio, "#999")

            row = QHBoxLayout()
            row.setSpacing(8)
            name = QLabel(prio)
            name.setFixedWidth(60)
            name.setStyleSheet(f"color: {t['text']}; font-size: 12px; font-weight: 600; border: none; padding: 0;")
            row.addWidget(name)

            bar = QProgressBar()
            bar.setValue(pct)
            bar.setTextVisible(False)
            bar.setFixedHeight(20)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {t['section_bg']};
                    border-radius: 6px; border: none;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 6px;
                }}
            """)
            row.addWidget(bar, 1)

            cnt_lbl = QLabel(f"{count}")
            cnt_lbl.setFixedWidth(30)
            cnt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            cnt_lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 700; border: none; padding: 0;")
            row.addWidget(cnt_lbl)

            layout.addLayout(row)

        layout.addStretch()
        return frame

    def _group_progress(self, group_data):
        frame, layout = self._card_frame("Group Progress")
        t = self.theme

        if not group_data:
            empty = QLabel("No groups yet")
            empty.setStyleSheet(f"color: {t['text_dim']}; font-size: 12px; border: none;")
            layout.addWidget(empty)
            layout.addStretch()
            return frame

        for g in group_data:
            row = QHBoxLayout()
            row.setSpacing(10)

            color_dot = QLabel("●")
            color_dot.setStyleSheet(f"color: {g['color']}; font-size: 16px; border: none; padding: 0;")
            row.addWidget(color_dot)

            name = QLabel(g["name"])
            name.setFixedWidth(100)
            name.setStyleSheet(f"color: {t['text']}; font-size: 12px; font-weight: 600; border: none; padding: 0;")
            row.addWidget(name)

            pct = (g["done"] / g["total"] * 100) if g["total"] > 0 else 0
            bar = QProgressBar()
            bar.setValue(int(pct))
            bar.setTextVisible(False)
            bar.setFixedHeight(16)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {t['section_bg']};
                    border-radius: 8px; border: none;
                }}
                QProgressBar::chunk {{
                    background-color: {g['color']};
                    border-radius: 8px;
                }}
            """)
            row.addWidget(bar, 1)

            stat = QLabel(f"{g['done']}/{g['total']}")
            stat.setFixedWidth(45)
            stat.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            stat.setStyleSheet(f"color: {t['text_dim']}; font-size: 11px; font-weight: 600; border: none; padding: 0;")
            row.addWidget(stat)

            layout.addLayout(row)

        layout.addStretch()
        return frame

    def _upcoming_tasks(self, tasks):
        frame, layout = self._card_frame("Upcoming Deadlines")
        t = self.theme

        if not tasks:
            empty = QLabel("No upcoming deadlines 🎉")
            empty.setStyleSheet(f"color: {t['text_dim']}; font-size: 12px; border: none;")
            layout.addWidget(empty)
            layout.addStretch()
            return frame

        today = date.today()
        for task in tasks:
            task = dict(task)
            try:
                due = datetime.strptime(task["due_date"], "%Y-%m-%d").date()
                days_left = (due - today).days
            except (ValueError, TypeError):
                continue

            row = QHBoxLayout()
            row.setSpacing(8)

            # Overdue indicator
            if days_left < 0:
                urgency = "🔴"
                days_text = f"{abs(days_left)}d overdue"
                days_color = "#e2445c"
            elif days_left == 0:
                urgency = "🟡"
                days_text = "Today"
                days_color = "#fdab3d"
            elif days_left <= 3:
                urgency = "🟡"
                days_text = f"{days_left}d left"
                days_color = "#fdab3d"
            else:
                urgency = "🟢"
                days_text = f"{days_left}d left"
                days_color = "#00c875"

            urg_lbl = QLabel(urgency)
            urg_lbl.setStyleSheet("font-size: 12px; border: none; padding: 0;")
            urg_lbl.setFixedWidth(20)
            row.addWidget(urg_lbl)

            name_lbl = QLabel(task["name"])
            name_lbl.setStyleSheet(f"color: {t['text']}; font-size: 12px; border: none; padding: 0;")
            row.addWidget(name_lbl, 1)

            grp_lbl = QLabel(task.get("group_name", ""))
            grp_lbl.setStyleSheet(f"""
                color: white; background-color: {task.get('group_color', '#999')};
                font-size: 10px; font-weight: 600; border-radius: 8px;
                padding: 2px 8px; border: none;
            """)
            row.addWidget(grp_lbl)

            due_lbl = QLabel(days_text)
            due_lbl.setFixedWidth(75)
            due_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            due_lbl.setStyleSheet(f"color: {days_color}; font-size: 11px; font-weight: 600; border: none; padding: 0;")
            row.addWidget(due_lbl)

            layout.addLayout(row)

        layout.addStretch()
        return frame


class _DonutChartWidget(QWidget):
    """Custom-painted donut chart."""

    def __init__(self, data, colors, total, theme, parent=None):
        super().__init__(parent)
        self.data = data
        self.colors = colors
        self.total = total
        self.theme = theme

    def paintEvent(self, event):
        if self.total == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        size = min(w, h) - 20
        x = (w - size) // 2
        y = (h - size) // 2
        from PyQt6.QtCore import QRectF
        rect = QRectF(x, y, size, size)

        start_angle = 90 * 16  # Start at top
        for status, count in self.data.items():
            if count == 0:
                continue
            span = int(count / self.total * 360 * 16)
            color = QColor(self.colors.get(status, "#999999"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawPie(rect, start_angle, -span)
            start_angle -= span

        # Inner circle (donut hole)
        hole_size = size * 0.55
        hole_x = x + (size - hole_size) / 2
        hole_y = y + (size - hole_size) / 2
        hole_rect = QRectF(hole_x, hole_y, hole_size, hole_size)
        painter.setBrush(QBrush(QColor(self.theme["card_bg"])))
        painter.drawEllipse(hole_rect)

        # Center text
        painter.setPen(QPen(QColor(self.theme["text"])))
        font = painter.font()
        font.setPointSize(22)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        done = self.data.get("Done", 0)
        pct = int(done / self.total * 100) if self.total > 0 else 0
        painter.drawText(hole_rect, Qt.AlignmentFlag.AlignCenter, f"{pct}%")

        painter.end()


# ─── Timeline View (Horizon 14-day ribbon) ───────────────────
class TimelineView(QWidget):
    """14-day horizontal timeline — one row per flow, tasks as pills at their due date column.

    Mirrors the web's Horizon Timeline. Range: today-3 … today+10.
    """

    task_clicked = pyqtSignal(int)  # task id
    DAY_OFFSETS = list(range(-3, 11))
    DAY_WIDTH = 82
    FLOW_COL_WIDTH = 170

    def __init__(self, db, theme, parent=None, skin_name="prism"):
        super().__init__(parent)
        self.db = db
        self.theme = theme
        self.current_skin = skin_name
        self._build()

    def set_theme(self, theme, skin_name=None):
        self.theme = theme
        if skin_name is not None:
            self.current_skin = skin_name
        self.refresh()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.container = QWidget()
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(16, 14, 16, 14)
        self.vbox.setSpacing(10)

        self.scroll.setWidget(self.container)
        outer.addWidget(self.scroll)
        self.refresh()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                # setParent(None) removes the widget from the view synchronously
                # (deleteLater alone is async and leaves ghost widgets on screen
                # until the next event loop iteration).
                w.setParent(None)
                w.deleteLater()
            else:
                sub = item.layout()
                if sub is not None:
                    self._clear_layout(sub)
                    sub.deleteLater()

    def refresh(self):
        self._clear_layout(self.vbox)
        t = self.theme

        # ── Title strip ──
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_lbl = QLabel("Timeline")
        title_lbl.setStyleSheet(
            f"color: {t['text']}; font-size: 18px; font-weight: 800; border: none; padding: 0;"
        )
        title_row.addWidget(title_lbl)
        sub_lbl = QLabel("14-day window · today − 3 through today + 10")
        sub_lbl.setStyleSheet(
            f"color: {t['text_dim']}; font-size: 11px; border: none; padding-top: 5px;"
        )
        title_row.addWidget(sub_lbl)
        title_row.addStretch()
        self.vbox.addLayout(title_row)

        # ── Scrollable ribbon grid ──
        today = date.today()
        days = [today + timedelta(days=off) for off in self.DAY_OFFSETS]

        # Use QGridLayout for header + data rows.
        grid_frame = QFrame()
        grid_frame.setStyleSheet(
            f"QFrame {{ background-color: {t['card_bg']}; border: 1px solid {t['border']}; "
            f"border-radius: 10px; }}"
        )
        grid = QGridLayout(grid_frame)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setSpacing(0)

        # Header row (row 0): flow label + 14 day headers.
        hdr = QLabel("FLOW / DAY")
        hdr.setFixedSize(self.FLOW_COL_WIDTH, 42)
        hdr.setStyleSheet(
            f"color: {t['text_dim']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.08em; border-bottom: 1px solid {t['border']}; "
            f"padding-left: 10px; background: transparent;"
        )
        hdr.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(hdr, 0, 0)

        for i, d in enumerate(days):
            is_today = d == today
            is_weekend = d.weekday() >= 5
            is_past = d < today
            fg = t['accent'] if is_today else t['text']
            bg = t['section_bg'] if is_weekend else "transparent"
            weight = "800" if is_today else "600"
            day_label = QLabel(f"{d.strftime('%a')}\n{d.day}")
            day_label.setFixedSize(self.DAY_WIDTH, 42)
            day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            border_bot = f"2px solid {t['accent']}" if is_today else f"1px solid {t['border']}"
            opacity = 0.6 if is_past and not is_today else 1.0
            day_label.setStyleSheet(
                f"color: {fg}; font-size: 10px; font-weight: {weight}; "
                f"background-color: {bg}; border-bottom: {border_bot}; "
                f"padding: 4px 0;"
            )
            day_label.setGraphicsEffect(None)  # ensure no lingering effect
            grid.addWidget(day_label, 0, i + 1)

        # Data rows — one per group.
        groups = self.db.get_groups()
        if not groups:
            empty = QLabel("No flows yet. Add a group + task with a due date.")
            empty.setStyleSheet(
                f"color: {t['text_dim']}; font-size: 12px; padding: 24px; border: none;"
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(empty, 1, 0, 1, 15)

        for row_idx, g in enumerate(groups, start=1):
            # Flow label column
            flow_lbl = QFrame()
            flow_lbl.setFixedWidth(self.FLOW_COL_WIDTH)
            flow_lbl.setMinimumHeight(56)
            flow_lbl.setStyleSheet(
                f"QFrame {{ border-left: 3px solid {g['color']}; "
                f"border-bottom: 1px solid {t['border']}; background: transparent; }}"
            )
            flow_vbox = QVBoxLayout(flow_lbl)
            flow_vbox.setContentsMargins(10, 8, 6, 6)
            flow_vbox.setSpacing(2)
            name = QLabel(g['name'])
            name.setStyleSheet(
                f"color: {t['text']}; font-size: 12px; font-weight: 700; border: none; padding: 0;"
            )
            flow_vbox.addWidget(name)
            # Task count subline
            gtasks = [dict(tt) for tt in self.db.get_tasks(g['id'])]
            done = sum(1 for tt in gtasks if tt['status'] == 'Done')
            sub = QLabel(f"{done}/{len(gtasks)} done")
            sub.setStyleSheet(
                f"color: {t['text_dim']}; font-size: 10px; border: none; padding: 0;"
            )
            flow_vbox.addWidget(sub)
            flow_vbox.addStretch()
            grid.addWidget(flow_lbl, row_idx, 0)

            # Compute tasks per day column (0-13)
            tasks_by_col = {i: [] for i in range(14)}
            for tt in gtasks:
                due = tt.get('due_date')
                if not due:
                    continue
                try:
                    dd = datetime.strptime(due, '%Y-%m-%d').date()
                    off = (dd - today).days
                    col = off - self.DAY_OFFSETS[0]
                    if 0 <= col < 14:
                        tasks_by_col[col].append(tt)
                except (ValueError, TypeError):
                    pass

            # Day cells
            for i, d in enumerate(days):
                is_today = d == today
                is_weekend = d.weekday() >= 5
                cell_bg = t['section_bg'] if is_weekend else "transparent"
                cell = QFrame()
                cell.setFixedWidth(self.DAY_WIDTH)
                cell.setMinimumHeight(56)
                border_right = f"1px solid {t['border']}"
                border_bottom = f"1px solid {t['border']}"
                border_top = f"2px solid {t['accent']}" if is_today else "none"
                cell.setStyleSheet(
                    f"QFrame {{ background-color: {cell_bg}; "
                    f"border-right: {border_right}; border-bottom: {border_bottom}; "
                    f"border-top: {border_top}; }}"
                )
                cell_vbox = QVBoxLayout(cell)
                cell_vbox.setContentsMargins(3, 3, 3, 3)
                cell_vbox.setSpacing(3)
                for tt in tasks_by_col[i]:
                    pill = self._make_pill(tt, g['color'])
                    cell_vbox.addWidget(pill)
                cell_vbox.addStretch()
                grid.addWidget(cell, row_idx, i + 1)

        # Wrap in horizontal scroll friendliness.
        self.vbox.addWidget(grid_frame)

        # ── Legend ──
        legend = QHBoxLayout()
        legend.setSpacing(16)
        for status in ["Not Started", "Working on it", "Waiting for review", "Stuck", "Done"]:
            chip = QHBoxLayout()
            chip.setSpacing(4)
            dot = QLabel("●")
            dot.setStyleSheet(
                f"color: {STATUS_COLORS.get(status, '#999')}; font-size: 12px; border: none; padding: 0;"
            )
            chip.addWidget(dot)
            lab = QLabel(status)
            lab.setStyleSheet(
                f"color: {t['text_dim']}; font-size: 10px; border: none; padding: 0;"
            )
            chip.addWidget(lab)
            wrap = QWidget()
            wrap.setLayout(chip)
            legend.addWidget(wrap)
        overdue_chip = QHBoxLayout()
        overdue_chip.setSpacing(4)
        od_box = QLabel("□")
        od_box.setStyleSheet("color: #e2445c; font-size: 12px; border: none; padding: 0;")
        overdue_chip.addWidget(od_box)
        od_lbl = QLabel("Overdue")
        od_lbl.setStyleSheet(f"color: {t['text_dim']}; font-size: 10px; border: none; padding: 0;")
        overdue_chip.addWidget(od_lbl)
        wrap = QWidget()
        wrap.setLayout(overdue_chip)
        legend.addWidget(wrap)
        legend.addStretch()
        self.vbox.addLayout(legend)

        self.vbox.addStretch()

    def _make_pill(self, task, group_color):
        """Render a single task as a clickable colored pill."""
        t = self.theme
        status = task.get('status', 'Not Started')
        status_color = STATUS_COLORS.get(status, '#999')
        name = (task.get('name') or '').strip() or 'Untitled'

        today = date.today()
        overdue = False
        try:
            dd = datetime.strptime(task.get('due_date') or '', '%Y-%m-%d').date()
            overdue = dd < today and status != 'Done'
        except (ValueError, TypeError):
            pass

        pill = QLabel(name)
        pill.setWordWrap(True)
        pill.setMinimumHeight(22)
        pill.setMaximumHeight(44)
        pill.setToolTip(
            f"{name}\nStatus: {status}\nDue: {task.get('due_date') or '—'}"
            + (f"\nPriority: {task.get('priority')}" if task.get('priority') else "")
        )
        pill.setCursor(Qt.CursorShape.PointingHandCursor)

        is_done = status == 'Done'
        bg = status_color if is_done else "transparent"
        fg = "white" if is_done else t['text']
        border = "2px solid #e2445c" if overdue else f"1px solid {status_color}"
        # Slightly darkened left-border matching status to hint the swimlane.
        pill.setStyleSheet(
            f"QLabel {{ background-color: {bg}; color: {fg}; border: {border}; "
            f"border-left: 3px solid {status_color}; border-radius: 4px; padding: 2px 6px; "
            f"font-size: 10px; font-weight: 600; }}"
        )

        # Click → emit task_clicked.
        tid = task.get('id')
        def handler(ev, _tid=tid):
            if _tid is not None:
                self.task_clicked.emit(int(_tid))
        pill.mousePressEvent = handler
        return pill


# ─── Focus Mode (Ember fullscreen) ────────────────────────────
class FocusOverlay(QDialog):
    """Ember-style full-screen focus mode with 50-min countdown.

    Hotkeys while visible:
        Esc            → exit
        Space          → pause/resume
        → / N          → next task
        S              → mark Stuck
        ⌘⏎ / Ctrl+⏎    → mark Done + advance
    """

    status_changed = pyqtSignal()
    SESSION_SECONDS = 50 * 60

    def __init__(self, db, theme, parent=None, skin_name="prism"):
        super().__init__(parent)
        self.db = db
        self.theme = theme
        self.current_skin = skin_name
        self.task_id = None
        self.remaining_sec = self.SESSION_SECONDS
        self.paused = False
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self._build()

    def set_theme(self, theme, skin_name=None):
        self.theme = theme
        if skin_name is not None:
            self.current_skin = skin_name
        if self.isVisible():
            self._render()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 28, 48, 32)
        root.setSpacing(18)

        # Top bar: exit + timer
        top = QHBoxLayout()
        top.setSpacing(10)
        self.exit_btn = QPushButton("✕ Exit")
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.clicked.connect(self.close)
        top.addWidget(self.exit_btn)

        top.addStretch()

        self.pause_indicator = QLabel("")
        top.addWidget(self.pause_indicator)

        self.timer_lbl = QLabel("50:00")
        self.timer_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.timer_lbl)
        root.addLayout(top)

        root.addStretch(2)

        # Middle: task title + meta
        self.eyebrow_lbl = QLabel("NOW FOCUSING")
        self.eyebrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.eyebrow_lbl)

        self.title_lbl = QLabel("")
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.title_lbl)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.meta_lbl)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self.done_btn = QPushButton("✓  Done  ⌘⏎")
        self.done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.done_btn.clicked.connect(lambda: self._mark_status("Done"))
        btn_row.addWidget(self.done_btn)

        self.stuck_btn = QPushButton("×  Stuck  S")
        self.stuck_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stuck_btn.clicked.connect(lambda: self._mark_status("Stuck"))
        btn_row.addWidget(self.stuck_btn)

        self.pause_btn = QPushButton("⏸  Pause  Space")
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.clicked.connect(self._toggle_pause)
        btn_row.addWidget(self.pause_btn)

        self.next_btn = QPushButton("→  Next")
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self._next_task)
        btn_row.addWidget(self.next_btn)

        btn_row.addStretch()
        root.addLayout(btn_row)

        root.addStretch(3)

        # Bottom: queue strip
        self.queue_label = QLabel("UP NEXT")
        self.queue_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.queue_label)

        self.queue_wrap = QWidget()
        self.queue_row = QHBoxLayout(self.queue_wrap)
        self.queue_row.setSpacing(8)
        self.queue_row.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.queue_wrap)

    # ── Public API ──
    def enter(self, task_id=None):
        """Open focus mode. If task_id is None, pick earliest-due candidate."""
        candidates = self._candidates()
        if not candidates:
            QMessageBox.information(self, "Focus", "Nothing to focus on — all clear.")
            return False
        if task_id is None:
            task_id = candidates[0]["id"]
        self.task_id = int(task_id)
        self.remaining_sec = self.SESSION_SECONDS
        self.paused = False
        self._render()
        self._timer.start()
        self.showFullScreen()
        self.activateWindow()
        self.raise_()
        self.setFocus()
        try:
            self.db._log_activity("FOCUS", self._get_task_name() or "", "entered")
        except Exception:
            pass
        return True

    def closeEvent(self, ev):
        self._timer.stop()
        super().closeEvent(ev)

    # ── Data helpers ──
    def _candidates(self, limit=10):
        rows = self.db.conn.execute(
            """SELECT t.id, t.name, t.status, t.priority, t.due_date,
                      g.name AS group_name, g.color AS group_color
               FROM tasks t JOIN groups_ g ON t.group_id = g.id
               WHERE t.status != 'Done'
               ORDER BY
                 CASE WHEN t.due_date IS NULL OR t.due_date = '' THEN 1 ELSE 0 END,
                 t.due_date ASC,
                 CASE t.priority
                   WHEN 'Critical' THEN 0 WHEN 'High' THEN 1
                   WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4
                 END,
                 t.id ASC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def _current_task(self):
        if self.task_id is None:
            return None
        row = self.db.conn.execute(
            """SELECT t.id, t.name, t.status, t.priority, t.due_date,
                      g.name AS group_name, g.color AS group_color
               FROM tasks t JOIN groups_ g ON t.group_id = g.id
               WHERE t.id = ?""",
            (self.task_id,)
        ).fetchone()
        return dict(row) if row else None

    def _get_task_name(self):
        task = self._current_task()
        return task["name"] if task else ""

    # ── Rendering ──
    def _render(self):
        t = self.theme
        serif = serif_font_family(self.current_skin)
        is_dark = bool(t.get("_is_dark", False))

        # Background + chrome styling
        self.setStyleSheet(f"QDialog {{ background-color: {t['bg']}; }}")

        self.exit_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {t['text_dim']}; "
            f"border: 1px solid {t['border']}; border-radius: 8px; padding: 6px 14px; "
            f"font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {t['section_bg']}; color: {t['text']}; }}"
        )
        self.timer_lbl.setStyleSheet(
            f"color: {t['accent']}; font-family: 'SF Mono', Menlo, monospace; "
            f"font-size: 32px; font-weight: 700; border: none;"
        )
        self.pause_indicator.setStyleSheet(
            f"color: {t['text_dim']}; font-size: 11px; letter-spacing: 0.1em;"
        )

        self.eyebrow_lbl.setStyleSheet(
            f"color: {t['text_dim']}; font-size: 11px; font-weight: 700; "
            f"letter-spacing: 0.25em; border: none;"
        )

        # Title
        task = self._current_task()
        if not task:
            self.title_lbl.setText("No task in focus")
            self.meta_lbl.setText("")
        else:
            self.title_lbl.setText(task["name"] or "Untitled")
            # Priority token
            tok = priority_to_token(task.get("priority"))
            tok_label = f"  {tok[1]}  " if tok else ""
            meta = f"{task.get('group_name','')}  ·  due {task.get('due_date') or '—'}{tok_label}  ·  {task.get('status','')}"
            self.meta_lbl.setText(meta.strip())

        self.title_lbl.setStyleSheet(
            f"color: {t['text']}; font-family: {serif}; font-size: 44px; "
            f"font-weight: 700; border: none; padding: 0 20px;"
        )
        self.meta_lbl.setStyleSheet(
            f"color: {t['text_dim']}; font-size: 13px; letter-spacing: 0.05em; border: none;"
        )

        # Buttons
        btn_base = (
            f"QPushButton {{ background: {t['section_bg']}; color: {t['text']}; "
            f"border: 1px solid {t['border']}; border-radius: 10px; padding: 10px 18px; "
            f"font-size: 13px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {t['card_bg']}; border-color: {t['accent']}; }}"
        )
        self.pause_btn.setStyleSheet(btn_base)
        self.next_btn.setStyleSheet(btn_base)
        self.done_btn.setStyleSheet(
            btn_base.replace(t['section_bg'], "#00c875").replace(t['text'], "white")
            .replace(f"border: 1px solid {t['border']}", "border: 1px solid #00c875")
        )
        self.stuck_btn.setStyleSheet(
            btn_base.replace(t['section_bg'], "#e2445c").replace(t['text'], "white")
            .replace(f"border: 1px solid {t['border']}", "border: 1px solid #e2445c")
        )

        # Queue
        self.queue_label.setStyleSheet(
            f"color: {t['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 0.25em;"
        )
        self._render_queue()

        # Timer label + pause state
        self._update_timer_label()
        self.pause_indicator.setText("⏸  PAUSED" if self.paused else "")

    def _render_queue(self):
        # Clear existing
        while self.queue_row.count():
            item = self.queue_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        t = self.theme
        candidates = self._candidates(limit=10)
        # Skip the current task
        candidates = [c for c in candidates if c["id"] != self.task_id][:8]

        self.queue_row.addStretch()
        for c in candidates:
            status = c.get("status", "Not Started")
            color = STATUS_COLORS.get(status, "#999")
            sym = {"Not Started": "○", "Working on it": "▶", "Waiting for review": "◐",
                   "On Hold": "⏸", "Stuck": "✕", "Done": "✓"}.get(status, "○")
            btn = QPushButton(f"{sym}  {c['name'][:24]}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: {t['card_bg']}; color: {t['text']}; "
                f"border: 1px solid {t['border']}; border-left: 3px solid {color}; "
                f"border-radius: 6px; padding: 6px 10px; font-size: 11px; }}"
                f"QPushButton:hover {{ border-color: {t['accent']}; }}"
            )
            tid = c["id"]
            btn.clicked.connect(lambda _=False, _tid=tid: self._switch_task(_tid))
            self.queue_row.addWidget(btn)
        self.queue_row.addStretch()

    def _switch_task(self, task_id):
        self.task_id = int(task_id)
        self.remaining_sec = self.SESSION_SECONDS
        self.paused = False
        self._render()

    # ── Timer ──
    def _on_tick(self):
        if self.paused:
            return
        self.remaining_sec = max(0, self.remaining_sec - 1)
        self._update_timer_label()
        if self.remaining_sec <= 0:
            self._timer.stop()
            QMessageBox.information(self, "Focus", "Session complete — 50 minutes done. Take a break.")

    def _update_timer_label(self):
        m, s = divmod(self.remaining_sec, 60)
        self.timer_lbl.setText(f"{m:02d}:{s:02d}")

    def _toggle_pause(self):
        self.paused = not self.paused
        self.pause_indicator.setText("⏸  PAUSED" if self.paused else "")

    # ── Actions ──
    def _mark_status(self, status):
        if self.task_id is None:
            return
        self.db.update_task(self.task_id, status=status)
        self.status_changed.emit()
        self._next_task()

    def _next_task(self):
        candidates = self._candidates()
        # Pick first candidate that isn't the current one.
        nxt = next((c for c in candidates if c["id"] != self.task_id), None)
        if nxt is None:
            QMessageBox.information(self, "Focus", "Queue complete — nothing else to focus on.")
            self.close()
            return
        self._switch_task(nxt["id"])

    # ── Keyboard ──
    def keyPressEvent(self, ev):
        key = ev.key()
        mods = ev.modifiers()
        if key == Qt.Key.Key_Escape:
            self.close()
            return
        if key == Qt.Key.Key_Space:
            self._toggle_pause()
            return
        if key in (Qt.Key.Key_Right, Qt.Key.Key_N):
            self._next_task()
            return
        if key == Qt.Key.Key_S:
            self._mark_status("Stuck")
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if mods & (Qt.KeyboardModifier.MetaModifier | Qt.KeyboardModifier.ControlModifier):
                self._mark_status("Done")
                return
        super().keyPressEvent(ev)


# ─── Notes Page ──────────────────────────────────────────────
class NoteItemWidget(QWidget):
    """Custom widget for note list items with 2-line preview, Notion-style.

    Displays title (with optional pin/folder icons), content preview, and date.
    Handles special characters safely via Qt text rendering.
    Supports search highlight and tag chips.
    """
    def __init__(self, title, preview, date_str, pinned=False, folder="", show_folder=False, is_active=False, theme=None, highlight="", tags=None, icon="", parent=None):
        super().__init__(parent)
        t = theme or LIGHT_THEME
        self.setFixedHeight(68)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(2)

        # Title line
        title_layout = QHBoxLayout()
        title_layout.setSpacing(4)
        if icon:
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet("font-size: 14px; border: none; background: transparent;")
            icon_lbl.setFixedWidth(18)
            title_layout.addWidget(icon_lbl)
        if pinned:
            pin_lbl = QLabel("\u2605")
            pin_lbl.setStyleSheet("color: #F2994A; font-size: 11px; border: none; background: transparent;")
            pin_lbl.setFixedWidth(14)
            title_layout.addWidget(pin_lbl)
        if show_folder and folder:
            folder_lbl = QLabel("\U0001F4C1")
            folder_lbl.setStyleSheet("font-size: 10px; border: none; background: transparent;")
            folder_lbl.setFixedWidth(14)
            title_layout.addWidget(folder_lbl)
        title_lbl = QLabel()
        if highlight:
            title_lbl.setTextFormat(Qt.TextFormat.RichText)
            title_lbl.setText(self._highlight_text(title, highlight, t))
        else:
            title_lbl.setText(title)
        title_lbl.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        title_lbl.setStyleSheet(f"color: {t.get('text', '#37352F')}; border: none; background: transparent;")
        title_lbl.setMaximumWidth(220)
        title_layout.addWidget(title_lbl)
        # Tag chips in title row (compact, max 2)
        if tags:
            shown_tags = tags[:2]
            for tag in shown_tags:
                bg, fg = get_tag_color(tag)
                tag_lbl = QLabel(tag)
                tag_lbl.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 6px; padding: 1px 5px; font-size: 8px; font-weight: 600; border: none;")
                tag_lbl.setFixedHeight(14)
                title_layout.addWidget(tag_lbl)
            if len(tags) > 2:
                more_lbl = QLabel(f"+{len(tags)-2}")
                more_lbl.setStyleSheet(f"color: {t.get('text_dim', '#999')}; font-size: 8px; border: none; background: transparent;")
                title_layout.addWidget(more_lbl)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Preview + date line
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(6)
        preview_text = preview[:60] if preview else "No content"
        preview_lbl = QLabel()
        if highlight:
            preview_lbl.setTextFormat(Qt.TextFormat.RichText)
            preview_lbl.setText(self._highlight_text(preview_text, highlight, t))
        else:
            preview_lbl.setText(preview_text)
        preview_lbl.setStyleSheet(f"color: {t.get('text_dim', '#999')}; font-size: 11px; border: none; background: transparent;")
        preview_lbl.setMaximumWidth(180)
        bottom_layout.addWidget(preview_lbl)
        bottom_layout.addStretch()
        date_lbl = QLabel(date_str)
        date_lbl.setStyleSheet(f"color: {t.get('text_dim', '#999')}; font-size: 9px; border: none; background: transparent;")
        bottom_layout.addWidget(date_lbl)
        layout.addLayout(bottom_layout)

    @staticmethod
    def _highlight_text(text, query, theme):
        """Return HTML with matching substring highlighted."""
        import html as html_mod
        safe = html_mod.escape(text)
        safe_q = html_mod.escape(query)
        if not safe_q:
            return safe
        import re
        pattern = re.compile(re.escape(safe_q), re.IGNORECASE)
        return pattern.sub(lambda m: f'<span style="background:#FDEB9C; color:#3d3a33; border-radius:2px; padding:0 1px;">{m.group()}</span>', safe)


class NotesPage(QWidget):
    """Full-featured Notion-style notes page with sidebar, folders, rich editor, and search.

    Supports CRUD, folder management, pinning, drag-reorder, linked tasks,
    auto-save with debounce, and keyboard shortcuts.
    """

    def __init__(self, db, theme, parent=None):
        super().__init__(parent)
        self.db = db
        self.theme = theme
        self.current_note_id = None
        self.current_folder = None  # None = show all, "" = unfiled, "X" = folder X
        self._last_saved_content = ""  # Track content for efficient saves
        self._last_saved_title = ""
        self._build()
        self._setup_shortcuts()

    def set_theme(self, theme):
        self.theme = theme
        self.editor.set_theme(theme)
        self._apply_notes_theme()
        self._refresh_folders()
        self._refresh_tag_filter()
        self._refresh_list()

    def _apply_notes_theme(self):
        """Apply comprehensive theme to every notes page element, including dark mode."""
        t = self.theme
        is_dark = t.get('bg', '#fff')[1:3] < '80' if len(t.get('bg', '#fff')) > 3 else False

        # ── Dark-mode overrides for Notion-like feel ──
        sidebar_bg = '#1E1E1E' if is_dark else t.get('section_bg', '#F7F6F3')
        editor_bg = '#191919' if is_dark else t.get('card_bg', '#fff')
        text_color = '#E3E2E0' if is_dark else t.get('text', '#37352F')
        border_color = '#373737' if is_dark else t.get('border', '#E3E2E0')
        active_item_bg = '#2D2D2D' if is_dark else 'rgba(0,115,234,0.08)'
        toolbar_bg = '#252525' if is_dark else t.get('card_bg', '#fff')
        hover_bg = "rgba(255,255,255,0.06)" if is_dark else "rgba(0,0,0,0.04)"
        active_border = t.get('accent', '#0073ea')

        # ── Left panel (sidebar) ──
        self._left_panel.setStyleSheet(f"""
            QWidget#notesLeftPanel {{
                background: {sidebar_bg};
                border-right: 1px solid {border_color};
            }}
        """)

        # ── Note list ──
        self.note_list.setStyleSheet(f"""
            QListWidget {{
                background: {sidebar_bg};
                border: none;
                outline: none;
                font-size: 13px;
            }}
            QListWidget::item {{
                border-radius: 8px;
                margin: 1px 4px;
                padding: 0px;
                border-left: 3px solid transparent;
            }}
            QListWidget::item:hover {{
                background: {hover_bg};
            }}
            QListWidget::item:selected {{
                background: {active_item_bg};
                border-left: 3px solid {active_border};
            }}
        """)

        # ── Search input with focus glow ──
        focus_glow = f"0 0 0 2px rgba(0,115,234,0.3)" if not is_dark else f"0 0 0 2px rgba(0,115,234,0.4)"
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: {t.get('toolbar_input_bg', 'rgba(0,0,0,0.05)')};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 12px;
                color: {text_color};
            }}
            QLineEdit:focus {{
                border: 1px solid {active_border};
            }}
        """)

        # ── Right panel (editor area) ──
        self._right_panel.setStyleSheet(f"""
            QWidget#notesRightPanel {{
                background: {editor_bg};
            }}
        """)

        # ── Title input with subtle bottom line on focus ──
        self.note_title.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                border-bottom: 2px solid transparent;
                background: transparent;
                padding: 4px 0px;
                font-size: 28px;
                font-weight: bold;
                color: {text_color};
            }}
            QLineEdit:focus {{
                border-bottom: 2px solid {border_color};
            }}
            QLineEdit:disabled {{
                color: {t.get('text_dim', '#999')};
                border-bottom: none;
            }}
        """)

        # ── Breadcrumb ──
        self.breadcrumb_label.setStyleSheet(f"color: {t.get('text_dim', '#999')}; font-size: 11px; border: none; background: transparent;")

        # ── Cover banner ──
        cover_color = t.get('accent', '#0073ea')
        self.cover_banner.setStyleSheet(f"""
            QFrame#coverBanner {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {cover_color}, stop:1 {'#00b894' if not is_dark else '#2d6a4f'});
                border-radius: 8px;
                min-height: 6px; max-height: 6px;
            }}
        """)

        # ── Header title and section label ──
        self.header_title.setStyleSheet(f"color: {text_color}; border: none; background: transparent;")
        self.recent_label.setStyleSheet(f"color: {t.get('text_dim', '#999')}; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; border: none; background: transparent; padding-left: 4px;")

        # ── Folder combo ──
        self.folder_combo.setStyleSheet(f"""
            QComboBox {{
                font-size: 11px; padding: 2px 8px; border-radius: 6px;
                border: 1px solid {border_color}; background: transparent;
                color: {text_color};
            }}
            QComboBox:hover {{ border: 1px solid {active_border}; }}
            QComboBox QAbstractItemView {{
                background: {editor_bg}; color: {text_color};
                border: 1px solid {border_color}; border-radius: 6px;
                selection-background-color: {active_item_bg};
            }}
        """)

        # ── Word count & metadata ──
        self.word_count_label.setStyleSheet(f"color: {t.get('text_dim', '#999')}; font-size: 10px; border: none; background: transparent;")
        self.meta_label.setStyleSheet(f"color: {t.get('text_dim', '#999')}; font-size: 10px; border: none; background: transparent;")

        # ── Tag input & search count ──
        self._tag_input.setStyleSheet(f"""
            QLineEdit {{
                font-size: 11px; padding: 2px 6px; border-radius: 6px;
                border: 1px dashed {border_color}; background: transparent;
                color: {text_color};
            }}
            QLineEdit:focus {{ border: 1px solid {active_border}; }}
        """)
        self.search_count_label.setStyleSheet(f"color: {t.get('text_dim', '#999')}; font-size: 10px; border: none; background: transparent; padding-left: 4px;")
        self._tag_filter_label.setStyleSheet(f"color: {t.get('text_dim', '#999')}; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; border: none; background: transparent; padding-left: 4px;")

        # ── Font combo ──
        self.font_combo.setStyleSheet(f"""
            QComboBox {{
                font-size: 11px; padding: 2px 8px; border-radius: 6px;
                border: 1px solid {border_color}; background: transparent;
                color: {text_color};
            }}
            QComboBox:hover {{ border: 1px solid {active_border}; }}
            QComboBox QAbstractItemView {{
                background: {editor_bg}; color: {text_color};
                border: 1px solid {border_color}; border-radius: 6px;
                selection-background-color: {active_item_bg};
            }}
        """)

        # ── Export button ──
        if hasattr(self, 'export_btn'):
            export_menu_bg = '#252525' if is_dark else '#fff'
            export_menu_sel = '#2D2D2D' if is_dark else '#F7F6F3'
            self.export_btn.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid {border_color}; border-radius: 6px;
                    padding: 2px 10px; font-size: 11px; background: transparent;
                    color: {text_color};
                }}
                QPushButton:hover {{ border: 1px solid {active_border}; color: {active_border}; }}
                QPushButton::menu-indicator {{ image: none; width: 0px; }}
            """)
            self.export_btn.menu().setStyleSheet(f"""
                QMenu {{ background: {export_menu_bg}; border: 1px solid {border_color}; border-radius: 6px; padding: 4px; }}
                QMenu::item {{ padding: 5px 16px; border-radius: 4px; font-size: 12px; color: {text_color}; }}
                QMenu::item:selected {{ background: {export_menu_sel}; }}
            """)

        # ── Save indicator ──
        if hasattr(self, '_save_indicator'):
            self._save_indicator.setStyleSheet(f"color: {t.get('text_dim', '#999')}; font-size: 10px; border: none; background: transparent;")

        # ── Empty state ──
        if hasattr(self, '_empty_state'):
            self._empty_state.setStyleSheet(f"color: {t.get('text_dim', '#999')}; background: transparent; border: none;")
            for child in self._empty_state.findChildren(QLabel):
                child.setStyleSheet(f"color: {t.get('text_dim', '#999')}; border: none; background: transparent;")
            for child in self._empty_state.findChildren(QPushButton):
                child.setStyleSheet(f"QPushButton {{ background-color: {active_border}; color: white; border: none; border-radius: 20px; font-size: 20px; font-weight: bold; }} QPushButton:hover {{ background-color: #0060c7; }}")

        # ── Splitter hover color ──
        if hasattr(self, '_splitter'):
            self._splitter.setStyleSheet(f"""
                QSplitter::handle {{ background: transparent; }}
                QSplitter::handle:hover {{ background: {active_border}; }}
            """)

    def _build(self):
        """Build the complete notes UI: sidebar, editor, toolbars, empty state."""
        # ── Timers ──
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._do_save)

        self._search_debounce = QTimer()
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(150)
        self._search_debounce.timeout.connect(self._do_search)

        # Save indicator fade timer
        self._save_indicator_timer = QTimer()
        self._save_indicator_timer.setSingleShot(True)
        self._save_indicator_timer.setInterval(1500)
        self._save_indicator_timer.timeout.connect(lambda: self._save_indicator.setText(""))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Splitter with hover-widen effect ──
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(1)
        self._splitter.setStyleSheet("""
            QSplitter::handle { background: transparent; }
            QSplitter::handle:hover { background: #0073ea; }
        """)
        # Set col-resize cursor on splitter handle
        handle = self._splitter.handle(1) if self._splitter.count() > 1 else None
        splitter = self._splitter

        # ── Left panel - folder + note list ──
        self._left_panel = QWidget()
        self._left_panel.setObjectName("notesLeftPanel")
        self._left_panel.setMinimumWidth(200)
        self._left_panel.setMaximumWidth(500)
        left_layout = QVBoxLayout(self._left_panel)
        left_layout.setContentsMargins(10, 12, 10, 10)
        left_layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        self.header_title = QLabel("Notes")
        self.header_title.setFont(QFont("Inter", 15, QFont.Weight.Bold))
        header.addWidget(self.header_title)
        header.addStretch()

        # New folder button
        new_folder_btn = QPushButton("\U0001F4C1")
        new_folder_btn.setFixedSize(28, 28)
        new_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_folder_btn.setToolTip("New Folder")
        new_folder_btn.setStyleSheet("QPushButton { border: none; font-size: 14px; background: transparent; border-radius: 6px; } QPushButton:hover { background: rgba(0,0,0,0.06); }")
        new_folder_btn.clicked.connect(self._new_folder)
        header.addWidget(new_folder_btn)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("QPushButton { background-color: #0073ea; color: white; border: none; border-radius: 14px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #0060c7; }")
        add_btn.clicked.connect(self._new_note)
        header.addWidget(add_btn)
        left_layout.addLayout(header)

        # Folder bar (scrollable)
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
        self.search.setPlaceholderText("\U0001F50D Search notes...")
        self.search.setFixedHeight(32)
        self.search.setStyleSheet("""
            QLineEdit {
                background: rgba(0,0,0,0.05); border: 1px solid #E3E2E0;
                border-radius: 8px; padding: 4px 12px; font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #0073ea; }
        """)
        self.search.textChanged.connect(self._on_search_changed)
        left_layout.addWidget(self.search)

        # Search result count label
        self.search_count_label = QLabel("")
        self.search_count_label.setStyleSheet("color: #999; font-size: 10px; border: none; background: transparent; padding-left: 4px;")
        self.search_count_label.hide()
        left_layout.addWidget(self.search_count_label)

        # Tag filter section
        self._tag_filter_label = QLabel("Tags")
        self._tag_filter_label.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        self._tag_filter_label.setStyleSheet("color: #999; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; border: none; background: transparent; padding-left: 4px;")
        left_layout.addWidget(self._tag_filter_label)

        self._tag_filter_scroll = QScrollArea()
        self._tag_filter_scroll.setWidgetResizable(True)
        self._tag_filter_scroll.setFixedHeight(30)
        self._tag_filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tag_filter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tag_filter_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollArea > QWidget > QWidget { background: transparent; }")
        self._tag_filter_container = QWidget()
        self._tag_filter_bar = QHBoxLayout(self._tag_filter_container)
        self._tag_filter_bar.setContentsMargins(0, 0, 0, 0)
        self._tag_filter_bar.setSpacing(4)
        self._tag_filter_scroll.setWidget(self._tag_filter_container)
        left_layout.addWidget(self._tag_filter_scroll)
        self._active_tag_filter = None  # Currently active tag filter

        # "Recently Edited" section label
        self.recent_label = QLabel("Recently Edited")
        self.recent_label.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        self.recent_label.setStyleSheet("color: #999; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; border: none; background: transparent; padding-left: 4px;")
        left_layout.addWidget(self.recent_label)

        # Note list (drag-drop enabled)
        self.note_list = QListWidget()
        self.note_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.note_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.note_list.setStyleSheet("""
            QListWidget {
                background: transparent; border: none; outline: none;
            }
            QListWidget::item {
                border-radius: 8px; margin: 1px 4px; padding: 0px;
                border-left: 3px solid transparent;
            }
            QListWidget::item:hover { background: rgba(0,0,0,0.04); }
            QListWidget::item:selected {
                background: rgba(0,115,234,0.08);
                border-left: 3px solid #0073ea;
            }
        """)
        self.note_list.currentRowChanged.connect(self._on_note_selected)
        self.note_list.model().rowsMoved.connect(self._on_rows_moved)
        left_layout.addWidget(self.note_list)

        splitter.addWidget(self._left_panel)

        # ── Right panel - editor ──
        self._right_panel = QWidget()
        self._right_panel.setObjectName("notesRightPanel")
        right_layout = QVBoxLayout(self._right_panel)
        right_layout.setContentsMargins(28, 16, 28, 12)
        right_layout.setSpacing(4)

        # Cover/banner stripe
        self.cover_banner = QFrame()
        self.cover_banner.setObjectName("coverBanner")
        self.cover_banner.setFixedHeight(6)
        self.cover_banner.setStyleSheet("""
            QFrame#coverBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0073ea, stop:1 #00b894);
                border-radius: 8px;
                min-height: 6px; max-height: 6px;
            }
        """)
        right_layout.addWidget(self.cover_banner)
        right_layout.addSpacing(8)

        # Breadcrumb: folder > note title
        self.breadcrumb_label = QLabel("")
        self.breadcrumb_label.setStyleSheet("color: #999; font-size: 11px; border: none; background: transparent;")
        right_layout.addWidget(self.breadcrumb_label)

        # ── Note title + controls row ──
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.note_title = QLineEdit()
        self.note_title.setPlaceholderText("Untitled")
        self.note_title.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        self.note_title.setStyleSheet("""
            QLineEdit {
                border: none; border-bottom: 2px solid transparent;
                background: transparent; padding: 4px 0px;
                font-size: 28px; font-weight: bold; color: #37352F;
            }
            QLineEdit:focus { border-bottom: 2px solid #E3E2E0; }
        """)
        self.note_title.setMinimumHeight(44)
        self.note_title.textChanged.connect(self._save_current)
        title_row.addWidget(self.note_title)

        # Auto-save indicator ("Saving..." / "Saved")
        self._save_indicator = QLabel("")
        self._save_indicator.setStyleSheet("color: #999; font-size: 10px; border: none; background: transparent;")
        self._save_indicator.setFixedWidth(60)
        title_row.addWidget(self._save_indicator)

        # Folder combo for current note
        self.folder_combo = QComboBox()
        self.folder_combo.setFixedWidth(130)
        self.folder_combo.setFixedHeight(28)
        self.folder_combo.setStyleSheet("""
            QComboBox {
                font-size: 11px; padding: 2px 8px; border-radius: 6px;
                border: 1px solid #E3E2E0; background: transparent;
            }
            QComboBox:hover { border: 1px solid #0073ea; }
        """)
        self.folder_combo.setToolTip("Move to folder")
        self.folder_combo.currentTextChanged.connect(self._on_folder_changed_for_note)
        title_row.addWidget(self.folder_combo)

        # Export button with dropdown menu
        self.export_btn = QPushButton("Export \u25be")
        self.export_btn.setFixedHeight(28)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #E3E2E0; border-radius: 6px;
                padding: 2px 10px; font-size: 11px; background: transparent;
                color: #37352F;
            }
            QPushButton:hover { border: 1px solid #0073ea; color: #0073ea; }
            QPushButton::menu-indicator { image: none; width: 0px; }
        """)
        export_menu = QMenu(self)
        export_menu.setStyleSheet("""
            QMenu { background: #fff; border: 1px solid #E3E2E0; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 5px 16px; border-radius: 4px; font-size: 12px; color: #37352F; }
            QMenu::item:selected { background: #F7F6F3; }
        """)
        export_menu.addAction("Markdown (.md)", self._export_markdown)
        export_menu.addAction("HTML (.html)", self._export_html)
        export_menu.addAction("PDF (.pdf)", self._export_pdf)
        self.export_btn.setMenu(export_menu)
        title_row.addWidget(self.export_btn)

        self.pin_btn = QPushButton("\u2606")
        self.pin_btn.setFixedSize(30, 30)
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.setStyleSheet("QPushButton { border: none; font-size: 17px; background: transparent; border-radius: 6px; } QPushButton:hover { background: rgba(0,0,0,0.06); }")
        self.pin_btn.clicked.connect(self._toggle_pin)
        title_row.addWidget(self.pin_btn)

        self.del_btn = QPushButton("\u2715")
        self.del_btn.setFixedSize(30, 30)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setStyleSheet("QPushButton { border: none; font-size: 14px; color: #e2445c; background: transparent; border-radius: 6px; } QPushButton:hover { background: rgba(226,68,92,0.08); }")
        self.del_btn.clicked.connect(self._delete_note)
        title_row.addWidget(self.del_btn)

        right_layout.addLayout(title_row)

        # ── Font selector row ──
        font_row = QHBoxLayout()
        font_row.setSpacing(6)
        font_label = QLabel("Font:")
        font_label.setStyleSheet("font-size: 11px; color: #999; border: none; background: transparent;")
        font_row.addWidget(font_label)
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Sans-serif", "Serif", "Monospace"])
        self.font_combo.setFixedWidth(110)
        self.font_combo.setFixedHeight(26)
        self.font_combo.setStyleSheet("""
            QComboBox {
                font-size: 11px; padding: 2px 8px; border-radius: 6px;
                border: 1px solid #E3E2E0; background: transparent;
            }
            QComboBox:hover { border: 1px solid #0073ea; }
        """)
        self.font_combo.currentTextChanged.connect(self._on_font_changed)
        font_row.addWidget(self.font_combo)
        font_row.addStretch()
        right_layout.addLayout(font_row)

        # ── Tags bar ──
        self._tags_widget = QWidget()
        tags_layout = QHBoxLayout(self._tags_widget)
        tags_layout.setContentsMargins(0, 2, 0, 2)
        tags_layout.setSpacing(4)
        tags_icon = QLabel("Tags:")
        tags_icon.setStyleSheet("font-size: 10px; font-weight: 600; color: #999; border: none; background: transparent;")
        tags_layout.addWidget(tags_icon)
        self._tag_chips_layout = QHBoxLayout()
        self._tag_chips_layout.setSpacing(4)
        tags_layout.addLayout(self._tag_chips_layout)
        self._tag_input = QLineEdit()
        self._tag_input.setPlaceholderText("Add tag...")
        self._tag_input.setFixedHeight(24)
        self._tag_input.setFixedWidth(100)
        self._tag_input.setStyleSheet("""
            QLineEdit {
                font-size: 11px; padding: 2px 6px; border-radius: 6px;
                border: 1px dashed #ccc; background: transparent;
            }
            QLineEdit:focus { border: 1px solid #0073ea; }
        """)
        self._tag_input.returnPressed.connect(self._add_tag_from_input)
        tags_layout.addWidget(self._tag_input)
        tags_layout.addStretch()
        right_layout.addWidget(self._tags_widget)

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
        right_layout.addSpacing(4)

        # ── Separator between title area and editor ──
        title_sep = QFrame()
        title_sep.setFixedHeight(1)
        title_sep.setStyleSheet(f"background: {self.theme.get('border', '#E3E2E0')}; border: none; margin: 0 0 4px 0;")
        right_layout.addWidget(title_sep)

        # ── Rich text editor ──
        self.editor = RichTextEditor(self.theme)
        self.editor.content_changed.connect(self._save_current)
        right_layout.addWidget(self.editor)

        # ── Bottom bar: word count + reading time | metadata ──
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(16)
        self.word_count_label = QLabel("")
        self.word_count_label.setStyleSheet("color: #999; font-size: 10px; border: none; background: transparent;")
        bottom_bar.addWidget(self.word_count_label)
        bottom_bar.addStretch()
        self.meta_label = QLabel()
        self.meta_label.setStyleSheet("color: #999; font-size: 10px; border: none;")
        bottom_bar.addWidget(self.meta_label)
        right_layout.addLayout(bottom_bar)

        splitter.addWidget(self._right_panel)
        splitter.setSizes([280, 700])  # default sizes

        # Set cursor on splitter handle after both widgets are added
        handle = splitter.handle(1)
        if handle:
            handle.setCursor(Qt.CursorShape.SplitHCursor)

        layout.addWidget(splitter)

        # ── Empty state overlay (shown when no notes exist) ──
        self._empty_state = QWidget(self._right_panel)
        self._empty_state.setObjectName("emptyState")
        empty_layout = QVBoxLayout(self._empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon = QLabel("\U0001F4DD")
        empty_icon.setFont(QFont("Inter", 36))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet("border: none; background: transparent;")
        empty_layout.addWidget(empty_icon)
        empty_msg = QLabel("Create your first note")
        empty_msg.setFont(QFont("Inter", 14))
        empty_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_msg.setStyleSheet("color: #999; border: none; background: transparent;")
        empty_layout.addWidget(empty_msg)
        empty_btn = QPushButton("+")
        empty_btn.setFixedSize(40, 40)
        empty_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_btn.setStyleSheet("QPushButton { background-color: #0073ea; color: white; border: none; border-radius: 20px; font-size: 20px; font-weight: bold; } QPushButton:hover { background-color: #0060c7; }")
        empty_btn.clicked.connect(self._new_note)
        empty_layout.addWidget(empty_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self._empty_state.hide()

        self._refresh_folders()
        self._refresh_tag_filter()
        self._refresh_list()
        self._set_editor_enabled(False)

    # ── Keyboard shortcuts ──────────────────────────────────────
    def _setup_shortcuts(self):
        """Register all keyboard shortcuts for the notes page."""
        # Ctrl+N: New note
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._new_note)
        # Ctrl+Delete / Ctrl+Backspace: Delete current note
        QShortcut(QKeySequence("Ctrl+Delete"), self, activated=self._delete_note)
        QShortcut(QKeySequence("Ctrl+Backspace"), self, activated=self._delete_note)
        # Ctrl+Shift+P: Toggle pin
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, activated=self._toggle_pin)
        # Ctrl+F: Focus search
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)
        # Escape: Clear search and return to editor
        QShortcut(QKeySequence("Escape"), self, activated=self._escape_search)
        # Ctrl+Shift+Up/Down: Navigate between notes
        QShortcut(QKeySequence("Ctrl+Shift+Up"), self, activated=self._prev_note)
        QShortcut(QKeySequence("Ctrl+Shift+Down"), self, activated=self._next_note)
        # Ctrl+/: Trigger slash command menu in editor
        QShortcut(QKeySequence("Ctrl+/"), self, activated=self._trigger_slash_menu)

    def _focus_search(self):
        """Focus the search input and select its text."""
        self.search.setFocus()
        self.search.selectAll()

    def _escape_search(self):
        """Clear search text and return focus to the editor."""
        if self.search.hasFocus() or self.search.text():
            self.search.clear()
            if self.current_note_id:
                self.editor.editor.setFocus()

    def _prev_note(self):
        """Select the previous note in the list."""
        row = self.note_list.currentRow()
        if row > 0:
            self.note_list.setCurrentRow(row - 1)

    def _next_note(self):
        """Select the next note in the list."""
        row = self.note_list.currentRow()
        if row < self.note_list.count() - 1:
            self.note_list.setCurrentRow(row + 1)

    def _trigger_slash_menu(self):
        """Open the slash command menu at the current cursor position in the editor."""
        if not self.current_note_id:
            return
        self.editor._slash_active = True
        self.editor._slash_filter = ""
        self.editor._slash_menu.filter("")
        rect = self.editor.editor.cursorRect()
        global_pos = self.editor.editor.mapToGlobal(rect.bottomLeft())
        self.editor._slash_menu.move(global_pos.x(), global_pos.y() + 4)
        self.editor._slash_menu.show()
        self.editor.editor.setFocus()

    # ── Debounced search ──────────────────────────────────────
    def _on_search_changed(self):
        """Start the 150ms debounce timer when search text changes."""
        self._search_debounce.start()

    def _do_search(self):
        """Execute the actual search filtering after debounce."""
        self._refresh_list()

    # ── Word count & breadcrumb ──────────────────────────────
    def _update_word_count(self):
        """Update the word count and estimated reading time in the bottom bar."""
        text = self.editor.get_plain_text()
        words = len(text.split()) if text.strip() else 0
        reading_min = max(1, words // 200)
        self.word_count_label.setText(f"{words} words  \u00B7  {reading_min} min read")

    def _update_breadcrumb(self):
        """Update the breadcrumb with clickable folder name (11px, gray, folder emoji)."""
        if not self.current_note_id:
            self.breadcrumb_label.setText("")
            return
        note = self.db.conn.execute("SELECT folder, title FROM notes WHERE id=?", (self.current_note_id,)).fetchone()
        if note:
            folder = note["folder"] if note["folder"] else "Notes"
            # Use rich text for clickable folder
            t = self.theme
            link_color = t.get('accent', '#0073ea')
            self.breadcrumb_label.setTextFormat(Qt.TextFormat.RichText)
            self.breadcrumb_label.setText(
                f'<span style="font-size:11px; color:{t.get("text_dim", "#999")};">'
                f'\U0001F4C1 <a href="folder:{folder}" style="color:{link_color}; text-decoration:none;">{folder}</a>'
                f'  /  {note["title"]}</span>'
            )
            # Connect link click if not already connected
            try:
                self.breadcrumb_label.linkActivated.disconnect()
            except TypeError:
                pass
            self.breadcrumb_label.linkActivated.connect(self._on_breadcrumb_click)

    def _on_breadcrumb_click(self, link):
        """Handle breadcrumb folder click to switch to that folder view."""
        if link.startswith("folder:"):
            folder_name = link[7:]
            if folder_name == "Notes":
                self._select_folder(None)
            else:
                self._select_folder(folder_name)

    # ── Folder management ────────────────────────────────────
    def _refresh_folders(self):
        """Rebuild the folder button bar with note counts."""
        while self.folder_bar.count():
            item = self.folder_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        folders = self.db.get_note_folders()
        t = self.theme

        # Get note counts per folder
        all_notes = self.db.get_notes()
        folder_counts = {}
        total_count = len(all_notes)
        for n in all_notes:
            n = dict(n)
            f = n.get("folder", "")
            folder_counts[f] = folder_counts.get(f, 0) + 1

        def make_btn(label, folder_val, icon="", count=0):
            active = self.current_folder == folder_val
            display = f"{icon} {label}".strip()
            if count > 0:
                display += f" ({count})"
            btn = QPushButton(display)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            bg = t.get("accent", "#0073ea") if active else "transparent"
            fg = "white" if active else t.get("text", "#3d3a33")
            border = "none" if active else f"1px solid {t.get('border', '#e8e0c8')}"
            btn.setStyleSheet(f"QPushButton {{ background: {bg}; color: {fg}; border: {border}; border-radius: 13px; padding: 2px 10px; font-size: 11px; font-weight: 600; }} QPushButton:hover {{ background: {t.get('accent', '#0073ea')}; color: white; }}")
            btn.clicked.connect(lambda: self._select_folder(folder_val))
            return btn

        self.folder_bar.addWidget(make_btn("All", None, "", total_count))
        for f in folders:
            count = folder_counts.get(f, 0)
            btn = make_btn(f, f, "\U0001F4C1", count)
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
        """Show rename/delete context menu for a folder button."""
        from PyQt6.QtWidgets import QMenu
        t = self.theme
        is_dark = t.get('bg', '#fff')[1:3] < '80' if len(t.get('bg', '#fff')) > 3 else False
        menu_bg = '#252525' if is_dark else '#fff'
        menu_border = '#373737' if is_dark else '#E3E2E0'
        menu_hover = '#2D2D2D' if is_dark else '#F7F6F3'
        menu_text = '#E3E2E0' if is_dark else '#37352F'
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {menu_bg}; border: 1px solid {menu_border}; border-radius: 6px; padding: 4px; }}
            QMenu::item {{ padding: 6px 16px; border-radius: 4px; font-size: 12px; color: {menu_text}; }}
            QMenu::item:selected {{ background: {menu_hover}; }}
        """)
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
        self._update_breadcrumb()

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

    # ── Drag reorder ───────────────────────────────────────────
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
        """Enable or disable the editor panel; show empty state when no note is selected."""
        self.note_title.setEnabled(enabled)
        self.editor.editor.setEnabled(enabled)
        self.pin_btn.setEnabled(enabled)
        self.del_btn.setEnabled(enabled)
        self.folder_combo.setEnabled(enabled)
        self.font_combo.setEnabled(enabled)
        self.linked_tasks_widget.setVisible(enabled)
        self._tags_widget.setVisible(enabled)
        self.cover_banner.setVisible(enabled)
        self._save_indicator.setVisible(enabled)
        # Show/hide empty state
        has_notes = hasattr(self, '_notes_cache') and len(self._notes_cache) > 0
        self._empty_state.setVisible(not enabled and not has_notes)
        if not enabled:
            self.note_title.clear()
            self.editor.set_html("")
            self.meta_label.setText("Select or create a note" if has_notes else "")
            self.word_count_label.setText("")
            self.breadcrumb_label.setText("")

    def _get_plain_preview(self, content):
        """Extract a plain-text preview (max 80 chars) from HTML content.

        Strips all HTML tags, collapses whitespace, and handles special characters.
        """
        if not content:
            return ""
        import re
        import html as html_mod
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', ' ', content)
        # Decode HTML entities (handles &lt; &gt; &amp; &quot; etc.)
        text = html_mod.unescape(text)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:80]

    def _refresh_list(self):
        """Rebuild the note list from database, applying folder, tag, and search filters."""
        import re as _re
        import html as _html_mod
        self.note_list.blockSignals(True)
        self.note_list.clear()
        search = self.search.text().lower() if hasattr(self, 'search') else ""
        notes = self.db.get_notes()
        self._notes_cache = []
        all_folders = set(self.db.get_note_folders()) if hasattr(self.db, 'get_note_folders') else set()
        match_count = 0

        for n in notes:
            n = dict(n)
            # Filter by folder
            if self.current_folder is not None:
                if n.get("folder", "") != self.current_folder:
                    continue
            # Filter by active tag filter
            if hasattr(self, '_active_tag_filter') and self._active_tag_filter:
                note_tags = [t.strip() for t in n.get("tags", "").split(",") if t.strip()]
                if self._active_tag_filter not in note_tags:
                    continue
            # Filter by search (title + plain-text content)
            if search:
                plain_content = _re.sub(r'<[^>]+>', ' ', n.get("content", ""))
                plain_content = _html_mod.unescape(plain_content)
                plain_content = _re.sub(r'\s+', ' ', plain_content).strip()
                if search not in n["title"].lower() and search not in plain_content.lower():
                    continue
                match_count += 1

            # Handle deleted folder: if note references a folder that no longer exists
            note_folder = n.get("folder", "")
            if note_folder and note_folder not in all_folders:
                note_folder = "Unfiled"

            self._notes_cache.append(n)

            # Create rich list item with preview
            preview = self._get_plain_preview(n.get("content", ""))
            updated = n["updated_at"][:10] if n.get("updated_at") else ""
            show_folder = self.current_folder is None and bool(n.get("folder"))
            note_tags = [t.strip() for t in n.get("tags", "").split(",") if t.strip()]

            # Truncate long titles for sidebar display
            display_title = n["title"]
            if len(display_title) > 30:
                display_title = display_title[:28] + "..."

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, n["id"])
            item.setSizeHint(QSize(0, 68))
            item.setToolTip(f"{n['title']}\nFolder: {note_folder or '(none)'}  |  Updated: {n['updated_at'][:16] if n.get('updated_at') else ''}")
            self.note_list.addItem(item)

            widget = NoteItemWidget(
                title=display_title,
                preview=preview,
                date_str=updated,
                pinned=bool(n["pinned"]),
                folder=note_folder,
                show_folder=show_folder,
                theme=self.theme,
                highlight=search,
                tags=note_tags if note_tags else None,
                icon=n.get("icon", ""),
            )
            self.note_list.setItemWidget(item, widget)

        self.note_list.blockSignals(False)

        # Update search result count
        if hasattr(self, 'search_count_label'):
            if search:
                self.search_count_label.setText(f"{match_count} result{'s' if match_count != 1 else ''}")
                self.search_count_label.show()
            else:
                self.search_count_label.setText("")
                self.search_count_label.hide()

        # Update the "Recently Edited" label visibility
        if hasattr(self, 'recent_label'):
            self.recent_label.setVisible(len(self._notes_cache) > 0)

        # Show/hide empty state
        if hasattr(self, '_empty_state'):
            has_notes = len(self._notes_cache) > 0
            self._empty_state.setVisible(not has_notes and not self.current_note_id)

        # Re-select current note
        if self.current_note_id:
            for i in range(self.note_list.count()):
                if self.note_list.item(i).data(Qt.ItemDataRole.UserRole) == self.current_note_id:
                    self.note_list.setCurrentRow(i)
                    break

    def _on_note_selected(self, row):
        """Handle note selection: auto-save previous, load new note, warn on large content."""
        # Auto-save previous note before switching (prevent data loss)
        if self.current_note_id and self._save_timer.isActive():
            self._save_timer.stop()
            self._do_save()

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
        content = note.get("content", "")
        self.editor.set_html(content)
        self.editor.editor.blockSignals(False)

        # Track last saved state for efficient save comparisons
        self._last_saved_title = note["title"]
        self._last_saved_content = self.editor.get_html()

        # Warn about very large notes
        if len(content) > 100000:
            self.meta_label.setText(f"Large note ({len(content)//1000}K chars - may be slow)  |  Created: {note['created_at'][:16]}")
        else:
            self.meta_label.setText(f"Created: {note['created_at'][:16]}  |  Updated: {note['updated_at'][:16]}")

        self.pin_btn.setText("\u2605" if note["pinned"] else "\u2606")

        # Load font preference
        note_font = note.get("font", "Sans-serif") or "Sans-serif"
        self.font_combo.blockSignals(True)
        idx = self.font_combo.findText(note_font)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
        else:
            self.font_combo.setCurrentIndex(0)
        self.font_combo.blockSignals(False)
        # Apply font to editor
        families = FONT_FAMILIES.get(note_font, FONT_FAMILIES['Sans-serif'])
        self.editor.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.theme['card_bg']};
                color: {self.theme['text']};
                border: none;
                border-radius: 8px;
                padding: 20px 28px;
                font-size: 14px;
                font-family: {families};
                selection-background-color: rgba(45,125,230,0.25);
            }}
        """)

        self._sync_folder_combo()
        self._refresh_linked_tasks()
        self._refresh_tag_chips()
        self._update_breadcrumb()
        self._update_word_count()

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

    # ── Auto-save with change detection ────────────────────────
    def _save_current(self):
        """Debounced save - waits 500ms after last keystroke, shows indicator."""
        if not self.current_note_id:
            return
        self._save_indicator.setText("Saving...")
        self._save_timer.start()

    def _do_save(self):
        """Save to DB only if content actually changed, then update sidebar item."""
        if not self.current_note_id:
            return
        title = self.note_title.text().strip() or "Untitled"
        content = self.editor.get_html()

        # Skip save if nothing changed (efficient saves)
        if title == self._last_saved_title and content == self._last_saved_content:
            self._save_indicator.setText("Saved")
            self._save_indicator_timer.start()
            return

        self.db.update_note(self.current_note_id, title=title, content=content)
        self._last_saved_title = title
        self._last_saved_content = content

        # Show "Saved" indicator briefly
        self._save_indicator.setText("Saved")
        self._save_indicator_timer.start()

        # Update the left-side list item text without triggering full refresh
        display_title = title if len(title) <= 30 else title[:28] + "..."
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == self.current_note_id:
                note = self.db.conn.execute("SELECT pinned, folder, tags FROM notes WHERE id=?", (self.current_note_id,)).fetchone()
                preview = self._get_plain_preview(content)
                note_tags = [t.strip() for t in note["tags"].split(",") if t.strip()] if note and note["tags"] else []
                note_icon = self.db.conn.execute("SELECT icon FROM notes WHERE id=?", (self.current_note_id,)).fetchone()
                widget = NoteItemWidget(
                    title=display_title,
                    preview=preview,
                    date_str=datetime.now().strftime("%Y-%m-%d"),
                    pinned=bool(note["pinned"]) if note else False,
                    folder=note["folder"] if note else "",
                    show_folder=self.current_folder is None and bool(note and note["folder"]),
                    theme=self.theme,
                    tags=note_tags if note_tags else None,
                    icon=note_icon["icon"] if note_icon and note_icon["icon"] else "",
                )
                self.note_list.setItemWidget(item, widget)
                break

        # Also update the cache
        for i, n in enumerate(self._notes_cache):
            if n["id"] == self.current_note_id:
                self._notes_cache[i]["title"] = title
                self._notes_cache[i]["content"] = content
                break

        self._update_breadcrumb()
        self._update_word_count()

    # ── Export functions ────────────────────────────────────────
    def _export_markdown(self):
        """Export current note as Markdown file."""
        if self.current_note_id is None:
            return
        note = dict(self.db.conn.execute("SELECT * FROM notes WHERE id=?", (self.current_note_id,)).fetchone())
        if not note:
            return

        content = self.editor.get_html()
        md = f"# {note['title']}\n\n"
        md += self._html_to_markdown(content)

        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export Markdown",
            f"{note['title']}.md", "Markdown (*.md)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(md)

    def _html_to_markdown(self, html):
        """Basic HTML to Markdown conversion."""
        import re
        md = html
        md = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<strong>(.*?)</strong>', r'**\1**', md, flags=re.DOTALL)
        md = re.sub(r'<b>(.*?)</b>', r'**\1**', md, flags=re.DOTALL)
        md = re.sub(r'<em>(.*?)</em>', r'*\1*', md, flags=re.DOTALL)
        md = re.sub(r'<i>(.*?)</i>', r'*\1*', md, flags=re.DOTALL)
        md = re.sub(r'<del>(.*?)</del>', r'~~\1~~', md, flags=re.DOTALL)
        md = re.sub(r'<code>(.*?)</code>', r'`\1`', md, flags=re.DOTALL)
        md = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'> \1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<li>(.*?)</li>', r'- \1\n', md, flags=re.DOTALL)
        md = re.sub(r'<hr\s*/?>', r'\n---\n\n', md)
        md = re.sub(r'<br\s*/?>', r'\n', md)
        md = re.sub(r'<p>(.*?)</p>', r'\1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<[^>]+>', '', md)  # strip remaining HTML tags
        md = md.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
        return md.strip()

    def _export_html(self):
        """Export current note as HTML file."""
        if self.current_note_id is None:
            return
        note = dict(self.db.conn.execute("SELECT * FROM notes WHERE id=?", (self.current_note_id,)).fetchone())
        if not note:
            return

        content = self.editor.get_html()
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{note['title']}</title>
<style>body{{font-family:-apple-system,sans-serif;max-width:720px;margin:40px auto;padding:0 20px;line-height:1.7;color:#37352F;}}
h1{{font-size:40px;font-weight:700;}}blockquote{{border-left:3px solid #E3E2E0;padding-left:16px;color:#666;}}
pre{{background:#F7F6F3;padding:16px;border-radius:6px;overflow-x:auto;}}
table{{border-collapse:collapse;width:100%;}}th,td{{border:1px solid #E3E2E0;padding:8px 12px;}}th{{background:#F7F6F3;}}</style>
</head><body><h1>{note['title']}</h1>{content}</body></html>"""

        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export HTML",
            f"{note['title']}.html", "HTML (*.html)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)

    def _export_pdf(self):
        """Export current note as PDF via QPrinter."""
        if self.current_note_id is None:
            return
        from PyQt6.QtPrintSupport import QPrinter
        from PyQt6.QtWidgets import QFileDialog

        note = dict(self.db.conn.execute("SELECT * FROM notes WHERE id=?", (self.current_note_id,)).fetchone())
        if not note:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export PDF",
            f"{note['title']}.pdf", "PDF (*.pdf)")
        if not path:
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        self.editor.editor.document().print(printer)

    # ── CRUD operations ─────────────────────────────────────────
    def _new_note(self):
        """Create a new note and scroll to it smoothly in the list."""
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
            # Smooth scroll to new item
            item = self.note_list.item(target_row)
            self.note_list.scrollToItem(item, QListWidget.ScrollHint.EnsureVisible)
            self._on_note_selected(target_row)
        self.note_title.setFocus()
        self.note_title.selectAll()

    def _toggle_pin(self):
        """Toggle the pinned state of the current note (Ctrl+Shift+P)."""
        if not self.current_note_id:
            return
        note = dict(self.db.conn.execute("SELECT * FROM notes WHERE id=?", (self.current_note_id,)).fetchone())
        new_pin = 0 if note["pinned"] else 1
        self.db.update_note(self.current_note_id, pinned=new_pin)
        self.pin_btn.setText("\u2605" if new_pin else "\u2606")
        self._refresh_list()

    def _delete_note(self):
        """Delete the current note after confirmation (Ctrl+Delete)."""
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

    # ── Linked tasks ───────────────────────────────────────────
    def _link_task(self):
        """Open dialog to link an unlinked task to the current note."""
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

    # ── Tag management ──────────────────────────────────────────
    def _add_tag_from_input(self):
        """Add a tag from the tag input field to the current note."""
        if not self.current_note_id:
            return
        tag = self._tag_input.text().strip()
        if not tag:
            return
        note = self.db.conn.execute("SELECT tags FROM notes WHERE id=?", (self.current_note_id,)).fetchone()
        existing = [t.strip() for t in note["tags"].split(",") if t.strip()] if note["tags"] else []
        if tag not in existing:
            existing.append(tag)
            self.db.update_note(self.current_note_id, tags=",".join(existing))
        self._tag_input.clear()
        self._refresh_tag_chips()
        self._refresh_tag_filter()
        self._refresh_list()

    def _remove_tag(self, tag):
        """Remove a tag from the current note."""
        if not self.current_note_id:
            return
        note = self.db.conn.execute("SELECT tags FROM notes WHERE id=?", (self.current_note_id,)).fetchone()
        existing = [t.strip() for t in note["tags"].split(",") if t.strip()] if note["tags"] else []
        if tag in existing:
            existing.remove(tag)
            self.db.update_note(self.current_note_id, tags=",".join(existing))
        self._refresh_tag_chips()
        self._refresh_tag_filter()
        self._refresh_list()

    def _refresh_tag_chips(self):
        """Rebuild the tag chips in the editor area for the current note."""
        while self._tag_chips_layout.count():
            item = self._tag_chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.current_note_id:
            return
        note = self.db.conn.execute("SELECT tags FROM notes WHERE id=?", (self.current_note_id,)).fetchone()
        if not note or not note["tags"]:
            return
        tags = [t.strip() for t in note["tags"].split(",") if t.strip()]
        for tag in tags:
            bg, fg = get_tag_color(tag)
            chip = QPushButton(f"{tag}  \u00d7")
            chip.setFixedHeight(22)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setStyleSheet(f"""
                QPushButton {{
                    background: {bg}; color: {fg}; border: none; border-radius: 11px;
                    padding: 2px 8px; font-size: 10px; font-weight: 600;
                }}
                QPushButton:hover {{ background: {fg}; color: white; }}
            """)
            chip.clicked.connect(lambda checked, t=tag: self._remove_tag(t))
            self._tag_chips_layout.addWidget(chip)

    def _refresh_tag_filter(self):
        """Rebuild the tag filter chips in the sidebar."""
        while self._tag_filter_bar.count():
            item = self._tag_filter_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_tags = self.db.get_all_tags()
        has_tags = len(all_tags) > 0
        self._tag_filter_label.setVisible(has_tags)
        self._tag_filter_scroll.setVisible(has_tags)

        if not has_tags:
            return

        t = self.theme
        for tag in all_tags:
            bg, fg = get_tag_color(tag)
            is_active = self._active_tag_filter == tag
            if is_active:
                style = f"QPushButton {{ background: {fg}; color: white; border: none; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: 600; }} QPushButton:hover {{ opacity: 0.85; }}"
            else:
                style = f"QPushButton {{ background: {bg}; color: {fg}; border: none; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: 600; }} QPushButton:hover {{ background: {fg}; color: white; }}"
            btn = QPushButton(tag)
            btn.setFixedHeight(20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(style)
            btn.clicked.connect(lambda checked, tg=tag: self._toggle_tag_filter(tg))
            self._tag_filter_bar.addWidget(btn)
        self._tag_filter_bar.addStretch()

    def _toggle_tag_filter(self, tag):
        """Toggle a tag filter on/off."""
        if self._active_tag_filter == tag:
            self._active_tag_filter = None
        else:
            self._active_tag_filter = tag
        self._refresh_tag_filter()
        self._refresh_list()

    # ── Font selector ──────────────────────────────────────────
    def _on_font_changed(self, font_name):
        """Apply the selected font to the editor and save to note."""
        if not self.current_note_id:
            return
        families = FONT_FAMILIES.get(font_name, FONT_FAMILIES['Sans-serif'])
        self.editor.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.theme['card_bg']};
                color: {self.theme['text']};
                border: none;
                border-radius: 8px;
                padding: 20px 28px;
                font-size: 14px;
                font-family: {families};
                selection-background-color: rgba(45,125,230,0.25);
            }}
        """)
        self.db.update_note(self.current_note_id, font=font_name)


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

            # Prism P0/P1/P2 token prefix on priority badge
            _ptok = priority_to_token(task["priority"])
            _ptxt = f"{_ptok[1]}  {task['priority']}" if _ptok else task["priority"]
            pbadge = BadgeWidget(_ptxt, PRIORITY_COLORS.get(task["priority"], "#999"), min_w=110)
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
        # P0/P1/P2 priority token (Prism)
        ptok = priority_to_token(self.task.get("priority", ""))
        if ptok is not None:
            lvl, lbl = ptok
            tok_color = {
                "p0": "#e2445c",  # P0 — critical
                "p1": "#fdab3d",  # P1 — high
                "p2": "#0073ea",  # P2 — normal
                "p3": "#a1a1a1",  # P3 — low
            }.get(lvl, theme['text_dim'])
            tok = QLabel(lbl)
            tok.setStyleSheet(
                f"color: white; background-color: {tok_color}; "
                f"border-radius: 3px; padding: 0 5px; font-size: 9px; "
                f"font-weight: 700; letter-spacing: 0.5px; border: none;"
            )
            meta.addWidget(tok)
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
        # Skin system — restore persisted choice if any, default to 'prism'
        self._settings = QSettings("Flowdesk", "Flowdesk")
        saved_skin = self._settings.value("skin", "prism")
        if saved_skin not in SKIN_THEMES:
            saved_skin = "prism"
        self.current_skin = saved_skin
        self.theme = SKIN_THEMES[saved_skin]
        # Legacy dark_mode kept in sync with the skin's isDark flag
        self.dark_mode = bool(self.theme.get("_is_dark", False))
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

        # Skin picker button (◎) — opens a menu with all 5 skins
        self.skin_btn = QPushButton("\u25CE")
        self.skin_btn.setFixedSize(28, 28)
        self.skin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.skin_btn.setToolTip("Change skin (⌘⇧T cycles)")
        self.skin_btn.clicked.connect(self._open_skin_menu)
        tb.addWidget(self.skin_btn)

        self.dark_btn = QPushButton("\u263d")
        self.dark_btn.setFixedSize(28, 28)
        self.dark_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dark_btn.setToolTip("Toggle light/dark (Prism ↔ Mission)")
        self.dark_btn.clicked.connect(self._toggle_dark)
        tb.addWidget(self.dark_btn)

        # Focus mode launcher (⌘⇧F)
        self.focus_btn = QPushButton("\u29BF")  # ⦿ circled bullseye
        self.focus_btn.setFixedSize(28, 28)
        self.focus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.focus_btn.setToolTip("Enter Focus mode (⌘⇧F)")
        self.focus_btn.clicked.connect(self._toggle_focus_mode)
        tb.addWidget(self.focus_btn)

        tb.addWidget(QLabel("  "))

        # Global shortcut: Cmd/Ctrl+Shift+T cycles through skins
        self._skin_shortcut = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        self._skin_shortcut.activated.connect(self._cycle_skin)

        # Global shortcut: Cmd/Ctrl+Shift+F opens Focus mode
        self._focus_shortcut = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        self._focus_shortcut.activated.connect(self._toggle_focus_mode)

        # Vim-style g-then-X navigation (g h/f/b/t/c/n)
        self._goto_pending = False
        self._goto_timer = QTimer(self)
        self._goto_timer.setSingleShot(True)
        self._goto_timer.setInterval(900)  # 900ms window to press second key
        self._goto_timer.timeout.connect(self._goto_timeout)
        self._goto_map = {
            Qt.Key.Key_H: (0, "Dashboard"),
            Qt.Key.Key_F: (1, "Flows"),
            Qt.Key.Key_B: (2, "Board"),
            Qt.Key.Key_T: (3, "Timeline"),
            Qt.Key.Key_C: (4, "Calendar"),
            Qt.Key.Key_N: (5, "Notes"),
        }

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

        # Tab widget - now with 5 tabs
        self.tabs = QTabWidget()

        # Dashboard view
        self.dashboard_page = DashboardPage(self.db, self.theme, skin_name=self.current_skin)
        self.tabs.addTab(self.dashboard_page, "Dashboard")

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

        # Timeline view (14-day horizon)
        self.timeline_view = TimelineView(self.db, self.theme, skin_name=self.current_skin)
        self.timeline_view.task_clicked.connect(self._jump_to_kanban_for_task)
        self.tabs.addTab(self.timeline_view, "Timeline")

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
        if hasattr(self, 'dashboard_page'):
            self.dashboard_page.refresh()
        if hasattr(self, 'timeline_view'):
            self.timeline_view.refresh()
        self._update_status_footer()
        # Don't refresh notes list while user is actively editing
        # (it would steal focus / disrupt typing)

    # ── Timeline → Kanban jump ──
    def _jump_to_kanban_for_task(self, task_id):
        """Switch to Kanban tab when a Timeline pill is clicked."""
        try:
            idx = self.tabs.indexOf(self.kanban_scroll) if hasattr(self, 'kanban_scroll') else -1
            if idx >= 0:
                self.tabs.setCurrentIndex(idx)
        except Exception:
            pass

    # ── Status footer (Iter 4 polish) ──
    def _update_status_footer(self):
        """Refresh the status bar string with flows + tasks + sync state."""
        try:
            stats = self.db.get_stats()
            groups = self.db.get_groups()
            skin = getattr(self, 'current_skin', 'prism')
            msg = (
                f"● {stats['total']} tasks  ·  {len(groups)} flows  ·  "
                f"{stats['by_status'].get('Working on it', 0)} working  ·  "
                f"{stats['by_status'].get('Stuck', 0)} stuck  ·  "
                f"skin: {skin}  ·  Flowdesk v2.4"
            )
            self.statusBar().showMessage(msg)
        except Exception:
            pass

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
        """Legacy dark toggle — flips between the current skin's light/dark counterparts.
        Prism↔Mission by default. Kept for backward compatibility with old keybindings."""
        next_skin = "mission" if not self.theme.get("_is_dark") else "prism"
        self.set_skin(next_skin)

    def set_skin(self, name):
        """Switch to a named skin. Persists the choice via QSettings."""
        if name not in SKIN_THEMES:
            return
        self.current_skin = name
        self.theme = SKIN_THEMES[name]
        self.dark_mode = bool(self.theme.get("_is_dark", False))
        if hasattr(self, "_settings"):
            self._settings.setValue("skin", name)
        self._apply_theme()
        self._refresh()

    def _cycle_skin(self):
        """Cycle to next skin in SKIN_ORDER. Triggered by Cmd/Ctrl+Shift+T."""
        cur = getattr(self, "current_skin", "prism")
        try:
            i = SKIN_ORDER.index(cur)
        except ValueError:
            i = 0
        self.set_skin(SKIN_ORDER[(i + 1) % len(SKIN_ORDER)])

    def keyPressEvent(self, ev):
        """Two-stroke vim nav: press 'g' then h/f/b/t/c/n to jump tabs.

        Skipped when focus is on a text-input widget so it doesn't swallow typing.
        """
        fw = QApplication.focusWidget()
        if fw is not None and isinstance(fw, (QLineEdit, QTextEdit)):
            super().keyPressEvent(ev)
            return

        if self._goto_pending:
            dst = self._goto_map.get(ev.key())
            self._goto_pending = False
            self._goto_timer.stop()
            if dst is not None:
                idx, label = dst
                if 0 <= idx < self.tabs.count():
                    self.tabs.setCurrentIndex(idx)
                    self.statusBar().showMessage(f"→ {label}", 1200)
                ev.accept()
                return
            # Fall through if second key didn't match
        if ev.key() == Qt.Key.Key_G and not (ev.modifiers() & (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier
            | Qt.KeyboardModifier.AltModifier)):
            self._goto_pending = True
            self._goto_timer.start()
            self.statusBar().showMessage("g… (h/f/b/t/c/n)", 900)
            ev.accept()
            return
        super().keyPressEvent(ev)

    def _goto_timeout(self):
        self._goto_pending = False
        self.statusBar().clearMessage()

    def _toggle_focus_mode(self):
        """Open Focus mode overlay, or close it if already open. ⌘⇧F."""
        ov = getattr(self, "_focus_overlay", None)
        if ov is None:
            ov = FocusOverlay(self.db, self.theme, parent=self, skin_name=self.current_skin)
            ov.status_changed.connect(self._refresh)
            self._focus_overlay = ov
        if ov.isVisible():
            ov.close()
            return
        ov.set_theme(self.theme, skin_name=self.current_skin)
        ov.enter()

    def _open_skin_menu(self):
        """Popup menu with all 5 skins, showing a color swatch + tagline for each."""
        from PyQt6.QtWidgets import QMenu, QWidgetAction, QLabel, QHBoxLayout, QWidget
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.theme['card_bg']};
                color: {self.theme['text']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{ padding: 6px 14px 6px 10px; border-radius: 6px; }}
            QMenu::item:selected {{ background-color: {self.theme['section_bg']}; }}
        """)
        for sid in SKIN_ORDER:
            label, tagline, swatch = SKIN_LABELS[sid]
            row = QWidget()
            lay = QHBoxLayout(row)
            lay.setContentsMargins(10, 4, 14, 4)
            lay.setSpacing(10)
            dot = QLabel()
            dot.setFixedSize(14, 14)
            dot.setStyleSheet(f"background-color: {swatch}; border-radius: 7px;")
            check = "● " if sid == self.current_skin else "   "
            name_lbl = QLabel(f"{check}{label}")
            name_lbl.setStyleSheet(f"color: {self.theme['text']}; font-size: 12px; font-weight: {'700' if sid == self.current_skin else '500'};")
            tag_lbl = QLabel(tagline)
            tag_lbl.setStyleSheet(f"color: {self.theme['text_dim']}; font-size: 10.5px;")
            lay.addWidget(dot)
            lay.addWidget(name_lbl)
            lay.addStretch(1)
            lay.addWidget(tag_lbl)
            act = QWidgetAction(menu)
            act.setDefaultWidget(row)
            act.triggered.connect(lambda _checked=False, s=sid: self.set_skin(s))
            # QWidgetAction swallows clicks on the inner widget; route them manually:
            def _mouse_factory(sid_):
                def _h(ev, _sid=sid_):
                    self.set_skin(_sid)
                    menu.close()
                return _h
            row.mousePressEvent = _mouse_factory(sid)
            menu.addAction(act)
        btn = self.skin_btn
        menu.exec(btn.mapToGlobal(btn.rect().bottomRight()) - QPoint(menu.sizeHint().width(), 0))

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
        # Skin picker button
        if hasattr(self, 'skin_btn'):
            # Use current accent color for the glyph to hint at active skin
            self.skin_btn.setStyleSheet(f"""
                QPushButton {{ border: none; font-size: 16px; color: {t['accent']}; background: transparent; border-radius: 6px; font-weight: 700; }}
                QPushButton:hover {{ background-color: {t['toolbar_btn_hover']}; }}
            """)
        # Sync indicator
        if hasattr(self, 'sync_indicator'):
            self.sync_indicator.set_theme(t)
        if hasattr(self, 'calendar_view'):
            self.calendar_view.set_theme(t)
        if hasattr(self, 'notes_page'):
            self.notes_page.set_theme(t)
        if hasattr(self, 'dashboard_page'):
            self.dashboard_page.set_theme(t, skin_name=getattr(self, 'current_skin', 'prism'))
        if hasattr(self, 'timeline_view'):
            self.timeline_view.set_theme(t, skin_name=getattr(self, 'current_skin', 'prism'))

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
