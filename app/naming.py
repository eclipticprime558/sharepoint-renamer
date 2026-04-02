"""
Naming rules module — adapted from suggest_names.py
"""
import re
from collections import defaultdict

ACRONYMS = {
    "SOAR", "DV", "SSA", "CJ", "CTH", "VSP", "SARAH", "OLC", "SSI", "SSDI",
    "SSISSDI", "CE", "PH", "SS", "PR", "CV", "HUD", "VA", "FAQ", "FY",
    "SPA", "MOU", "MOA", "RFP", "RFQ", "HR", "IT", "ID", "TB", "RRH",
    "HMIS", "ESG", "SAMM", "TDCHA", "HHS", "COC", "PIT", "LMHA", "DSHS",
    "PATH", "SSVF", "GPD", "HCV", "PSH", "TH", "VASH", "PHA", "CEO", "CFO",
    "COO", "CTO", "508", "ESNAPS", "TX", "SNOFO", "PG", "APR", "DEC", "JAN",
    "FEB", "MAR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV",
    "ALTFUND", "CoC", "COC", "COSA", "PBC", "AR", "AP", "GL", "PO", "W9",
    "YHDP", "NOFA", "BOD", "MHP", "UFA", "TWC", "TDHCA", "DSHS",
    "AAB", "ACAC", "DIS", "HDAC", "HRSAC", "HSPAB", "ISS", "LEAB",
    "OA", "PHP", "YAB", "YYA", "PS", "SSRG", "NHSDC", "SAM",
    "NPI", "EIN", "IRS", "ACH", "NACHA", "PPP", "SBA", "CARES",
}

PRESERVE_EXACT = {
    "esnaps":     "eSNAPS",
    "quickbooks": "QuickBooks",
    "quickbook":  "QuickBooks",
    "coc":        "CoC",
    "cocs":       "CoCs",
}

LOWERCASE_WORDS = {
    "a", "an", "the", "and", "but", "or", "for", "nor", "on", "at",
    "to", "by", "in", "of", "up", "as", "is", "it", "with",
}

_DATE_SINGLE   = r'\d{1,2}[._]\d{1,2}[._]\d{2,4}'
DATE_RANGE_RE  = re.compile(rf'({_DATE_SINGLE})\s*(?:to|-)\s*({_DATE_SINGLE})', re.IGNORECASE)
DATE_SINGLE_RE = re.compile(rf'\b({_DATE_SINGLE})\b')
MMDDYY_RE      = re.compile(r'\b(0[1-9]|1[0-2])([0-3]\d)(1[6-9]|2[0-9])\b')
FY_RANGE_RE    = re.compile(r'\b(20[1-2]\d)-(20[1-2]\d)\b')
YEAR_RE        = re.compile(r'\b(20[1-2]\d)\b')

ORG_REPLACEMENTS = [
    (r'\bSouth\s+Alamo\s+Regional\s+Alliance(?:\s+for\s+(?:the\s+)?Homeless(?:ness)?)?\b', 'SARAH'),
    (r'\bClose\s+to\s+Home\b',                   'CTH'),
    (r'\bCity\s+of\s+San\s+Antonio\b',           'COSA'),
    (r'\bSan\s+Antonio\s+Housing\s+Authority\b', 'SAHA'),
    (r'\bDepartment\s+of\s+Housing\s+and\s+Urban\s+Development\b', 'HUD'),
]

WORD_ABBREVS = {
    "Accounts": "Accts", "Account": "Acct",
    "Agreements": "Agmts", "Agreement": "Agmt",
    "Allocations": "Allocs", "Allocation": "Alloc",
    "Amendments": "Amnds", "Amendment": "Amnd",
    "Applications": "Apps", "Application": "App",
    "Assessments": "Assmts", "Assessment": "Assmt",
    "Attachments": "Attch", "Attachment": "Attch",
    "Authorization": "Auth", "Authorized": "Auth",
    "Budgets": "Budgs", "Budget": "Budg",
    "Calculations": "Calcs", "Calculation": "Calc",
    "Certificates": "Certs", "Certificate": "Cert",
    "Checklists": "Chklsts", "Checklist": "Chklst",
    "Communications": "Comms", "Communication": "Comm",
    "Compensation": "Comp", "Compliance": "Compl",
    "Conferences": "Confs", "Conference": "Conf",
    "Contractors": "Cntrs", "Contractor": "Cntr",
    "Contracts": "Cntrcts", "Contract": "Cntrct",
    "Contributions": "Contribs", "Contribution": "Contrib",
    "Coordinators": "Coords", "Coordinator": "Coord",
    "Departments": "Depts", "Department": "Dept",
    "Descriptions": "Descs", "Description": "Desc",
    "Development": "Dev",
    "Documents": "Docs", "Document": "Doc",
    "Employees": "Emps", "Employee": "Emp",
    "Evaluations": "Evals", "Evaluation": "Eval",
    "Expenditures": "Expends", "Expenditure": "Expend",
    "Expenses": "Exps",
    "Financial": "Fin", "Foundation": "Fdn",
    "Government": "Govt",
    "Guidelines": "Guidlns", "Guideline": "Guidln",
    "Housing": "Hsg",
    "Implementation": "Impl", "Information": "Info",
    "Invoices": "Invs", "Invoice": "Inv",
    "Letters": "Ltrs", "Letter": "Ltr",
    "Maintenance": "Maint", "Management": "Mgmt",
    "Meetings": "Mtgs", "Meeting": "Mtg",
    "Memorandum": "Memo",
    "National": "Natl",
    "Notifications": "Notifs", "Notification": "Notif",
    "Operations": "Ops",
    "Organizations": "Orgs", "Organization": "Org",
    "Payments": "Pymts", "Payment": "Pymt",
    "Payable": "Pybl", "Performance": "Perf",
    "Presentations": "Pres", "Presentation": "Pres",
    "Procedures": "Procs", "Procedure": "Proc",
    "Proposals": "Props", "Proposal": "Prop",
    "Quarterly": "Qtrly",
    "Receivable": "Rcvbl",
    "References": "Refs", "Reference": "Ref",
    "Registration": "Reg", "Reimbursement": "Reimb",
    "Reports": "Rpts", "Report": "Rpt",
    "Requirements": "Reqmts", "Requirement": "Reqmt",
    "Requests": "Reqs", "Request": "Req",
    "Schedules": "Scheds", "Schedule": "Sched",
    "Services": "Svcs", "Service": "Svc",
    "Signatures": "Sigs", "Signature": "Sig",
    "Specifications": "Specs", "Specification": "Spec",
    "Statements": "Stmts", "Statement": "Stmt",
    "Submissions": "Subms", "Submission": "Subm",
    "Summaries": "Summs", "Summary": "Summ",
    "Templates": "Tmpls", "Template": "Tmpl",
    "Termination": "Term",
    "Transactions": "Trans", "Transaction": "Trans",
    "Transitions": "Trans", "Transition": "Trans",
    "Training": "Trng",
    "Transfers": "Xfers", "Transfer": "Xfer",
    "Updates": "Upds", "Update": "Upd",
    "Vendors": "Vndrs", "Vendor": "Vndr",
    "Verification": "Verif",
    "Volunteers": "Vols", "Volunteer": "Vol",
    "Worksheets": "Wkshts", "Worksheet": "Wksht",
}

FILLER_WORDS = {"of", "the", "for", "in", "with", "and", "a", "an", "by", "or", "to", "at"}

PREFIX_SHORTCUTS = [
    ("Homelink Project Transfer Memo", "Transfer Memo"),
    ("HUD RRH Transfer Memos",         "HUD RRH Memo"),
    ("SAMM ESG TDCHA RRH",             "SAMM ESG RRH"),
]


def fmt_date(raw):
    parts = re.split(r'[._]', raw)
    if len(parts) == 3:
        m, d, y = parts
        if len(y) == 4:
            y = y[2:]
        return f"{int(m):02d}.{int(d):02d}.{y}"
    return raw


def extract_dates(name):
    m = DATE_RANGE_RE.search(name)
    if m:
        d1, d2 = fmt_date(m.group(1)), fmt_date(m.group(2))
        return (name[:m.start()] + " " + name[m.end():]).strip(), f"{d1}-{d2}"
    m = DATE_SINGLE_RE.search(name)
    if m:
        date_str = fmt_date(m.group(1))
        cleaned = re.sub(r'[\s._\-]*' + re.escape(m.group(1)) + r'[\s._\-]*', ' ', name).strip()
        return cleaned, date_str
    m = MMDDYY_RE.search(name)
    if m:
        date_str = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
        cleaned = re.sub(r'[\s._\-]*' + re.escape(m.group(0)) + r'[\s._\-]*', ' ', name).strip()
        return cleaned, date_str
    m = FY_RANGE_RE.search(name)
    if m:
        cleaned = re.sub(r'[\s._\-]*' + re.escape(m.group(0)) + r'[\s._\-]*', ' ', name).strip()
        return cleaned, m.group(0)
    m = YEAR_RE.search(name)
    if m:
        cleaned = re.sub(r'[\s]*' + re.escape(m.group(0)) + r'[\s]*', ' ', name).strip()
        return cleaned, m.group(1)
    return name, ""


def split_camel_case(text):
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([A-Z]{2,})([A-Z][a-z])', r'\1 \2', text)
    return text


def title_case_word(word, position):
    low = word.lower()
    if low in PRESERVE_EXACT:
        return PRESERVE_EXACT[low]
    if re.match(r'^[A-Z]{1,4}\d+[A-Z0-9]*$', word):
        return word.upper()
    upper = word.upper()
    if upper == "QUICKBOOKS":
        return "QuickBooks"
    if upper in ACRONYMS:
        return upper
    if position > 0 and low in LOWERCASE_WORDS:
        return low
    if re.match(r'^\$[\d,]+[kKmMbB]$', word):
        return word[:-1] + word[-1].upper()
    return word.capitalize()


def apply_title_case(text):
    text = re.sub(r'\b([A-Z]{2,})#(\d+)', lambda m: m.group(1).upper() + '#' + m.group(2), text, flags=re.IGNORECASE)
    words = text.split()
    return " ".join(title_case_word(w, i) for i, w in enumerate(words))


def shorten_known_patterns(name):
    for long, short in PREFIX_SHORTCUTS:
        if name.lower().startswith(long.lower()):
            name = short + name[len(long):]
            break
    name = re.sub(r'[\s_]+\d{1,3}$', '', name).strip()
    return name


def clean_name(original):
    name = original

    if name.startswith("~$"):
        return "DELETE - Temp File"

    name = re.sub(r'\.(pdf|docx?|xlsx?|pptx?|csv|txt)\b', '', name, flags=re.IGNORECASE)

    for pattern, replacement in ORG_REPLACEMENTS:
        name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

    name = re.sub(r'\beSNAPS\b', 'ESNAPS', name, flags=re.IGNORECASE)
    name = re.sub(r'\be-snaps\b', 'ESNAPS', name, flags=re.IGNORECASE)
    name = re.sub(r'\be\s+snaps\b', 'ESNAPS', name, flags=re.IGNORECASE)
    name = re.sub(r'\bQuickBooks\b', 'QUICKBOOKS', name, flags=re.IGNORECASE)
    name = name.replace('CoCs', 'COCS').replace('CoC', 'COC')
    name = re.sub(r'\b(TX-\d+)\b', lambda m: m.group(1).replace('-', 'HYPHEN'), name)
    name = re.sub(r'\b(HMIS|SOAR|HUD|COC|ESG|RRH|SSVF|PATH|VASH|HCV|PSH)([(\[.])', r'\1 \2', name, flags=re.IGNORECASE)

    name, date_str = extract_dates(name)
    name = split_camel_case(name)
    name = re.sub(r'\s*-\s*', ' ', name)
    name = name.replace('_', ' ')
    name = name.replace('HYPHEN', '-')
    name = re.sub(r'\s*\(\d+\)\s*', ' ', name).strip()
    name = re.sub(r'\bFINAL\b', '', name, flags=re.IGNORECASE).strip()
    name = shorten_known_patterns(name)
    name = re.sub(r'^(and|or|the|a)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name).strip()
    name = apply_title_case(name)
    name = re.sub(r'\s+', ' ', name).strip()

    for word, abbrev in WORD_ABBREVS.items():
        name = re.sub(rf'\b{re.escape(word)}\b', abbrev, name)

    name = re.sub(r'\s+', ' ', name).strip()

    if len(name) > 30:
        words = name.split()
        filtered = [words[0]] + [w for w in words[1:] if w.lower() not in FILLER_WORDS]
        name = ' '.join(filtered)
        name = re.sub(r'\s+', ' ', name).strip()

    if date_str and name:
        name = f"{name} {date_str}"
    elif date_str:
        name = date_str

    return name


def extract_folder_path(raw_path):
    match = re.search(r'/root:(/.*)', raw_path)
    return match.group(1) if match else raw_path


def generate_suggestions(rows):
    """Apply clean_name to a list of row dicts. Returns rows with SuggestedName filled."""
    for row in rows:
        row['suggested_name'] = clean_name(row['original_name'])

    # Deduplicate
    name_counts = defaultdict(list)
    for i, row in enumerate(rows):
        if row['suggested_name'] == "DELETE - Temp File":
            continue
        key = (row['suggested_name'].lower(), row.get('extension', '').lower())
        name_counts[key].append(i)

    for key, indices in name_counts.items():
        if len(indices) > 1:
            for n, idx in enumerate(indices[1:], 1):
                rows[idx]['suggested_name'] = f"{rows[idx]['suggested_name']} ({n})"

    return rows
