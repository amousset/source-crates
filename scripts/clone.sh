#!/bin/bash

set -xe

# Avoid git authentication prompts
export GIT_TERMINAL_PROMPT=0

mkdir -p crates-src

# data/crates.csv comes from crates.io db dump
for crate in $(xsv select downloads,name,repository ./data/crates.csv | rg "^(\d{5}).*"); do
  repo=$(echo $crate | cut -d, -f3)
  name=$(echo $crate | cut -d, -f2)

  if [ -z "$repo" ]; then
    echo "norepo" > crates-src/$name
  else
    if [ ! -d crates-src/$name ]; then
      if ! git clone --depth 1 $repo crates-src/$name; then
        echo "auth" > crates-src/$name
      fi
    else
      git -C crates-src/$name pull
    fi
  fi
done

