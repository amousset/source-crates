#!/usr/bin/python

# This script completes the source-crates.toml file from submodules information

import toml
import json
import sys
from pprint import pprint

src_crates = toml.load(open('../db/source-crates.toml'))
crates = json.load(open('../data/crates.json'))

for crate in src_crates:

    # todo try to clone to get submodule info


    if crate in crates["crates"]:
        if "url" in crates["crates"][crate]:
            src_crates[crate]["upstream_repository"] = crates["crates"][crate]["url"]
        if "commit" in crates["crates"][crate]:
            src_crates[crate]["upstream_commit"] = crates["crates"][crate]["commit"]

# Add now URLs with TODO type
with open('../db/source-crates.toml', 'w', encoding='utf-8') as f:
    toml.dump(src_crates, f)
