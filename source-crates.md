# External source crates

The goals would be something along the lines of creating guidelines for handling
externally imported code and developing the supporting tooling (automatic import of new releases,
automatic import of CVEs to RustSec, etc) Or, in terms of problems rather than solutions - make it
easier to import C/C++ code in a secure and reliable manner and keep it up-to-date

It is a good idea to use crates.io as a repository for C/C++ dependencies used by Rust library? It's already massively used, and we need to deal with it.

This article investigates the Rust crates including third-party code (often C/C++ libraries)
statically linked into Rust binaries. The goal is to explore the current situation and the
challenges it creates, and to propose some possible improvements.

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

To get an idea to which extend this pattern is used, let's explore crates.io content.

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

### Results

In short, there are 95 C/C++ native libraries in the top 7k crates (included with submodules, not
counting those directly copied into the crate source.

Only 7 crates including a C/C++ library among these 95 libraries currently have the `-src` suffix in their
name (`boringssl-src`, `openblas-src`, `sqlite3-src`, `openssl-src`, `netlib-src`, `zeromq-src`
and `luajit-src`).

## Issues

We have seen that:

- A lot of widely-used crates include third-party libraries
- There is no consistency in naming (crates, features) or behaviors. Some `-sys` crates (like [`curl-sys`](https://github.com/alexcrichton/curl-rust/issues/321)) even silently fall back to using statically linked dependencies if not detected on the build system.

This can be a source of problems, especially because of the lack of visibility over the included code in terms of:

- *Presence*: It is not always easy to even know if a library was statically linked as it does not appear in the crates tree, nor `cargo-audit` output.
- *Licenses*: They are often different from the Rust source, and not easily discoverable. For example, `cargo deny check licenses` cannot check them. A good example is the OpenSSL licence for versions before 3.0, which is incompatible with GPL.
- *Vulnerabilities*: Except for dedicated source crates (`openssl-src` has [RustSec advisories](https://rustsec.org/packages/openssl-src.html)), there is no visibility over vulnerabilities affecting the included library in the usual Rust tooling (`cargo-audit` and `cargo-deny`)
- *Versioning*: There is no easy visibility over the upstream version. Sometime the upstream version is used as build version for dedicated crates, like `111.15.0+1.1.1k` for `openssl-src` (`1.1.1k` being the upstream release pointed by the submodule commit)
- *Trust*: The code is included from external git repositories, written by unidentified people, and is not visible in tooling like `cargo-supply-chain`, `rust-audit` or `cargo-crev`

Current challenges with software supply chain attacks push TODO.


### Security

### Compliance

SBOM

## Prior art

Not much. `sys` crates for naming-based behavior and conventions.

### Other ecosystems

#### D-lang

https://code.dlang.org/packages/openssl

* Uses a versioning scheme similar to the rust crate (`2.0.3+1.1.0h`). 
* Documents the openssl license as the package license ("OpenSSL or SSLeay")

### crates.io

#### curl-sys

Other crates work like this (`brotli-sys`).

#### openssl-src

One of the most used crate embedding a static library is `openssl-src`. It is an example of a dedicated crate, i.e. it only contains the logic to build openssl and its sources (through a git submodule).

The crate versions are built as the following SemVer string: `111.16.0+1.1.1l`, defined as `MAJOR.MINOR.PATCH+BUILD`

The build metadata here is used as upstream version documentation. The major version documents the compatibility of the library (1.1.OX, 1.1.1X, etc. are compatible). The minor version is incremented at each upstream patch version bump. The patch version is used for changes in the crate not linked to an upstream version bump.

Build metadata is [defined](https://semver.org/#spec-item-10) as:

> Build metadata MAY be denoted by appending a plus sign and a series of dot separated identifiers immediately following the patch or pre-release version. Identifiers MUST comprise only ASCII alphanumerics and hyphens [0-9A-Za-z-]. Identifiers MUST NOT be empty. Build metadata MUST be ignored when determining version precedence. Thus two versions that differ only in the build metadata, have the same precedence. Examples: 1.0.0-alpha+001, 1.0.0+20130313144700, 1.0.0-beta+exp.sha.5114f85, 1.0.0+21AF26D3—-117B344092BD.

This means that the upstream version is:

* Ignored by version comparison
* Can contain various embedded version representation

The `openssl-src` crate is used by `openssl-sys` (and openssl is statically built in the resulting binary) when the `vendored` feature is enabled (which it is not by default). Crates depending on `openssl-sys` or (like `native-tls`) may expose a similar flag too.

## Propositions

### Define an official convention

Just as `-sys` crates have an official definition in cargo docs, with a set of best practices, a first step could be to come up with similar guidelines for external source crates. This should build upon and stay compatible with existing implementation, and allow an easy convergence for libraries using different patterns.

This could be improved by additionnal cargo metadata.

#### Draft proposal

- Split third-party code inclusion into dedicated separate crates, and name them with the `-src` suffix
- Use the upstream version as crate build version. This means that the crate version needs to be incremented for each upstream update (as already done for `openssl-src`). The problem is that it makes version requirements in dependant crates less readable (as the upstream version is not part of it). It could a plus though, as a lot of projects don't use semver versionning.
- Use git submodules when possible as it makes upstream tracking easier
- Add a reference to the included code in the cargo metadata TODO
- Use a common behavior for static linking in libraries, including feature naming

This would allow:

- To improve discoverability and help library authors who want to allow statically linking a dependency
- To know when a static library is included, directly from `cargo-tree`
- To file RustSec advisories for vulnerabilities in upstream libraries (like already done for `openssl-src`). We could automate detection based on CVEs for common libraries, and integrate directly with `cargo-audit` and `cargo-deny`

#### Limitations

* If the `-src` contains dedicated code to build the included code, it is a problem is licensed under a license different from the included code
* There is no standard way to designate a piece of software, espacially C/C++ libraries. It could be a link to a Git repository. TODO
* putting the upstream version in build metadata (i.e. after +) is not a great idea because
according to the semver spec there is no defined ordering for versions that only differ by build
metadata. Meaning it might not be possible to match on some build versions but not others, which
would be necessary for RustSec. But that's details.


### Improve tooling

Cargo-based tooling could get some knowledge to detect `-src` crates and implement special handling (extract upstream version, etc.).

This could allow implementing correct [SBOM](https://www.cisa.gov/sbom) (like [cargo-spdx](https://github.com/alilleybrinker/cargo-spdx)).






# NOTES

advisory unmaintained pour https://github.com/nodejs/http-parser
https://github.com/rustsec/advisory-db/pull/1124
https://internals.rust-lang.org/t/pre-rfc-cargo-features-for-configuring-sys-crates/12431
https://amousset.github.io/source-crates/ 
https://rust-lang.github.io/rfcs/2856-project-groups.html
https://internals.rust-lang.org/t/how-to-audit-and-improve-rust-crates-eco-system-for-security-in-general/16699 

https://www.reddit.com/r/rust/comments/n43pcb/psa_libzsys_on_musl_no_longer_links_statically_by/

- crates versions and features: use `rust-audit`

- compiler version:

  - Easily accessible with [rustc_version_runtime](https://crates.io/crates/rustc_version_runtime)
  - Always there (in non-stripped binaries):

```
$ strings your_executable | grep 'rustc version'
clang LLVM (rustc version 1.51.0 (2fd73fabe 2021-03-23))
```



I'm also not convinced that submodules are a good idea. There are a lot of pitfalls around them; for
one, a repo with submodules is no longer defined by its commit hash, which makes reproducibility a
lot harder. Also, it turns out that C/C++ projects often have different contents in git compared to
release tarballs, and require different procedures to build from git vs release tarballs.

another thing I've lamented is how much e.g. curl versions lag behind upstream, even in case of
critical security fixes. We could build automated infrastructure for updating library versions: new
release tarballs could be pulled automatically, and with a bit of work even published automatically:
we could run crater on the dependencies of the crate before and after the update, if all tests pass
then publish it without requiring manual review. I believe @HeroicKatora has been working on a
"crater for your dependencies" kind of tool

Hmm, how should the version synchronization between -sys and -src crates be handled? Is there a way
to specify "I want -src version X" even though you don't depend on it directly? If not, should -sys
and src crates be published together and always have the same version to allow selecting a specific
version of -src crate?

