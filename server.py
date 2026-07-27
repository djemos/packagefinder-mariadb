#!/usr/bin/env python3

from flask import Flask, jsonify, request
from pathlib import Path
import json


BASE = Path("/srv/httpd/htdocs/slackware-browser")

PACKAGES_FILE = BASE / "data/packages.json"


app = Flask(__name__)


def load_packages():

    with open(PACKAGES_FILE, encoding="utf-8") as f:
        return json.load(f)



@app.route("/api/packages")
def packages():

    data = load_packages()

    query = request.args.get("q", "").lower()
    repo = request.args.get("repo", "")
    arch = request.args.get("arch", "")


    if query:
        data = [
            p for p in data
            if query in p["name"].lower()
            or query in p["description"].lower()
        ]


    if repo:
        data = [
            p for p in data
            if p["repository"] == repo
        ]


    if arch:
        data = [
            p for p in data
            if p["arch"] == arch
        ]


    return jsonify(data)



@app.route("/")
def index():

    return """
    <h1>Slackware / Slackel Package Browser</h1>
    <p>API:</p>
    <a href="/api/packages?q=firefox">
    Search firefox
    </a>
    """



if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080
    )
