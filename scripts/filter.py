#!/usr/bin/python

import re
import json
import toml
from pprint import pprint

# Filter raw data using some heuristics to only keep
# stuff relevant to security.

def repo_info(repo):
    # flaky heuristic, but works for github, gitlab and a lot of hosted servers
    regex = r'(https?|git)://(.+)/(.+)/(.+)/?(\.git)?'
    search = re.search(regex, repo)
    if not search:
        return (None, None, None)

    return (search.group(2).lower(), search.group(3).lower(), search.group(4).lower())

# Are the two repos part of the same organization
def same_organization(url1, url2):
    (platform1, org1, repo1) = repo_info(url1)
    if platform1 is None or org1 is None:
        return False
    (platform2, org2, repo2) = repo_info(url2)
    if platform2 is None or org2 is None:
        return False

    return platform1 == platform2 and org1 == org2


# Rebuild data by dependency
# key is repo url
dependencies = {}
repositories = {}
repositories_old = {}

with open('repositories.toml') as toml_file:
    repositories_old = toml.load(toml_file)

with open('crates.json') as json_file:
    data = json.load(json_file)
    for crate, crate_info in data["crates"].items():
        if "submodules" not in crate_info:
            continue

        for module, module_info in crate_info["submodules"].items():
            url = module_info["url"]
            (platform, org, repo) = repo_info(url)

            if same_organization(crate_info["url"], url):
                # local to the same organization, let's skip
                continue

            if url not in dependencies:
                dependencies[url] = {}

            # import old data
            if url in repositories_old:
                repositories[url] = repositories_old[url]

            if url not in repositories:
                repositories[url] = {"tag": "TODO"}

            repositories[url]

            dependencies[url][crate] = {}
            if "date" in module_info:
                dependencies[url][crate]["date"] = module_info["date"]
            if "commit" in module_info:
                dependencies[url][crate]["commit"] = module_info["commit"]
            dependencies[url][crate]["path"] = module_info["path"]
            dependencies[url][crate]["url"] = crate_info["url"]

with open('submodules.json', 'w', encoding='utf-8') as f:
    json.dump(dependencies, f, indent=4)

# Add new URLs with TODO type
with open('repositories.toml', 'w', encoding='utf-8') as f:
    toml.dump(repositories, f)

exit(0)


print("# Source crates")
print("")
for dep,dep_info in dependencies.items():
    print(f"## {dep}")
    print("")
    for crate,info in dep_info.items():
        if crate+"-sys" in dep_info:
            if info["url"] == dep_info[crate+"-sys"]["url"]:
                # skip if
                continue
        print(f"### {crate}")
        print("")
        if "date" in info:
            print(" * latest change: " + info["date"])
        print(" * path: " + info["path"])
        print(" * url: " + info["url"])
        print("")

