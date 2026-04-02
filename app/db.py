import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS kv (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT UNIQUE,
            original_name TEXT,
            suggested_name TEXT,
            extension TEXT,
            folder_path TEXT,
            parent_path TEXT,
            last_modified TEXT,
            approved INTEGER DEFAULT 0,
            renamed INTEGER DEFAULT 0,
            over30 INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS rename_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT,
            original_name TEXT,
            new_name TEXT,
            folder_path TEXT,
            status TEXT,
            error TEXT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def kv_set(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)", (key, json.dumps(value)))
    conn.commit()
    conn.close()


def kv_get(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
    conn.close()
    return json.loads(row['value']) if row else default


def kv_delete(key):
    conn = get_conn()
    conn.execute("DELETE FROM kv WHERE key = ?", (key,))
    conn.commit()
    conn.close()


def clear_files():
    conn = get_conn()
    conn.execute("DELETE FROM files")
    conn.commit()
    conn.close()


def insert_files(rows):
    conn = get_conn()
    conn.executemany("""
        INSERT OR REPLACE INTO files
        (item_id, original_name, suggested_name, extension, folder_path, parent_path, last_modified, over30)
        VALUES (:item_id, :original_name, :suggested_name, :extension, :folder_path, :parent_path, :last_modified, :over30)
    """, rows)
    conn.commit()
    conn.close()


def get_files(folder=None, search=None, approved=None, over30=None, offset=0, limit=100):
    conn = get_conn()
    conditions = ["renamed = 0"]
    params = []

    if folder:
        conditions.append("folder_path LIKE ?")
        params.append(f"/{folder.strip('/')}%")
    if search:
        conditions.append("(original_name LIKE ? OR suggested_name LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if approved is not None:
        conditions.append("approved = ?")
        params.append(1 if approved else 0)
    if over30 is not None:
        conditions.append("over30 = ?")
        params.append(1 if over30 else 0)

    where = " AND ".join(conditions)
    total = conn.execute(f"SELECT COUNT(*) FROM files WHERE {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM files WHERE {where} ORDER BY folder_path, original_name LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()
    conn.close()
    return total, [dict(r) for r in rows]


def get_top_folders():
    conn = get_conn()
    rows = conn.execute("""
        SELECT SUBSTR(folder_path, 2, INSTR(SUBSTR(folder_path, 2), '/') - 1) as top_folder,
               COUNT(*) as file_count,
               SUM(CASE WHEN approved=1 THEN 1 ELSE 0 END) as approved_count
        FROM files
        WHERE renamed = 0
        GROUP BY top_folder
        ORDER BY top_folder
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def approve_files(item_ids, approved=True):
    conn = get_conn()
    placeholders = ','.join('?' * len(item_ids))
    conn.execute(
        f"UPDATE files SET approved = ? WHERE item_id IN ({placeholders})",
        [1 if approved else 0] + list(item_ids)
    )
    conn.commit()
    conn.close()


def approve_folder(folder_path):
    conn = get_conn()
    conn.execute(
        "UPDATE files SET approved = 1 WHERE folder_path LIKE ? AND renamed = 0",
        [f"/{folder_path.strip('/')}%"]
    )
    conn.commit()
    conn.close()


def update_suggested_name(item_id, suggested_name):
    conn = get_conn()
    over30 = 1 if len(suggested_name) > 30 else 0
    conn.execute(
        "UPDATE files SET suggested_name = ?, over30 = ? WHERE item_id = ?",
        (suggested_name, over30, item_id)
    )
    conn.commit()
    conn.close()


def get_approved_for_folder(folder_path):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM files
        WHERE folder_path LIKE ?
        AND approved = 1
        AND renamed = 0
        AND suggested_name != original_name
        AND suggested_name != 'DELETE - Temp File'
    """, [f"/{folder_path.strip('/')}%"]).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_renamed(item_id, status, error=""):
    conn = get_conn()
    if status == "OK":
        conn.execute("UPDATE files SET renamed = 1 WHERE item_id = ?", (item_id,))
    conn.execute("""
        INSERT INTO rename_log (item_id, original_name, new_name, folder_path, status, error)
        SELECT item_id, original_name, suggested_name || extension, folder_path, ?, ?
        FROM files WHERE item_id = ?
    """, (status, error, item_id))
    conn.commit()
    conn.close()


def get_rename_log(limit=200):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM rename_log ORDER BY ts DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_conn()
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN approved=1 THEN 1 ELSE 0 END) as approved,
            SUM(CASE WHEN renamed=1 THEN 1 ELSE 0 END) as renamed,
            SUM(CASE WHEN over30=1 AND renamed=0 THEN 1 ELSE 0 END) as over30,
            SUM(CASE WHEN suggested_name='DELETE - Temp File' THEN 1 ELSE 0 END) as temp_files
        FROM files
    """).fetchone()
    conn.close()
    return dict(stats)
