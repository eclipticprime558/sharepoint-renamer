"""
Naming rules module — adapted from suggest_names.py
"""
import re
from collections import defaultdict

ACRONYMS = {
    # Generic business / finance
    "CEO", "CFO", "COO", "CTO", "CIO", "VP", "SVP", "EVP",
    "HR", "IT", "ID", "FAQ", "FY", "Q1", "Q2", "Q3", "Q4",
    "MOU", "MOA", "RFP", "RFQ", "SPA", "NDA", "SLA", "SOW",
    "AR", "AP", "GL", "PO", "W9", "EIN", "IRS", "ACH",
    "US", "USA", "UK", "EU", "UN",
    # Months (for date parsing)
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
    # Software / tech
    "PDF", "XLS", "CSV", "PPT", "URL", "API",
}

PRESERVE_EXACT = {
    "quickbooks": "QuickBooks",
    "quickbook":  "QuickBooks",
    "powerpoint": "PowerPoint",
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

ORG_REPLACEMENTS = []  # Populated at runtime from user-supplied custom_org_replacements

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

PREFIX_SHORTCUTS = []  # Reserved for future user-defined shortcuts


def _merge_rules(rules):
    """Merge custom rules dict into module-level defaults, return merged copies."""
    import copy
    acronyms = set(ACRONYMS)
    abbrevs  = dict(WORD_ABBREVS)
    org_reps = list(ORG_REPLACEMENTS)
    if not rules:
        return acronyms, abbrevs, org_reps, 30, True, True, True, True
    for a in rules.get('custom_acronyms', []):
        if a.strip():
            acronyms.add(a.strip().upper())
    for k, v in rules.get('custom_abbrevs', {}).items():
        if k.strip() and v.strip():
            abbrevs[k.strip()] = v.strip()
    for pair in rules.get('custom_org_replacements', []):
        if len(pair) == 2 and pair[0].strip() and pair[1].strip():
            org_reps.insert(0, (re.escape(pair[0].strip()), pair[1].strip()))
    target      = int(rules.get('target_length', 30))
    title_case  = bool(rules.get('title_case', True))
    rm_fillers  = bool(rules.get('remove_fillers', True))
    split_cc    = bool(rules.get('split_camelcase', True))
    norm_dates  = bool(rules.get('normalize_dates', True))
    return acronyms, abbrevs, org_reps, target, title_case, rm_fillers, split_cc, norm_dates


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


def title_case_word(word, position, acronyms):
    low = word.lower()
    if low in PRESERVE_EXACT:
        return PRESERVE_EXACT[low]
    if re.match(r'^[A-Z]{1,4}\d+[A-Z0-9]*$', word):
        return word.upper()
    upper = word.upper()
    if upper == "QUICKBOOKS":
        return "QuickBooks"
    if upper in acronyms:
        return upper
    if position > 0 and low in LOWERCASE_WORDS:
        return low
    if re.match(r'^\$[\d,]+[kKmMbB]$', word):
        return word[:-1] + word[-1].upper()
    return word.capitalize()


def apply_title_case(text, acronyms):
    text = re.sub(r'\b([A-Z]{2,})#(\d+)', lambda m: m.group(1).upper() + '#' + m.group(2), text, flags=re.IGNORECASE)
    words = text.split()
    return " ".join(title_case_word(w, i, acronyms) for i, w in enumerate(words))


def shorten_known_patterns(name):
    for long, short in PREFIX_SHORTCUTS:
        if name.lower().startswith(long.lower()):
            name = short + name[len(long):]
            break
    name = re.sub(r'[\s_]+\d{1,3}$', '', name).strip()
    return name


def clean_name(original, _rules_tuple=None):
    if _rules_tuple is None:
        acronyms, abbrevs, org_reps, target, title_case, rm_fillers, split_cc, norm_dates = _merge_rules(None)
    else:
        acronyms, abbrevs, org_reps, target, title_case, rm_fillers, split_cc, norm_dates = _rules_tuple

    name = original

    if name.startswith("~$"):
        return "DELETE - Temp File"

    name = re.sub(r'\.(pdf|docx?|xlsx?|pptx?|csv|txt)\b', '', name, flags=re.IGNORECASE)

    for pattern, replacement in org_reps:
        name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

    name = re.sub(r'\bQuickBooks\b', 'QUICKBOOKS', name, flags=re.IGNORECASE)
    name = re.sub(r'\bPowerPoint\b', 'POWERPOINT', name, flags=re.IGNORECASE)

    if norm_dates:
        name, date_str = extract_dates(name)
    else:
        date_str = ""

    if split_cc:
        name = split_camel_case(name)

    name = re.sub(r'\s*-\s*', ' ', name)
    name = name.replace('_', ' ')
    name = name.replace('HYPHEN', '-')
    name = re.sub(r'\s*\(\d+\)\s*', ' ', name).strip()
    name = re.sub(r'\bFINAL\b', '', name, flags=re.IGNORECASE).strip()
    name = shorten_known_patterns(name)
    name = re.sub(r'^(and|or|the|a)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name).strip()

    if title_case:
        name = apply_title_case(name, acronyms)
    name = re.sub(r'\s+', ' ', name).strip()

    for word, abbrev in abbrevs.items():
        name = re.sub(rf'\b{re.escape(word)}\b', abbrev, name)

    name = re.sub(r'\s+', ' ', name).strip()

    if rm_fillers and len(name) > target:
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


def generate_suggestions(rows, rules=None):
    """Apply clean_name to a list of row dicts. Returns rows with SuggestedName filled."""
    merged = _merge_rules(rules)
    acronyms, abbrevs, org_reps, target, title_case, rm_fillers, split_cc, norm_dates = merged

    for row in rows:
        row['suggested_name'] = clean_name(row['original_name'], _rules_tuple=merged)

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

    for r in rows:
        r["over30"] = len(r["suggested_name"]) > target

    return rows
