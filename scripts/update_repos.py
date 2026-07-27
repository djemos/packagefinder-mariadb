#!/usr/bin/env python3

import json
import urllib.request
from pathlib import Path
import re

BASE = Path("/srv/httpd/htdocs/packagefinder")

REPOS_FILE = BASE / "data/repositories.json"
PACKAGES_FILE = BASE / "data/packages.json"

def split_package(filename):
    filename = filename.replace(".txz", "")
    parts = filename.rsplit("-", 3)

    if len(parts) == 4:
        return {
            "name": parts[0],
            "version": parts[1],
            "package_arch": parts[2],
            "build": parts[3]
        }

    return {
        "name": filename,
        "version": "",
        "package_arch": "",
        "build": ""
    }

def download(url):
    print("Downloading:", url)
    try:
        with urllib.request.urlopen(url) as response:
            # Ανάκτηση του Last-Modified header από τον server
            last_modified = response.headers.get("Last-Modified", "")
            text = response.read().decode("utf-8", errors="ignore")
            return text, last_modified
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return "", ""

def count_files(url):
    try:
        import bz2

        with urllib.request.urlopen(url) as response:
            data = response.read()

        if url.endswith(".bz2"):
            data = bz2.decompress(data)

        return len(data.decode(
            "utf-8",
            errors="ignore"
        ).splitlines())

    except Exception as e:
        print("File count error:", e)
        return 0
        
def parse_packages(text, repo):
    packages = []
    blocks = text.split("\n\n")

    for block in blocks:
        name = re.search(r"PACKAGE NAME:\s+(.+)", block)
        location = re.search(r"PACKAGE LOCATION:\s+(.+)", block)
        size = re.search(r"PACKAGE SIZE \(compressed\):\s+(.+)", block)

        if name:
            pkg = name.group(1).strip()
            info = split_package(pkg)
            
        description_lines = []
        requires_list = []

        for line in block.splitlines():
            if line.startswith("PACKAGE REQUIRED:"):
               deps = line.split(":",1)[1].strip()
               if deps:
                   requires_list = [
                       x.strip()
                       for x in deps.split(",")
                       if x.strip()
                   ]
            elif line.startswith("PACKAGE DESCRIPTION:"):
               continue
            elif name and line.startswith(info["name"] + ":"):
               text_desc = line.split(":",1)[1].rstrip()
               if text_desc:
                   description_lines.append(text_desc)

        if name:
            pkg = name.group(1).strip()
            info = split_package(pkg)

            packages.append(
                {
                    "repository": repo["name"],
                    "arch": info["package_arch"] if info["package_arch"] else repo["arch"],
                    "package": pkg,
                    "name": info["name"],
                    "version": info["version"],
                    "package_arch": info["package_arch"],
                    "build": info["build"],
                    "location": location.group(1).strip() if location else "",
                    "size": size.group(1).strip() if size else "",
                    "description": "\n".join(description_lines),
                    "requires": requires_list,
                }
            )

    return packages

def main():
    repos = json.loads(REPOS_FILE.read_text(encoding="utf-8"))
    all_packages = []

    for repo in repos:
        packages_url = repo["url"] + "PACKAGES.TXT"

        # Η download() επιστρέφει πλέον και την ημερομηνία
        text, last_modified_date = download(packages_url)

        packages = parse_packages(text, repo)

        # Αυτόματη ενημέρωση του αριθμού πακέτων
        repo["nr_packages"] = len(packages)
        
        # ΔΙΟΡΘΩΣΗ: Αποθήκευση της ημερομηνίας που επέστρεψε ο HTTP Server
        if last_modified_date:
            repo["last_update"] = last_modified_date

        if repo.get("file_list") and repo["file_list"] != "unsupported":
            file_url = repo["url"].rstrip("/") + "/" + repo["file_list"]
            repo["nr_files"] = count_files(file_url)
        else:
            repo["nr_files"] = 0
    
        print(
           repo["name"],
           ":",
           len(packages),
           "packages",
           "files:",
           repo["nr_files"],
           "updated:",
           repo.get("last_update", "Unknown")
        )

        all_packages.extend(packages)

    REPOS_FILE.write_text(
        json.dumps(repos, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    PACKAGES_FILE.write_text(
        json.dumps(all_packages, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print()
    print("Total packages:", len(all_packages))
   
if __name__ == "__main__":
    main()
