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

try:
    with open(REPOS_FILE, encoding="utf-8") as f:
        repositories = json.load(f)

    with open(PACKAGES_FILE, encoding="utf-8") as f:
        packages = json.load(f)

except Exception as e:
    print(json.dumps({"error": f"Database load error: {str(e)}"}, ensure_ascii=False))
    sys.exit(1)


# Repository lookup tables
repo_urls = {r["name"]: r["url"] for r in repositories}
repo_ids = {r["name"]: r["id"] for r in repositories}

# Query parameters
query = urllib.parse.parse_qs(os.environ.get("QUERY_STRING", ""))

package_name = query.get("package", [""])[0]
repo_id = query.get("repo", [""])[0]

if not package_name:
    print(json.dumps({"error": "Missing package parameter"}, ensure_ascii=False))
    sys.exit(0)

found_package = None

for p in packages:
    # Έλεγχος αν το όνομα ταιριάζει
    if p.get("name") != package_name:
        continue

    rid = str(repo_ids.get(p["repository"], ""))
    
    # Αν έχει οριστεί repo_id στο URL, πρέπει να ταιριάζει και αυτό
    if repo_id and rid != str(repo_id):
        continue

    # Βρέθηκε το πακέτο, κρατάμε ένα αντίγραφο για επεξεργασία
    found_package = dict(p)
    found_package["repository_id"] = rid
    break

if not found_package:
    print(json.dumps({"error": f"Package '{package_name}' not found"}, ensure_ascii=False))
    sys.exit(0)

# Υπολογισμός URLs λήψης
base_url = repo_urls.get(found_package["repository"], "")
if base_url:
    location_clean = found_package["location"].replace("./", "").rstrip("/")
    found_package["download"] = f"{base_url.rstrip('/')}/{location_clean}/{found_package['package']}"
    found_package["location_url"] = f"{base_url.rstrip('/')}/{location_clean}/"
else:
    found_package["download"] = ""
    found_package["location_url"] = ""

# Εύρεση των πλήρων metadata του Repository (repository_info)
found_package["repository_info"] = {}
for r in repositories:
    if str(r["id"]) == found_package["repository_id"]:
        found_package["repository_info"] = r
        break

# Κανονικοποίηση Distro
repo_name = found_package["repository"]
if repo_name in ("Slackel x86_64", "Slackel i486"):
    found_package["repository"] = "Slackel"
    found_package["distro"] = "current"
elif repo_name in ("Slackware64 current", "Slackware current"):
    found_package["repository"] = "Official"
    found_package["distro"] = "current"
elif repo_name in ("Salix x86_64", "Salix i486"):
    found_package["repository"] = "Salix"
    found_package["distro"] = "15.0"
else:
    found_package["distro"] = "mixed"

# Διασφάλιση ύπαρξης των πεδίων για το UI
found_package["size"] = found_package.get("size", "N/A")
found_package["dependencies"] = found_package.get("requires", [])
found_package["required_by"] = []

# Εκτύπωση ΕΝΟΣ ΚΑΙ ΜΟΝΑΔΙΚΟΥ έγκυρου JSON αντικειμένου
print(json.dumps(found_package, indent=2, ensure_ascii=False))
