"""
db.py — SQLite database helper (no ORM, uses built-in sqlite3)
"""
import sqlite3
from flask import g, current_app

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(current_app.config["DATABASE"])
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            role       TEXT DEFAULT 'staff',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            meal_time        TEXT,
            service_type     TEXT,
            day_type         TEXT,
            customers_count  INTEGER,
            checkout_price   REAL,
            base_price       REAL,
            emailer          INTEGER,
            homepage         INTEGER,
            pred_demand      REAL,
            pred_wastage     REAL,
            pred_quantity    REAL,
            alert            TEXT,
            created_at       TEXT DEFAULT (datetime('now'))
        );
    """)
    db.commit(); db.close()

def query(sql, args=(), one=False):
    db = get_db()
    cur = db.execute(sql, args)
    rv  = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid
