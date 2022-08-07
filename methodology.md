
# Methodology

- Select all crates with more than 100k downloads (4772 crates on 2022-08-07)
- Try to clone all associated repositories (3072 repositories successfully cloned with
  [`scripts/clone.sh`](https://github.com/amousset/source-crates/blob/main/scripts/clone.sh))
- Then compute information about these crates and their submodules with
  [`scripts/modules.py`](https://github.com/amousset/source-crates/blob/main/scripts/modules.py) in
  [`data/crates.json`](https://github.com/amousset/source-crates/blob/main/data/crates.json).

There were 438 different submodule repositories (after
excluding submodules in the same Github organization as the source repository). When several crates
are hosted in the same directory, the submodule appears several time, which explain the high number
of duplicates. The submodules list, with the repositories they are part of, computed with
[`scripts/filter.py`](https://github.com/amousset/source-crates/blob/main/scripts/filter.py), is
located in
[`data/submodules.json`](https://github.com/amousset/source-crates/blob/main/data/submodules.json).

_Note: A few crates use code from the [copies](https://github.com/copies) organization which
provides mirrors for projects hosted outside of Github. It gives no indication about who it's run
by, and does not seem to be frequently updated, nor following upstream versions._

Among these 216 included repositories:

- 102 contained data sets (unicode data, time zones, syntax highlighting definitions, etc.)
- 34 contained tests suites or test data set
- 90 libraries, including 14 Rust libraries, 14 C++ libraries and 56 C libraries

(these numbers are based on approximate tagging manually done in
[`data/repositories.toml`](https://github.com/amousset/source-crates/blob/main/data/repositories.toml)).
