#!/usr/bin/env python3

import json
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
REPOS_FILE = BASE / "data/repositories.json"


print("Content-Type: application/json; charset=utf-8")
print()


try:
    with open(REPOS_FILE, encoding="utf-8") as f:
        repos = json.load(f)

except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)


repo_id = os.environ.get("QUERY_STRING", "")

# example: id=26
repo_id = repo_id.replace("id=", "")


for r in repos:

    if str(r.get("id")) == repo_id:
        print(json.dumps(
            r,
            indent=2,
            ensure_ascii=False
        ))
        sys.exit(0)


print(json.dumps({
    "error": "repository not found"
}))
