#!/usr/bin/python

import json
import os
import subprocess
import re
from pprint import pprint
import email.utils

directory = "crates"
repo_dir = "repos"

modules = {}
# list of crates we couldn't check
modules["nocheck_crates"] = []
modules["crates"] = {}

# canonify repo URLs
def clean_url(url):
    url = url.replace(".git", "").rstrip("/")
    regex = r'(https?|git):/?/?(github\.com|gitlab\.com)/(.+)/(.+)'
    search = re.search(regex, url)

    if search:
        new_url = "https://"+search.group(2)+"/"+search.group(3)+"/"+search.group(4)
        return new_url.lower()
    else:
        return url

for crate in os.listdir(directory):
    print(f"= {crate}")

    f = open(os.path.join(directory, crate), "r")
    repo = f.read().strip()

    if repo == "norepo" or repo == "auth":
        modules["nocheck_crates"].append(crate)
        continue

    if not crate in modules:
        modules["crates"][crate] = {}

    # Repo url
    proc = subprocess.Popen(["git config -f .git/config -l"],
                            cwd=os.path.join(repo_dir, repo),
                            stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    for line in out.decode('utf-8').splitlines():
        search = re.search(r'remote\..+\.url=(.+)', line)
        if search:
            modules["crates"][crate]["url"] = clean_url(search.group(1))

    # Commit id
    proc = subprocess.Popen(["git log -q"],
                            cwd=os.path.join(repo_dir, repo),
                            stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    for line in out.decode('utf-8').splitlines():
        search = re.search(r'commit (.+)', line)
        if search:
            modules["crates"][crate]["commit"] = search.group(1)

    # Submodules
    modules_file = os.path.join(repo_dir, repo, ".gitmodules")
    if os.path.exists(modules_file) and not os.stat(modules_file).st_size == 0:
        modules["crates"][crate]["submodules"] = {}

        proc = subprocess.Popen(["git config -f .gitmodules -l"],
                                cwd=os.path.join(repo_dir, repo),
                                stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        for line in out.decode('utf-8').splitlines():
            search = re.search(r'submodule\.(.+)\.(.+)=(.+)', line)
            module = search.group(1)
            if not module in modules["crates"][crate]["submodules"]:
                modules["crates"][crate]["submodules"][module] = {}
            if search.group(2) == "url":
                modules["crates"][crate]["submodules"][module][search.group(2)] = clean_url(search.group(3))
            else:
                modules["crates"][crate]["submodules"][module][search.group(2)] = search.group(3)

        for module in modules["crates"][crate]["submodules"]:
            # Submodule latest commit date
            proc = subprocess.Popen(["git log -q -- " + modules["crates"][crate]["submodules"][module]["path"]],
                                    cwd=os.path.join(repo_dir, repo),
                                    stdout=subprocess.PIPE, shell=True)
            (out, err) = proc.communicate()
            for line in out.decode('utf-8').splitlines():
                search = re.search(r'Date: *(.*)', line)
                if search:
                    date = email.utils.parsedate_to_datetime(search.group(1))
                    modules["crates"][crate]["submodules"][module]["date"] = date.isoformat()

            # Submodule commit id
            proc = subprocess.Popen(["git submodule"],
                                    cwd=os.path.join(repo_dir, repo),
                                    stdout=subprocess.PIPE, shell=True)
            (out, err) = proc.communicate()
            for line in out.decode('utf-8').splitlines():
                search = re.search(r'-(.+) ' + module, line)
                if search:
                    modules["crates"][crate]["submodules"][module]["commit"] = search.group(1)

with open('crates.json', 'w', encoding='utf-8') as f:
    json.dump(modules, f, ensure_ascii=False, indent=4)
