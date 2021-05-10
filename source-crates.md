## Introduction

This article investigates the Rust crates including third-party code (often C/C++ libraries)
statically linked into Rust binaries. The goal is to explore the current situation and the
challenges, and to propose some improvements and proof-of-concepts for dedicated tooling.

There are two main ways to include third-party dependency libraries into a crate source (and
resulting binary):

- dedicated crates (usually containing `-src` in the name). A widely used example is `openssl-src`
  (used as `openssl-sys` dependency if the `vendored` feature is enabled).
- normal [`-sys` crates](https://doc.rust-lang.org/cargo/reference/build-scripts.html#-sys-packages)
  which are able to compile the library they are providing an interface for, either by default or
  only when enabled by a feature flag (see this [blog post](https://kornel.ski/rust-sys-crate) blog
  posts for explanations). A widely used example is `curl-sys`.

Sometimes the code is copied into the repository, sometimes it is configured as a git submodule. In
any case the source becomes part of the the crate uploaded to the registry.

## Current state

In order to understand the current situation, besides currently recognizable `-src` crates, a first
step can be to analyze the most downloaded crates, and look for included third-party code.

### Methodology

- Select all crates with more than 10k downloads (6984 crates on 2021-05-05)
- Try to clone all associated repositories (6322 crates successfully cloned with
  [`scripts/clone.sh`](https://github.com/amousset/source-crates/blob/main/scripts/clone.sh))
- Look for submodules in the cloned crates (595 crates contained submodules)
- Then compute information about these crates and their submodules with
  [`scripts/modules.py`](https://github.com/amousset/source-crates/blob/main/scripts/modules.py) in
  [`data/crates.json`](https://github.com/amousset/source-crates/blob/main/data/crates.json).

Among those 595 crates containing submodules, there were 251 different submodule repositories (after
excluding submodules in the same Github organization as the source repository). When several crates
are hosted in the same directory, the submodule appears several time, which explain the high number
of duplicates. The submodules list, with the repositories they are part of, computed with
[`scripts/filter.py`](https://github.com/amousset/source-crates/blob/main/scripts/filter.py), is
located in
[`data/submodules.json`](https://github.com/amousset/source-crates/blob/main/data/submodules.json).

_Note: Three crates use code from the [copies](https://github.com/copies) organization which
provides mirrors for projects hosted outside of Github. It gives no indication about who it's run
by, and does not seem to be updated regularly, nor following upstream versions._

Among these 251 included repositories:

- 89 contained data sets (unicode data, time zones, syntax highlighting definitions, etc.)
- 32 contained tests suites or test data set
- 119 libraries, including 13 Rust libraries, 24 C++ libraries and 71 C libraries

(these numbers are based on approximate tagging in
[`data/repositories.toml`](https://github.com/amousset/source-crates/blob/main/data/repositories.toml)).

**In short, there are 95 C/C++ native libraries in the top 7k crates (included with submodules, not
counting those directly copied into the crate source.**

**Only 7 crates including a C/C++ library among these 95 libraries have the `-src` suffix in their
name** (`boringssl-src`, `openblas-src`, `sqlite3-src`, `openssl-src`, `netlib-src`, `zeromq-src`
and `luajit-src`).

### Conclusions

- A lot of widely-used crates include third-party libraries
- There is no consistency in naming (crates, features) or behaviors. Some `-sys` crates (like
  [`curl-sys`](https://github.com/alexcrichton/curl-rust/issues/321)) use statically linked
  dependencies automatically if not detected on the build system

This can be a source of problems, especially because of the lack of visibility over the included
code in terms of:

- *Presence*: It is not always easy to even know if a library was statically linked as it does not
  appear in the crates tree
- *Licenses*: They are often different from the Rust source, and not easily discoverable. For
  example, `cargo deny check licenses` cannot check them.
- *Vulnerabilities*: Except for dedicated source crates (`openssl-src` has
  [RustSec advisories](https://rustsec.org/packages/openssl-src.html)), there is no visibility over
  vulnerabilities affecting the library in the usual Rust tooling (`cargo-audit` and `cargo-deny`)
- *Versioning*: There is no easy visibility over the upstream version. Sometime the upstream version
  is used as build version for dedicated crates, like `111.15.0+1.1.1k` for `openssl-src` (`1.1.1k`
  being the upstream release pointed by the submodule commit)
- *Trust*: The code is included from external git repositories, written by unidentified people, and
  is not visible in tooling like `cargo-supply-chain`, `rust-audit` or `cargo-crev`

## Perspectives

### Best practices for libraries

To help the ecosystem converge towards common practices (like it is done for `-sys` crates), it
could be useful to discuss and document them.

They could include (based on existing crates):

- Recommend to split third-party code inclusion into separate crates, and name them with the `-src`
  suffix
- Use the upstream version as crate build version
- Use git submodules when possible as it makes upstream tracking easier
- Use a common behavior for static linking, including feature naming

This would allow:

- To improve discoverability and help library authors who want to allow statically linking a
  dependency
- To know when a static library is included, directly from `cargo-tree`
- To file RustSec advisories for vulnerabilities in upstream libraries (like already done for
  `openssl-src`). We could automate detection based on CVEs for common libraries, and integrate
  directly with `cargo-audit` and `cargo-deny`

### Dedicated tooling

Even if all source crates were dedicated and recognizable, important information would still be
missing. Before an integrated solution, a solution could be to semi-manually define a database of
information about upstream libraries, which could be consumed by the tooling.

This database could include:

- the library license
- the upstream repository (to avoid having to clone to look for submodules)

This would allow:

- To correctly check for licenses in statically linked libraries
- To get information about upstream authors in `cargo-supply-chain`

A proof-of-concept of such a database is present in
[db/source-crates.toml](https://github.com/amousset/source-crates/blob/main/db/source-crates.toml),
which contains existing `-src` crates. The
[`src-crates`](https://github.com/amousset/source-crates/tree/main/src-crates) cli allows updating
its content from crates.io.

### Proof of concept

The easiest option for source crates integration would be to be able to use usual tooling of the
Rust ecosystem.

#### `cargo supply-chain`

It could be modified to use the information database and display the list of source crates with:

- License
- Version (based on crate version)
- Publisher (Github organization in practice for now)

Current [experimental branch](https://github.com/amousset/cargo-supply-chain/tree/source_crates)
gives something like:

```
$ cargo supply-chain source-crates
Source crates packaging third-party projects:
krb5
  version: 1.18.2
openssl
  license: OpenSSL License/SSLeay
  repository: https://github.com/openssl/openssl
  version: 1.1.1k
```

It parses upstream version from source crate version and uses information from the source crated
database in this repository.

#### `cargo deny licenses`

The same principle could be done to add static libraries licenses to `cargo deny` and properly check
all included code.
