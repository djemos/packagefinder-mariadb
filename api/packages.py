#!/usr/bin/env python3

import json
import urllib.parse
import os
import sys
from pathlib import Path

# Έλεγχος και φιλτράρισμα αυτοματοποιημένων bots / scanners
user_agent = os.environ.get('HTTP_USER_AGENT', '').lower()
bad_agents = ['curl', 'wget', 'python', 'perl', 'libwww', 'go-http', 'scanner', 'bot', 'spider']

if not user_agent or any(agent in user_agent for agent in bad_agents):
    # Επιστρέφουμε έγκυρο header στον Apache για να μην βγάλει 500 Internal Server Error
    print("Content-Type: text/html\n")
    print("Access Denied: Automated tools are not allowed.")
    sys.exit(0)

BASE = Path("/srv/httpd/htdocs/packagefinder")
PACKAGES_FILE = BASE / "data/packages.json"
REPOS_FILE = BASE / "data/repositories.json"

print("Content-Type: application/json; charset=utf-8")
print()

# 1. ΑΣΦΑΛΗΣ ΦΟΡΤΩΣΗ ΑΡΧΕΙΩΝ
try:
    with open(REPOS_FILE, encoding="utf-8") as f:
        repositories = json.load(f)
    with open(PACKAGES_FILE, encoding="utf-8") as f:
        packages = json.load(f)
except Exception as e:
    print(json.dumps({"error": f"Database error: {str(e)}"}, ensure_ascii=False))
    sys.exit(1)

# Lookup tables
repo_urls = {}
repo_ids = {}
repo_distros = {}  # Νέο lookup table για τη σωστή έκδοση διανομής
repo_briefs = {}   # Νέο lookup table για το πεδίο brief από τη βάση δεδομένων
for r in repositories:
    if isinstance(r, dict) and "name" in r:
        repo_urls[r["name"]] = r.get("url", "")
        repo_ids[r["name"]] = r.get("id", "")
        repo_distros[r["name"]] = r.get("slackware_version", "mixed")
        repo_briefs[r["name"]] = r.get("brief", "") # Αποθήκευση του Brief ονόματος

# 2. ΑΣΦΑΛΗΣ ΛΗΨΗ ΠΑΡΑΜΕΤΡΩΝ URL (Προσθήκη distro για το φίλτρο του μενού)
try:
    query = urllib.parse.parse_qs(os.environ.get("QUERY_STRING", ""))
    q = query.get("q", [""])[0].lower().strip()
    repo = query.get("repo", [""])[0].strip()
    arch = query.get("arch", ["all"])[0].lower().strip()
    search_type = query.get("type", ["name"])[0].lower().strip()
    # Λήψη της επιλεγμένης έκδοσης από το μενού/radio buttons (π.χ. "15.0", "14.2", "current", "all")
    distro_filter = query.get("distro", ["all"])[0].lower().strip()
except Exception:
    q, repo, arch, search_type, distro_filter = "", "", "all", "name", "all"

# 3. ΕΝΙΑΙΟΣ ΒΡΟΧΟΣ ΕΠΕΞΕΡΓΑΣΙΑΣ, ΦΙΛΤΡΑΡΙΣΜΑΤΟΣ ΚΑΙ ΥΠΟΛΟΓΙΣΜΟΥ (SINGLE PASS)
final_packages = []
seen_filenames = set()

# Προετοιμασία λέξεων-κλειδιών αναζήτησης
distro_keywords = [
    "current", "15.0", "14.2", "14.1", "14.0", 
    "salix", "slackel", "official", "slackware", "slackware64", "mixed"
]
clean_q = q.replace("-", " ") if q else ""
search_words = clean_q.split()

active_distro_filters = [w for w in search_words if w in distro_keywords]
package_search_words = [w for w in search_words if w not in distro_keywords]

for p in packages:
    if not isinstance(p, dict):
        continue

    # --- Α. ΜΑΡΠΑΡΙΣΜΑ & ΚΑΝΟΝΙΚΟΠΟΙΗΣΗ ΔΕΔΟΜΕΝΩΝ ---
    raw_repo = p.get("repository", "")
    p_package = p.get("package", "")
    p_arch = p.get("arch", "")
    raw_repo_lower = str(raw_repo).lower()

    if "slackel" in raw_repo_lower:
        p["clean_repo"] = "slackel"
        p["clean_distro"] = p["distro"] = "current"
        p["repository"] = "Slackel"
        p["is_official"] = False
    elif "slackware" in raw_repo_lower:
        p["clean_repo"] = "official"
        p["repository"] = "Official"
        p["is_official"] = True
        
        if "current" in raw_repo_lower: p["clean_distro"] = p["distro"] = "current"
        elif "15.0" in raw_repo_lower: p["clean_distro"] = p["distro"] = "15.0"
        elif "14.2" in raw_repo_lower: p["clean_distro"] = p["distro"] = "14.2"
        elif "14.1" in raw_repo_lower: p["clean_distro"] = p["distro"] = "14.1"
        elif "14.0" in raw_repo_lower: p["clean_distro"] = p["distro"] = "14.0"
        else: p["clean_distro"] = p["distro"] = "current"
    elif "salix" in raw_repo_lower:
        p["clean_repo"] = "salix"
        p["repository"] = "Salix"
        p["is_official"] = False
        
        # ΕΔΩ ΕΓΙΝΕ Η ΔΙΟΡΘΩΣΗ: Έλεγχος τόσο για "14.2" όσο και για "142" για σωστή ανίχνευση του Salix Extra
        if "15.0" in raw_repo_lower or "150" in raw_repo_lower: 
            p["clean_distro"] = p["distro"] = "15.0"
        elif "14.2" in raw_repo_lower or "142" in raw_repo_lower: 
            p["clean_distro"] = p["distro"] = "14.2"
        elif "14.1" in raw_repo_lower or "141" in raw_repo_lower: 
            p["clean_distro"] = p["distro"] = "14.1"
        elif "14.0" in raw_repo_lower or "140" in raw_repo_lower: 
            p["clean_distro"] = p["distro"] = "14.0"
        else: 
            p["clean_distro"] = p["distro"] = "15.0"
    else:
        p["clean_repo"] = "mixed"
        actual_distro = repo_distros.get(raw_repo, "mixed")
        p["clean_distro"] = p["distro"] = actual_distro
        
        db_brief = repo_briefs.get(raw_repo, "")
        p["repository"] = db_brief if db_brief else (raw_repo if raw_repo else "Unknown")
        p["is_official"] = False

    if isinstance(p_package, str) and "noarch" in p_package.lower():
        p["arch"] = "noarch"
    else:
        p["arch"] = p_arch if p_arch else "unknown"

    p["raw_repository"] = raw_repo
    p["repository_id"] = repo_ids.get(raw_repo, "")

    # --- Α2. ΑΚΑΡΙΑΙΟ ΦΙΛΤΡΑΡΙΣΜΑ ΜΕΣΩ ΜΕΝΟΥ (RADIO BUTTONS) ---
    # Κόβει αμέσως τις λάθος εκδόσεις πριν προχωρήσει η αναζήτηση
    if distro_filter and distro_filter != "all":
        if p["clean_distro"] != distro_filter:
            continue

    # --- Β. ΦΙΛΤΡΑΡΙΣΜΑ DROPDOWN / URL ---
    if repo and str(p.get("repository", "")) != repo:
        continue

    # --- Γ. ΦΙΛΤΡΑΡΙΣΜΑ ΑΡΧΙΤΕΚΤΟΝΙΚΗΣ ---
    if arch and arch != "all":
        p_arch_lower = p["arch"].lower()
        if arch == "i386":
            if p_arch_lower != "noarch" and not any(x in p_arch_lower for x in ["i386", "i486", "i586", "i686"]):
                continue
        elif arch == "x86_64":
            if p_arch_lower != "x86_64" and p_arch_lower != "noarch":
                continue
        elif arch == "noarch":
            if p_arch_lower != "noarch":
                continue
        else:
            if p_arch_lower != arch:
                continue

    # --- Δ. ΕΞΥΠΝΟ ΦΙΛΤΡΑΡΙΣΜΑ ΚΕΙΜΕΝΟΥ (SEARCH QUERY) ---
    if q:
        if active_distro_filters:
            match_distro = True
            has_repo_filter = any(rf in active_distro_filters for rf in ["slackel", "salix", "official", "slackware", "slackware64"])
            has_version_filter = any(vf in active_distro_filters for vf in ["current", "15.0", "14.2", "14.1", "14.0"])

            if has_repo_filter:
                repo_matched = False
                if "slackel" in active_distro_filters and p["clean_repo"] == "slackel":
                    repo_matched = True
                elif "salix" in active_distro_filters and p["clean_repo"] == "salix":
                    repo_matched = True
                elif any(x in active_distro_filters for x in ["official", "slackware", "slackware64"]) and p["clean_repo"] == "official":
                    repo_matched = True
                if not repo_matched:
                    match_distro = False
            if has_version_filter:
                version_matched = False
                for vf in ["current", "15.0", "14.2", "14.1", "14.0"]:
                    if vf in active_distro_filters and p["clean_distro"] == vf:
                        version_matched = True
                if not version_matched:
                    match_distro = False

            if not match_distro:
                continue
        # 2. Φίλτρο Λέξεων Πακέτου
        if package_search_words:
            if search_type == "description":
                text_to_search = str(p.get("description", ""))
            elif search_type == "filename":
                text_to_search = str(p.get("package", ""))
            else:
                text_to_search = f"{p.get('name', '')} {p.get('version', '')}"
            text_to_search = text_to_search.lower()

            if not all(word in text_to_search for word in package_search_words):
                continue
    # --- Ε. ΕΛΕΓΧΟΣ ΜΟΝΑΔΙΚΟΤΗΤΑΣ (ΔΙΠΛΟΤΥΠΑ) ---
    filename_key = p.get("package", "")
    if filename_key:
        unique_file_key = (filename_key, p["clean_repo"], p["clean_distro"], p["arch"])
        if unique_file_key in seen_filenames:
            continue
        seen_filenames.add(unique_file_key)
    else:
        fallback_key = (p.get("name"), p.get("version"), p["repository_id"], p["clean_distro"], p["arch"])
        if fallback_key in seen_filenames:
            continue
        seen_filenames.add(fallback_key)

    # --- ΣΤ. ΥΠΟΛΟΓΙΣΜΟΣ URLs & RANKING ---
    base_url = repo_urls.get(raw_repo, "")
    location_clean = str(p.get("location", "")).replace("./", "").rstrip("/")
    p["location"] = location_clean if location_clean else "unknown"

    if base_url:
        p["download"] = f"{base_url.rstrip('/')}/{location_clean}/{p.get('package', '')}"
        p["location_url"] = f"{base_url.rstrip('/')}/{location_clean}/"
    else:
        p["download"] = ""
        p["location_url"] = ""

    if p["is_official"] and not p.get("distro"):
        p["distro"] = "current"

    # Υπολογισμός Rank σχετικότητας
    rank = 0.0
    if q:
        if q in ["current", "15.0", "14.2", "14.1", "14.0", "salix", "slackel", "official", "slackware", "slackware64", "mixed"]:
            rank = 1.0 if p["is_official"] else 2.0
        else:
            name = str(p.get("name", "")).lower()
            version = str(p.get("version", "")).lower()
            package = str(p.get("package", "")).lower()
            desc = str(p.get("description", "")).lower()

            if name == q or q in package: rank = 10.0
            elif name.startswith(q): rank = 8.0
            elif q in name: rank = 6.0
            elif q in version: rank = 5.0
            elif q in desc: rank = 3.0

    p["rank"] = rank
    p["size"] = p.get("size", "N/A")

    # Κανονικοποίηση Requires
    raw_requires = p.get("requires")
    if isinstance(raw_requires, list):
        p["requires"] = [str(r).strip() for r in raw_requires if str(r).strip()]
    elif isinstance(raw_requires, str) and raw_requires.strip():
        p["requires"] = [r.strip() for r in raw_requires.replace(",", " ").split() if r.strip()]
    else:
        p["requires"] = []

    # ΚΑΘΟΛΙΚΗ ΑΝΤΙΚΑΤΑΣΤΑΣΗ ΜΕ BRIEF ΣΤΟ ΤΕΛΟΣ (Αφού πέρασαν όλα τα φίλτρα)
    final_brief = repo_briefs.get(raw_repo, "")
    if final_brief:
        p["repository"] = final_brief

    final_packages.append(p)

# 4. ΤΑΞΙΝΟΜΗΣΗ ΚΑΙ ΕΚΤΥΠΩΣΗ JSON
final_packages.sort(key=lambda x: x.get("rank", 0), reverse=True)
print(json.dumps(final_packages, indent=2, ensure_ascii=False))
