"""
SharePoint Rename App — FastAPI Backend
Multi-tenant, session-based, Render-ready
"""
import os, re, time, uuid, threading
import requests
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from .naming import clean_name, extract_folder_path, generate_suggestions

# ── Config ─────────────────────────────────────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'static')

# Permissions needed
SCOPES_READ  = "https://graph.microsoft.com/Sites.Read.All https://graph.microsoft.com/Files.Read.All"
SCOPES_WRITE = "https://graph.microsoft.com/Sites.ReadWrite.All https://graph.microsoft.com/Files.ReadWrite.All"

# ── In-memory session store ────────────────────────────────────────────────────
# { session_id: { token, user, files, scan_state, rename_state, write_access } }
_sessions: dict = {}
SESSION_TTL = 4 * 60 * 60  # 4 hours

def _gc_sessions():
    now = time.time()
    dead = [k for k, v in _sessions.items() if now - v.get('ts', 0) > SESSION_TTL]
    for k in dead:
        del _sessions[k]

def get_session(session_id: str) -> dict:
    _gc_sessions()
    if not session_id or session_id not in _sessions:
        raise HTTPException(401, "Session expired or invalid. Please sign in again.")
    sess = _sessions[session_id]
    sess['ts'] = time.time()
    return sess

def new_session() -> tuple[str, dict]:
    sid = str(uuid.uuid4())
    _sessions[sid] = {'ts': time.time(), 'files': [], 'scan_state': {'status': 'idle'}, 'rename_state': {'status': 'idle'}}
    return sid, _sessions[sid]

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="SharePoint Rename App")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))



# ── Auth ───────────────────────────────────────────────────────────────────────

class TokenBody(BaseModel):
    access_token: str
    write_access: bool = False

@app.post("/api/auth/session")
def create_session(body: TokenBody):
    """Frontend calls this after getting a token from MSAL.js"""
    # Validate token by calling /me
    resp = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {body.access_token}"},
        timeout=10
    )
    if resp.status_code != 200:
        raise HTTPException(401, "Invalid access token")

    me = resp.json()
    sid, sess = new_session()
    sess['token'] = body.access_token
    sess['write_access'] = body.write_access
    sess['user'] = {
        "name":   me.get("displayName"),
        "email":  me.get("mail") or me.get("userPrincipalName"),
        "tenant": me.get("userPrincipalName", "").split("@")[-1],
    }
    return {"session_id": sid, "user": sess['user']}


@app.get("/api/auth/me")
def auth_me(x_session_id: Optional[str] = Header(None)):
    if not x_session_id or x_session_id not in _sessions:
        return {"authenticated": False}
    sess = _sessions[x_session_id]
    return {"authenticated": True, "user": sess.get('user'), "write_access": sess.get('write_access', False)}


@app.delete("/api/auth/session")
def delete_session(x_session_id: Optional[str] = Header(None)):
    if x_session_id and x_session_id in _sessions:
        del _sessions[x_session_id]
    return {"ok": True}


# ── Scan ───────────────────────────────────────────────────────────────────────

class ScanConfig(BaseModel):
    site_url: str
    library: str
    exclude_folders: List[str] = ["Research"]

def _graph_get(token, url):
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    resp.raise_for_status()
    return resp.json()

def _scan_recursive(token, site_id, drive_id, folder_url, exclude, counters, state):
    try:
        data = _graph_get(token, folder_url)
    except Exception:
        return []

    items = data.get("value", [])
    nxt = data.get("@odata.nextLink")
    while nxt:
        try:
            page = _graph_get(token, nxt)
            items.extend(page.get("value", []))
            nxt = page.get("@odata.nextLink")
        except Exception:
            break

    files = []
    for item in items:
        remote = item.get("remoteItem")
        if "folder" in item or (remote and "folder" in remote):
            if item["name"] in exclude:
                continue
            counters["folders"] += 1
            state["message"] = f"Scanning: {item['name']}  ({counters['files']:,} files so far)"
            if remote:
                rd = remote["parentReference"]["driveId"]
                ri = remote["id"]
                child_url = f"https://graph.microsoft.com/v1.0/drives/{rd}/items/{ri}/children"
                files.extend(_scan_recursive(token, site_id, rd, child_url, exclude, counters, state))
            else:
                child_url = (
                    f"https://graph.microsoft.com/v1.0/sites/{site_id}"
                    f"/drives/{drive_id}/items/{item['id']}/children"
                )
                files.extend(_scan_recursive(token, site_id, drive_id, child_url, exclude, counters, state))
        else:
            counters["files"] += 1
            state["progress"] = counters["files"]
            files.append({
                "name":          item["name"],
                "parent_path":   item["parentReference"]["path"],
                "item_id":       item["id"],
                "last_modified": item["lastModifiedDateTime"],
            })
    return files

def _do_scan(session_id: str, config: ScanConfig):
    sess = _sessions.get(session_id)
    if not sess:
        return
    state = sess['scan_state']
    state.update({"status": "running", "message": "Connecting...", "progress": 0, "total": 0})
    token = sess['token']

    try:
        import urllib.parse
        parsed   = urllib.parse.urlparse(config.site_url)
        hostname = parsed.netloc
        path     = parsed.path.strip("/")
        site     = _graph_get(token, f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{path}")
        site_id  = site["id"]

        drives = _graph_get(token, f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives")["value"]
        drive  = next((d for d in drives if d["name"] == config.library), None)
        if not drive:
            available = ", ".join(d["name"] for d in drives)
            state.update({"status": "error", "message": f"Library '{config.library}' not found. Available: {available}"})
            return
        drive_id = drive["id"]

        state["message"] = "Scanning files..."
        folder_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children"
        counters   = {"files": 0, "folders": 0}
        all_files  = _scan_recursive(token, site_id, drive_id, folder_url, config.exclude_folders, counters, state)

        state["message"] = "Generating suggested names..."
        import os as _os
        rows = []
        for f in all_files:
            base, ext = _os.path.splitext(f["name"])
            fp = extract_folder_path(f["parent_path"])
            rows.append({
                "item_id":       f["item_id"],
                "original_name": base,
                "suggested_name": "",
                "extension":     ext,
                "folder_path":   fp,
                "parent_path":   f["parent_path"],
                "last_modified": f["last_modified"],
                "approved":      False,
                "renamed":       False,
                "over30":        False,
            })

        generate_suggestions(rows)
        for r in rows:
            r["over30"] = len(r["suggested_name"]) > 30

        sess['files'] = rows
        state.update({
            "status":   "done",
            "message":  f"Scan complete — {len(rows):,} files found",
            "progress": len(rows),
            "total":    len(rows),
        })

    except Exception as e:
        state.update({"status": "error", "message": str(e)})


@app.post("/api/scan")
def start_scan(config: ScanConfig, background_tasks: BackgroundTasks,
               x_session_id: Optional[str] = Header(None)):
    sess = get_session(x_session_id)
    if sess['scan_state'].get('status') == 'running':
        raise HTTPException(400, "Scan already running")
    background_tasks.add_task(_do_scan, x_session_id, config)
    return {"ok": True}


@app.get("/api/scan/status")
def scan_status(x_session_id: Optional[str] = Header(None)):
    sess = get_session(x_session_id)
    return sess['scan_state']


# ── Files ──────────────────────────────────────────────────────────────────────

@app.get("/api/files")
def list_files(
    folder: Optional[str] = None,
    search: Optional[str] = None,
    approved: Optional[bool] = None,
    over30: Optional[bool] = None,
    offset: int = 0,
    limit: int = 100,
    x_session_id: Optional[str] = Header(None),
):
    sess  = get_session(x_session_id)
    rows  = sess['files']

    if folder:
        rows = [r for r in rows if r['folder_path'].startswith('/' + folder.strip('/'))]
    if search:
        s = search.lower()
        rows = [r for r in rows if s in r['original_name'].lower() or s in r['suggested_name'].lower()]
    if approved is not None:
        rows = [r for r in rows if r['approved'] == approved]
    if over30 is not None:
        rows = [r for r in rows if r['over30'] == over30]

    total = len(rows)
    return {"total": total, "rows": rows[offset:offset + limit]}


@app.get("/api/files/folders")
def list_folders(x_session_id: Optional[str] = Header(None)):
    sess   = get_session(x_session_id)
    counts = {}
    for r in sess['files']:
        top = r['folder_path'].lstrip('/').split('/')[0]
        if top not in counts:
            counts[top] = {"top_folder": top, "file_count": 0, "approved_count": 0}
        counts[top]["file_count"] += 1
        if r['approved']:
            counts[top]["approved_count"] += 1
    return sorted(counts.values(), key=lambda x: x['top_folder'])


@app.get("/api/files/stats")
def file_stats(x_session_id: Optional[str] = Header(None)):
    sess  = get_session(x_session_id)
    files = sess['files']
    return {
        "total":      len(files),
        "approved":   sum(1 for r in files if r['approved']),
        "renamed":    sum(1 for r in files if r['renamed']),
        "over30":     sum(1 for r in files if r['over30'] and not r['renamed']),
        "temp_files": sum(1 for r in files if r['suggested_name'] == 'DELETE - Temp File'),
    }


class UpdateName(BaseModel):
    suggested_name: str

@app.patch("/api/files/{item_id}")
def update_file(item_id: str, body: UpdateName, x_session_id: Optional[str] = Header(None)):
    sess = get_session(x_session_id)
    for r in sess['files']:
        if r['item_id'] == item_id:
            r['suggested_name'] = body.suggested_name
            r['over30'] = len(body.suggested_name) > 30
            return {"ok": True}
    raise HTTPException(404, "File not found")


class ApproveBody(BaseModel):
    item_ids: Optional[List[str]] = None
    folder:   Optional[str] = None
    approved: bool = True

@app.post("/api/files/approve")
def approve(body: ApproveBody, x_session_id: Optional[str] = Header(None)):
    sess = get_session(x_session_id)
    for r in sess['files']:
        if body.folder and r['folder_path'].startswith('/' + body.folder.strip('/')):
            r['approved'] = body.approved
        elif body.item_ids and r['item_id'] in body.item_ids:
            r['approved'] = body.approved
    return {"ok": True}


# ── Rename ─────────────────────────────────────────────────────────────────────

def _rename_item(token, drive_id, item_id, new_name, retries=3):
    url     = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for attempt in range(retries):
        try:
            resp = requests.patch(url, headers=headers, json={"name": new_name}, timeout=30)
            if resp.status_code == 200:
                return True, ""
            if resp.status_code == 429:
                time.sleep(int(resp.headers.get("Retry-After", 10)))
                continue
            return False, f"HTTP {resp.status_code}: {resp.text[:150]}"
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                return False, str(e)
    return False, "Max retries exceeded"

def _extract_drive_id(parent_path):
    m = re.search(r'/drives/([^/]+)/', parent_path)
    return m.group(1) if m else None

def _do_rename(session_id: str, folder: str):
    sess = _sessions.get(session_id)
    if not sess:
        return
    state = sess['rename_state']
    token = sess['token']

    targets = [
        r for r in sess['files']
        if r['folder_path'].startswith('/' + folder.strip('/'))
        and r['approved']
        and not r['renamed']
        and r['suggested_name'] != r['original_name']
        and r['suggested_name'] != 'DELETE - Temp File'
    ]

    state.update({"status": "running", "done": 0, "total": len(targets), "errors": 0,
                  "message": f"Renaming {len(targets)} files..."})

    for row in targets:
        new_name = row['suggested_name'] + row['extension']
        drive_id = _extract_drive_id(row['parent_path'])
        if not drive_id:
            ok, err = False, "Could not extract drive ID"
        else:
            ok, err = _rename_item(token, drive_id, row['item_id'], new_name)
        if ok:
            row['renamed'] = True
        else:
            state['errors'] += 1
        state['done'] += 1
        state['message'] = f"Renamed {state['done']}/{len(targets)}"
        time.sleep(0.15)

    errors = state['errors']
    state.update({
        "status":  "done",
        "message": f"Done — {state['done'] - errors} succeeded, {errors} failed"
    })


class RenameConfig(BaseModel):
    folder: str

@app.post("/api/rename")
def start_rename(config: RenameConfig, background_tasks: BackgroundTasks,
                 x_session_id: Optional[str] = Header(None)):
    sess = get_session(x_session_id)
    if not sess.get('write_access'):
        raise HTTPException(403, "Write access required. Please sign in again with full access.")
    if sess['rename_state'].get('status') == 'running':
        raise HTTPException(400, "Rename already running")
    background_tasks.add_task(_do_rename, x_session_id, config.folder)
    return {"ok": True}


@app.get("/api/rename/status")
def rename_status(x_session_id: Optional[str] = Header(None)):
    sess = get_session(x_session_id)
    return sess['rename_state']
