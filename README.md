# External source crates

This post investigates the Rust crates including third-party code (often C/C++ libraries) statically linked into Rust binaries. The goal is to explore the current situation to propose ways to make it easier to import C/C++ code in a secure and reliable manner.

## Current state

### Overview

To get an idea to which extent this pattern is used, let's explore crates.io content with an analysis of the crates with more than 100k downloads on 2022-08-07 (the 4,7k top crates), see the  [`methodology`](https://github.com/amousset/source-crates/blob/main/methodology.md) for more details.

There are currently 70 C/C++ native libraries included in 58 crates from the top 4,7k crates (included with submodules, not counting those directly copied into the crate source). Some of them are widely used, like `libz-sys` with 20M downloads and 46 reverse dependencies, or `libgit2-sys` with 11M downloads. Among these crates:

* 6 have the `-src` suffix in their name
  * `boringssl-src`, `openblas-src`, `sqlite3-src`, `openssl-src`, `zeromq-src` and `luajit-src`
  * A total of 47 crates in crates.io have the `-src` suffix.

* 38 are `-sys` crates that include a library directly
  * `libevent-sys`, `pcre2-sys`, `lmdb-sys`, `lzma-sys`, `lmdb-rkv-sys`, `croaring-sys`, `openvino-sys`, `zstd-sys`, `cloudflare-zlib-sys`, `mozjpeg-sys`, `boring-sys`, `libsodium-sys`, `librocksdb-sys`, `libz-sys`, `libnghttp2-sys`, `libgit2-sys`, `sdl2-sys`, `curl-sys`, `rpmalloc-sys`, `sass-sys`, `rdkafka-sys`, `snmalloc-sys`, `wabt-sys`, `z3-sys`, `ckb-librocksdb-sys`, `libssh2-sys`, `libbpf-sys`, `oboe-sys`, `lz4-sys`, `tikv-jemalloc-sys`, `fasthash-sys`, `libusb1-sys`, `shaderc-sys`, `minimp3-sys`, `jemalloc-sys`, `liblmdb-sys`, `aom-sys`, `brotli-sys`
  * A total of 2288 crates in crates.io have the `-sys` suffix.

* 2 have a `_sys` suffix, a `-sys` variant
  * `audiopus_sys` and `onig_sys`

* 1 has an `-ffi` suffix, a `-sys` variant
  * `wepoll-ffi`

* 12 have no specific name pattern
  * `afl`, `hidapi`, `khronos_api`, `mimalloc`, `parity-secp256k1`, `rust-htslib`, `rusty_v8`, `souper-ir`, `spirv-reflect`, `sprs`, `tflite`, `twox-hash`

Two main patterns appear:

- standard [`-sys` crates](https://doc.rust-lang.org/cargo/reference/build-scripts.html#-sys-packages) which are also able to compile the library they are providing an interface for, either by default or only when enabled by a feature flag (see this [blog post](https://kornel.ski/rust-sys-crate) for details on how it's done).
- dedicated crates containing `-src` in the name.

_Note_: We have only analyzed the crates containing submodules, but sometimes the code is vendored directly into the repository, like `freetype-sys` which has a copy of freetype2 sources. In any case, the source becomes part of the crate uploaded to the registry, and sometimes of the produced binaries.

### Case studies

Let's have a closer looks at a few representative crates.

#### mozjpeg-sys

* The source is included through a git submodule.
* The version number of the crate, `1.0.2`, is not related to the upstream version, `4.0.3`.
* The license of the crate is `IJG` which broadly matches the source crate (but seems [incomplete](https://github.com/mozilla/mozjpeg/blob/5c6a0f0971edf1ed3cf318d7b32308754305ac9a/LICENSE.md))
* It always builds `mozjpeg` as a static dependency.

#### curl-sys

* The source is included through a git submodule.
* The crate versions are built as the following SemVer string: `0.4.56+curl-7.83.1`, defined as `MAJOR.MINOR.PATCH+BUILD` with `BUILD` being `curl-`+the upstream curl version.
* By default, it will try to dynamically link to the system curl and openssl, and fallback on static linking. It also has `static-curl`/`static-ssl` features to enforce static linking.
* There is [no way](https://github.com/alexcrichton/curl-rust/issues/321) to enforce dynamic linking (i.e. make the build fail if library is missing on the system).
* The crate documents an `MIT` license, while curl is licensed under a custom license (but close to MIT).

_Build number in SemVer_

The major version documents the compatibility of the library (1.1.OX, 1.1.1X, etc. are compatible). The minor version is incremented at each upstream patch version bump. The patch version is used for changes in the crate not linked to an upstream version bump. The build metadata here is used as upstream version documentation.

#### openssl-src

* The source is included through a git submodule.
* The crate only contains the logic to build openssl (through a git submodule). The interface is in `openssl-sys` which depends on `openssl-src` when the `vendored` feature is enabled (disabled by default). Some crates depending on `openssl-sys` (like `native-tls`) expose a similar flag too.
* The crate documents an `MIT OR Apache-2.0` license, while openssl is licensed under:
* Apache-2.0 starting from 3.0
* Dual OpenSSL and SSLeay licenses before, which are in particular not compatible with the GPL. The `release/111` branch providing versions under this license is still maintained.
* The crate versions are built as the following SemVer string: `111.16.0+1.1.1l`, defined as `MAJOR.MINOR.PATCH+BUILD`, with `BUILD` being the upstream openssl version.

## Issues

A lot of widely-used crates include third-party libraries,
with low consistency in behavior.

- There is no consistency in naming (crates, features) or behaviors. 

This can be a source of problems in terms of:

- *Presence*: It is not always easy to even know if a library was statically linked as it does not appear in the crates tree, `cargo-auditable` data, or any [SBOM](https://www.cisa.gov/sbom) (like [cargo-spdx](https://github.com/alilleybrinker/cargo-spdx))
- *Licenses*: The core problem here is that we get a crate with a license documented in `Cargo.toml` but which sometimes is different from the one applied to the library embedded in the crate's source.
  In this case they are not easily discoverable, for example, `cargo deny check licenses` cannot check them. A good example is the OpenSSL licence for versions before 3.0, which is incompatible with GPL.
- *Vulnerabilities*: Except for dedicated source crates (`openssl-src` has [RustSec advisories](https://rustsec.org/packages/openssl-src.html)), there is no visibility over vulnerabilities affecting the included library in the usual Rust tooling (`cargo-audit` and `cargo-deny`)
- *Versioning*: There is no easy visibility over the upstream version.
- *Trust*: The code is included from external git repositories, written by unidentified people, and is not visible in tooling like `cargo-supply-chain`, `rust-audit` or `cargo-crev`
- *Usability*: The way to select static vs. dynamic compilation varies, and is sometimes not even actionnable. Some `-sys` crates (like [`curl-sys`](https://github.com/alexcrichton/curl-rust/issues/321)) silently fall back to using statically linked dependencies if not detected on the build system without a way to force dynamic linking.

Current challenges with software supply chain attacks push TODO.

## Propositions

Just as `-sys` crates have an official definition in cargo docs, with a set of best practices, a first step could be to come up with similar guidelines for external source crates. This should build upon and stay compatible with existing implementation, and allow an easy convergence for libraries using different patterns.

This could be improved by additional tooling, metadata, etc.

### Crate architecture

Having dedicated crates (with the `-src` suffix for discoverability) seems to have quite a few advantages:

* Allow independent versioning, releases, licenses
* Allow accurate vulnerability management (through `advisory-db`)
* Give visibility over included code

  * In `cargo tree`, `cargo auditable`
  * 

One obvious drawback is the maintenance overhead.

#### Configuration

Ideally there should be a standard way (through
features on `-sys` crates) to:

* Allow to enforce either static or dynamic linking
* Keep the convenient default used in most existing crates (dynamic linking with static fallback)

The is already a [pre-RFC](https://internals.rust-lang.org/t/pre-rfc-cargo-features-for-configuring-sys-crates/12431) by @kornel to address this.

### Source embedding

There are two ways:

* git submodule

  * another problem is that some libraries have different contents in git compared to release tarballs, and may have different build procedures (git vs. tarball).

* source import in tree

### Versioning

We saw that most existing `-src` crates use the SemVer build metadata to provide upstream version.
Build metadata is [defined](https://semver.org/#spec-item-10) as:

> Build metadata MAY be denoted by appending a plus sign and a series of dot separated identifiers immediately following the patch or pre-release version. Identifiers MUST comprise only ASCII alphanumerics and hyphens [0-9A-Za-z-]. Identifiers MUST NOT be empty. Build metadata MUST be ignored when determining version precedence. Thus, two versions that differ only in the build metadata, have the same precedence. Examples: 1.0.0-alpha+001, 1.0.0+20130313144700, 1.0.0-beta+exp.sha.5114f85, 1.0.0+21AF26D3—-117B344092BD.

This means that the upstream version is:

* Ignored by version comparison
* Can contain various embedded version representation

Using the upstream version directly would cause some trouble:

* Not all software use SemVer compatible versioning
* We need to keep a way to publish updated build code without bumping the embedded code

### Metadata

Licenses

does a crate license need to match all files included in the crate?

Link to source * There is no standard way to designate a piece of software, especially C/C++ libraries. It could be a link to a Git repository

### Improve tooling

Cargo-based tooling could get some knowledge to detect `-src` crates and implement special handling (extract upstream version, etc.).



automatic import of new releases, automatic import of CVEs to RustSec, etc


== Way forward

* If others are interested, a [project group](https://rust-lang.github.io/rfcs/2856-project-groups.html) dedicated to working on this topic

_Special thanks to @Shnatsel for reviewing this._