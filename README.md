# External source crates

This post investigates the Rust crates including third-party code (often C/C++ libraries) statically linked into Rust binaries. The goal is to explore the current situation and to start a discussion about ways to make it easier to import C/C++ code in a secure and reliable manner.

## Current state

### Overview

To get an idea to which extent this pattern is used, let's explore crates.io content with an analysis of the crates with more than 100k downloads on 2022-08-07 (the 4,7k top crates, see the  [methodology](https://github.com/amousset/source-crates/blob/main/methodology.md) for more details).

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
- dedicated crates containing `-src` in the name, depended on by `-sys` crates

_Note_: This only covers the crates containing submodules, but sometimes the code is vendored directly into the repository, like `freetype-sys` which has a copy of freetype2 sources. In any case, the source becomes part of the crate uploaded to the registry.

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

#### openssl-src

* The source is included through a git submodule.
* The crate only contains the logic to build openssl. The API is in `openssl-sys` which depends on `openssl-src` when the `vendored` feature is enabled (disabled by default). Some crates depending on `openssl-sys` (like `openssl` and `native-tls`) expose a similar flag too.
* The crate documents an `MIT OR Apache-2.0` license, while openssl is licensed under:
  * Apache-2.0 starting from 3.0
  * Dual OpenSSL and SSLeay licenses before, which are in particular not compatible with the GPL. The `release/111` branch providing versions under this license is still maintained.
* The crate versions are built as the following SemVer string: `111.16.0+1.1.1l`, defined as `MAJOR.MINOR.PATCH+BUILD`, with `BUILD` being the upstream openssl version.

## Issues

A lot of widely-used crates include third-party libraries, with little consistency. It causes problems in terms of:

- *Visibility*: It is not always easy to know if a library was statically linked (and which version) as it does not appear in the crates tree, `cargo-auditable` data, or any automated [SBOM](https://www.cisa.gov/sbom) (like [cargo-spdx](https://github.com/alilleybrinker/cargo-spdx))
- *Usability*: The way to select static vs. dynamic compilation varies, and is sometimes not even actionnable. Some `-sys` crates fall back to using statically linked dependencies if not detected on the build system [without a way to force dynamic linking](https://github.com/alexcrichton/curl-rust/issues/321).
- *Licenses*: The core problem here is that the license documented in the `Cargo.toml` (which is supposedly thought to cover only the build code) is sometimes different from the licenses applicable to the library itself, meaning the crate metadata does not match reality. In this case they are not easily discoverable, and tools like `cargo deny check licenses` cannot check them. A good example is the OpenSSL licence for versions before 3.0, which is incompatible with GPL.
- *Vulnerabilities*: Except for [dedicated source crates](https://rustsec.org/packages/openssl-src.html), there is no accurate visibility over vulnerabilities affecting the included library in the usual Rust tooling (`cargo-audit` and `cargo-deny`).
- *Trust*: The code is included from external sources, written by unidentified people, and is not visible in tooling like `cargo-supply-chain`, `rust-audit` or `cargo-crev`

## Possible improvements

Just like `-sys` crates have an official definition in cargo docs, with a set of recommended practices, a first step could be to come up with similar guidelines for external source crates. This could build upon implementations, and allow an easy convergence for libraries using different patterns. This could then be improved by additional tooling or metadata.

### Architecture

Having dedicated crates (with the `-src` suffix for discoverability) seems to have quite a few advantages:

* Allow independent versioning, releases, licenses, security advisories
* Give visibility over included code in all cargo-based tooling

One obvious big drawback is the maintenance overhead.

### Configuration

Ideally there should be a recommended way (through
features on `-sys` crates) to:

* Allow to enforce either static or dynamic linking
* Keep the convenient default used in most existing crates (dynamic linking with static fallback)

The is already a [pre-RFC](https://internals.rust-lang.org/t/pre-rfc-cargo-features-for-configuring-sys-crates/12431) by @kornel to discuss this.

### Source embedding

There are two ways:

* git submodule

  * Some libraries have different contents in git compared to release tarballs, and may have different build procedures (git vs. tarball).

* Source import directly in tree

### Versioning

Most existing `-src` crates use the SemVer build metadata to provide upstream version. Build metadata is [defined](https://semver.org/#spec-item-10) as a _series of dot separated identifiers using only ASCII alphanumerics and hyphens_, which are _ignored when determining version precedence_. Hence, the format is quite flexible, but cannot be used for actual version comparisons (which need to rely on the base SemVer version).

Using the upstream version directly as the crate version would cause some trouble:

* Not all software use SemVer compatible versioning
* We need to keep a way to publish updated build code without bumping the embedded code

### Metadata

The license of a crate should cover all files included in the crate archive, including external embedded files.

Using a dedicated crate makes it easier by allowing to easily document different licenses for external code and `-sys` crate.

### Improve tooling

Some cargo-based tooling could get some knowledge to detect `-src` crates and implement special handling (extract upstream version, etc.), maybe using additional metadata.

## Conclusion

* Do you know other ressources around this topic?
* If others are interested, a [project group](https://rust-lang.github.io/rfcs/2856-project-groups.html) could be an option to work on this topic.

_Special thanks to @Shnatsel for reviewing this._