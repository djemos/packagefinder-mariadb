#!/usr/bin/env python3

import json
import urllib.request
import urllib.parse
import bz2
import os
from pathlib import Path
import sys

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

query = urllib.parse.parse_qs(
    os.environ.get("QUERY_STRING", "")
)

package = query.get("package", [""])[0]
repo_id = str(query.get("repo", [""])[0])

if not package or not repo_id:
    print(json.dumps({
        "count": 0,
        "files": []
    }))
    raise SystemExit

repos = json.loads(REPOS_FILE.read_text(encoding="utf-8"))

repo = None

for r in repos:
    if str(r["id"]) == repo_id:
        repo = r
        break

if repo is None:
    print(json.dumps({
        "count": 0,
        "files": []
    }))
    raise SystemExit

if repo.get("file_list") in (None, "", "unsupported"):
    print(json.dumps({
        "count": 0,
        "files": []
    }))
    raise SystemExit

manifest_url = (
    repo["url"].rstrip("/")
    + "/"
    + repo["file_list"]
)

try:

    with urllib.request.urlopen(manifest_url) as response:
        data = response.read()

    if manifest_url.endswith(".bz2"):
        data = bz2.decompress(data)

    text = data.decode(
        "utf-8",
        errors="ignore"
    )

except Exception:

    print(json.dumps({
        "count": 0,
        "files": []
    }))
    raise SystemExit

pkg = package

files = []
inside = False

for line in text.splitlines():

    if line.startswith("||   Package:"):

        current = line.split("Package:", 1)[1].strip()

        # ./xap/package.txz -> package.txz
        current_pkg = current.split("/")[-1]

        inside = (current_pkg == pkg)

        continue

    if not inside:
        continue

    line = line.strip()

    if not line:
        continue

    if line.startswith("++") or line.startswith("||"):
        continue

    parts = line.split()

    if len(parts) >= 6:
        path = parts[-1]

        if path != "./" and not path.endswith("/"):
            files.append(path)
        
print(json.dumps(
    {
        "count": len(files),
        "files": files
    },
    indent=2,
    ensure_ascii=False
))
