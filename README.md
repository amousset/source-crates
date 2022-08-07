# External source crates

It is a good idea to use crates.io as a repository for C/C++ dependencies used by Rust library? It's already massively used, and we need to deal with it.

make it easier to import C/C++ code in a secure and reliable manner and keep it up-to-date

This article investigates the Rust crates including third-party code (often C/C++ libraries) statically linked into Rust binaries. The goal is to explore the current situation and the
challenges it creates, and to propose some possible improvements.

## Current state

### Overview

To get an idea to which extend this pattern is used, let's explore crates.io content with an analysis of the crates with more than 100k downloads on 2022-08-07 (the 4,7k top crates), see the  [`methodology`](https://github.com/amousset/source-crates/blob/main/methodology.md) for more details.

There are currently 70 C/C++ native libraries included in 58 crates from the top 4,7k crates (included with submodules, not counting those directly copied into the crate source). Some of them are highly used, like `libz-sys` with 20M downloads en 46 reverse dependencies, or `libgit2-sys` with 11M downloads).

Among these 58 crates:

* 6 have the `-src` suffix in their name (`boringssl-src`, `openblas-src`, `sqlite3-src`, `openssl-src`, `zeromq-src` and `luajit-src`). A total of 47 crates in crates.io have the `-src` suffix.

* 38 are `-sys` crates that include a library directly (`libevent-sys`, `pcre2-sys`, `lmdb-sys`, `lzma-sys`, `lmdb-rkv-sys`, `croaring-sys`, `openvino-sys`, `zstd-sys`, `cloudflare-zlib-sys`, `mozjpeg-sys`, `boring-sys`, `libsodium-sys`, `librocksdb-sys`, `libz-sys`, `libnghttp2-sys`, `libgit2-sys`, `sdl2-sys`, `curl-sys`, `rpmalloc-sys`, `sass-sys`, `rdkafka-sys`, `snmalloc-sys`, `wabt-sys`, `z3-sys`, `ckb-librocksdb-sys`, `libssh2-sys`, `libbpf-sys`, `oboe-sys`, `lz4-sys`, `tikv-jemalloc-sys`, `fasthash-sys`, `libusb1-sys`, `shaderc-sys`, `minimp3-sys`, `jemalloc-sys`, `liblmdb-sys`, `aom-sys`, `brotli-sys`). A total of 2288 crates in crates.io have the `-sys` suffix.

* 2 have a `_sys` suffix (`audiopus_sys` and `onig_sys`), i.e. almost-`-sys` crates.

* 1 has an `-ffi` suffix (`wepoll-ffi`), i.e. a `-sys` variant.

* 12 have no specific name pattern (`afl`, `hidapi`, `khronos_api`, `mimalloc`, `parity-secp256k1`, `rust-htslib`, `rusty_v8`, `souper-ir`, `spirv-reflect`, `sprs`, `tflite`, `twox-hash`)

Two main patterns appear:

- dedicated crates containing `-src` in the name. A widely used example is `openssl-src` (used as `openssl-sys` dependency if the `vendored` feature is enabled).
- normal [`-sys` crates](https://doc.rust-lang.org/cargo/reference/build-scripts.html#-sys-packages) which are able to compile the library they are providing an interface for, either by default or
  only when enabled by a feature flag (see this [blog post](https://kornel.ski/rust-sys-crate) for details on how it's done). A widely used example is `curl-sys`.

Note that we only analyzed the crates containing submodules, but sometimes the code is vendored directly into the repository, like for example with `freetype-sys` which has a copy of freetype2 sources. In any case, the source becomes part of the the crate uploaded to the registry, and sometimes of the produced binaries.

### Case studies

Let's have a closer looks at a few representative crates.

#### mozjpeg-sys

* The source is included through a git submodule.
* The version number of the crate, `1.0.2`, is not related to the upstream version, `4.0.3`.
* The license of the crate is `IJG` which matches the source crate (but seems [incomplete](https://github.com/mozilla/mozjpeg/blob/5c6a0f0971edf1ed3cf318d7b32308754305ac9a/LICENSE.md))
* It always builds `mozjpeg` as a static dependency.

#### curl-sys

* The source is included through a git submodule.
* The crate versions are built as the following SemVer string: `0.4.56+curl-7.83.1`, defined as `MAJOR.MINOR.PATCH+BUILD` with `BUILD` being `curl-` the upstream curl version.
* By default, it will try to dynamically link to the system curl and openssl, and fallback on static linking. It also has `static-curl`/`static-ssl` features to enforce static linking.
* The crate documents an `MIT` license, while curl is licensed under a custom license (but close to MIT).
* There is [now way](https://github.com/alexcrichton/curl-rust/issues/321) to enforce dynamic linking (i.e. make the build fail if library is missing on the system).

**Build number in SemVer**

The build metadata here is used as upstream version documentation. The major version documents the compatibility of the library (1.1.OX, 1.1.1X, etc. are compatible). The minor version is incremented at each upstream patch version bump. The patch version is used for changes in the crate not linked to an upstream version bump.

Build metadata is [defined](https://semver.org/#spec-item-10) as:

> Build metadata MAY be denoted by appending a plus sign and a series of dot separated identifiers immediately following the patch or pre-release version. Identifiers MUST comprise only ASCII alphanumerics and hyphens [0-9A-Za-z-]. Identifiers MUST NOT be empty. Build metadata MUST be ignored when determining version precedence. Thus two versions that differ only in the build metadata, have the same precedence. Examples: 1.0.0-alpha+001, 1.0.0+20130313144700, 1.0.0-beta+exp.sha.5114f85, 1.0.0+21AF26D3—-117B344092BD.

This means that the upstream version is:

* Ignored by version comparison
* Can contain various embedded version representation

#### openssl-src

* The source is included through a git submodule.
* The crate only contains the logic to build openssl (through a git submodule). The interface is in `openssl-sys` which depends `openssl-src` on when the `vendored` feature is enabled (disabled by default). Crates depending on `openssl-sys` or (like `native-tls`) may expose a similar flag too.
* The crate documents an `MIT OR Apache-2.0` license, while openssl is licensed under:
 * Apache-2.0 starting from 3.0
 * Dual OpenSSL and SSLeay licenses before, which are in particular not compatible with the GPL. The `release/111` branch providing versions under this license is still maintained.
* The crate versions are built as the following SemVer string: `111.16.0+1.1.1l`, defined as `MAJOR.MINOR.PATCH+BUILD`, with `BUILD` being the upstream openssl version. See `curl-sys` for details.

## Issues

- A lot of widely-used crates include third-party libraries
- There is no consistency in naming (crates, features) or behaviors. Some `-sys` crates (like [`curl-sys`](https://github.com/alexcrichton/curl-rust/issues/321)) even silently fall back to using statically linked dependencies if not detected on the build system.

This can be a source of problems, especially because of the lack of visibility over the included code in terms of:

- *Presence*: It is not always easy to even know if a library was statically linked as it does not appear in the crates tree, nor `cargo-auditable` data.
- *Licenses*: The core problem here is that we get a crate with a license documented in `Cargo.toml` but which sometimes is different from the one applied to the library embedded in the crate's source.
In this case they are not easily discoverable, for example, `cargo deny check licenses` cannot check them. A good example is the OpenSSL licence for versions before 3.0, which is incompatible with GPL.
- *Vulnerabilities*: Except for dedicated source crates (`openssl-src` has [RustSec advisories](https://rustsec.org/packages/openssl-src.html)), there is no visibility over vulnerabilities affecting the included library in the usual Rust tooling (`cargo-audit` and `cargo-deny`)
- *Versioning*: There is no easy visibility over the upstream version.
- *Trust*: The code is included from external git repositories, written by unidentified people, and is not visible in tooling like `cargo-supply-chain`, `rust-audit` or `cargo-crev`
- *Usability*: The way to select static vs. dynamic compilation varies, and is sometimes not even actionnable (i.e. the crates enforce static linking if the library is not found on the system, and dynamic linking otherwise).

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

## Propositions

### Define an official convention

Just as `-sys` crates have an official definition in cargo docs, with a set of best practices, a first step could be to come up with similar guidelines for external source crates. This should build upon and stay compatible with existing implementation, and allow an easy convergence for libraries using different patterns.

This could be improved by additionnal cargo metadata.

#### Draft proposal

- Split third-party code inclusion into dedicated separate crates, and name them with the `-src` suffix
- Use the upstream version as crate build version. This means that the crate version needs to be incremented for each upstream update (as already done for `openssl-src`). The problem is that it makes version requirements in dependant crates less readable (as the upstream version is not part of it). It could a plus though, as a lot of projects don't use semver versionning.
- Add a reference to the included code in the cargo metadata TODO
- Use a common behavior for static linking in libraries, including feature naming

This would allow:

- To improve discoverability and help library authors who want to allow statically linking a dependency
- To know when a static library is included, directly from `cargo-tree`
- To file RustSec advisories for vulnerabilities in upstream libraries (like already done for `openssl-src`). We could automate detection based on CVEs for common libraries, and integrate directly with `cargo-audit` and `cargo-deny`

#### Question

does a crate licnese need to match all files included in the crate?

* Use submodules or not? a repo with submodules is no longer defined by its commit hash, which makes reproducibility a
lot harder. Also, it turns out that C/C++ projects often have different contents in git compared to
release tarballs, and require different procedures to build from git vs release tarballs.

Hmm, how should the version synchronization between -sys and -src crates be handled? Is there a way
to specify "I want -src version X" even though you don't depend on it directly? If not, should -sys
and src crates be published together and always have the same version to allow selecting a specific
version of -src crate?

#### Limitations / Cons

* This would add a burden on the maintainers (more crates to maintain, more versions to release, etc.)
* If the `-src` contains dedicated code to build the included code, it is a problem is licensed under a license different from the included code
* There is no standard way to designate a piece of software, espacially C/C++ libraries. It could be a link to a Git repository. TODO
* putting the upstream version in build metadata (i.e. after +) is not a great idea because
according to the semver spec there is no defined ordering for versions that only differ by build metadata. Meaning it might not be possible to match on some build versions but not others, which
would be necessary for RustSec. But that's details.

### Improve tooling

Cargo-based tooling could get some knowledge to detect `-src` crates and implement special handling (extract upstream version, etc.).

This could allow implementing correct [SBOM](https://www.cisa.gov/sbom) (like [cargo-spdx](https://github.com/alilleybrinker/cargo-spdx)).

automatic import of new releases, automatic import of CVEs to RustSec, etc

another thing I've lamented is how much e.g. curl versions lag behind upstream, even in case of
critical security fixes. We could build automated infrastructure for updating library versions: new
release tarballs could be pulled automatically, and with a bit of work even published automatically:
we could run crater on the dependencies of the crate before and after the update, if all tests pass
then publish it without requiring manual review. I believe @HeroicKatora has been working on a
"crater for your dependencies" kind of tool
