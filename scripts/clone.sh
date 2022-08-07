#!/bin/bash

set -xe

# Avoid git authentication prompts
export GIT_TERMINAL_PROMPT=0

#wget https://static.crates.io/db-dump.tar.gz
#tar -xf db-dump.tar.gz

#cd 2022-08-06-020034

# data/crates.csv comes from crates.io db dump
for crate in $(xsv select downloads,name,repository ./data/crates.csv | rg "^(\d{6}).*"); do
  mkdir -p crates
  mkdir -p repos

  repo=$(echo $crate | cut -d, -f3)
  repo_hash=$(echo "$repo" | sha1sum | cut -d' ' -f1)
  name=$(echo $crate | cut -d, -f2)

  if [ -z "$repo" ]; then
    echo "norepo" > crates/$name
  else
    if [ ! -d repos/${repo_hash} ]; then
      if ! git clone --depth 1 $repo repos/$repo_hash; then
        echo "auth" > crates/$name
        continue
      fi
    fi
    echo $repo_hash > crates/$name
  fi
done
