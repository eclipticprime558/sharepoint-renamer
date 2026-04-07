# FileForge — SharePoint File Renamer

A web-based tool for bulk-renaming files in a SharePoint document library. Upload your own Azure App Registration, scan a library, review AI-suggested names in a spreadsheet-style interface, and apply renames — all from the browser.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-latest-green) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## How It Works

The app walks you through six steps on a single scrolling page:

| Step | What happens |
|------|-------------|
| **1 · Azure Setup** | Register an app in Azure AD and grant Graph API permissions |
| **2 · Connect** | Enter your Client ID and sign in with your Microsoft 365 account |
| **3 · Configure** | Set your site URL, library name, and naming rules |
| **4 · Scan** | FileForge recursively walks your SharePoint library |
| **5 · Review** | Inspect and approve suggested names in a spreadsheet-style table |
| **6 · Rename** | Apply approved renames folder by folder |

---

## Features

- **Intelligent naming engine** — title case, word abbreviations (Report→Rpt, Meeting→Mtg), CamelCase splitting, date normalization (moved to end in MM.DD.YY format), filler word removal
- **Spreadsheet preview** — sortable, filterable table with inline name editing and character count indicators
- **Copy for Claude** — formats unapproved files as a structured prompt you can paste into [claude.ai](https://claude.ai) for AI name suggestions
- **Customizable rules** — set character target, toggle individual rules, add your own acronyms, abbreviations, and org name replacements
- **Two auth tiers** — sign in read-only to scan and review, or read+write to apply renames
- **Safe by default** — requires explicit approval per file; SharePoint version history preserves original names

---

## Azure App Registration

You need a Microsoft 365 admin account to set this up once. The app walks you through each step, but the short version:

1. Go to **portal.azure.com** → App registrations → New registration
2. Copy the **Application (client) ID**
3. Add API permissions (Microsoft Graph → Delegated):
   - Scan only: `Sites.Read.All` + `Files.Read.All`
   - Scan + rename: `Sites.ReadWrite.All` + `Files.ReadWrite.All`
4. Grant admin consent
5. Add this app's URL as a **Single-page application** redirect URI under Authentication

---

## Self-Hosting

### Requirements

- Python 3.11+
- A Microsoft 365 tenant with SharePoint

### Run Locally

```bash
git clone https://github.com/eclipticprime558/sharepoint-renamer.git
cd sharepoint-renamer
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

### Deploy to Render

The repo includes a `render.yaml` for one-click deploy:

1. Fork this repo
2. Go to [dashboard.render.com](https://dashboard.render.com) → New → Blueprint
3. Connect your fork — Render reads `render.yaml` automatically

The service name is `sharepoint-renamer` and runs on a free tier web service.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Auth | MSAL.js (Microsoft Authentication Library) |
| Graph API | Microsoft Graph v1.0 |
| Frontend | Vanilla JS + Bootstrap 5 |
| Session store | In-memory (4-hour TTL) |
| Hosting | Render |

---

## Naming Rules

The engine applies these transformations in order:

1. Strip embedded extensions (`.pdf`, `.docx` in filename body)
2. Apply custom org name replacements (user-defined)
3. Protect software names (QuickBooks, PowerPoint)
4. Extract and normalize dates → moved to end as `MM.DD.YY`
5. Split CamelCase words
6. Remove hyphens, underscores, duplicate markers `(1)`, and `FINAL`
7. Apply title case (with acronym and lowercase-word preservation)
8. Apply word abbreviations (100+ built-in, plus user additions)
9. Strip filler words (`of`, `the`, `for`…) if name still exceeds target length
10. Append date suffix

Temp/lock files (`~$` prefix) are flagged as `DELETE - Temp File` rather than renamed.

---

## Security Notes

- Access tokens are never persisted to disk or database — sessions are in-memory only
- All Graph API calls use delegated (user) permissions, not app-only
- Read-only sign-in cannot write to SharePoint regardless of server state
- Sessions expire after 4 hours of inactivity
