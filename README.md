https://amousset.github.io/source-crates/ https://rust-lang.github.io/rfcs/2856-project-groups.html

- Feature Name: `external_source_crates`
- Start Date: 2021-08-08

# Summary

One paragraph explanation of the feature.

# Motivation

Why are we doing this? What use cases does it support? What is the expected outcome?

# Guide-level explanation

Explain the proposal as if it was already included in the language and you were teaching it to
another Rust programmer. That generally means:

- Introducing new named concepts.
- Explaining the feature largely in terms of examples.
- Explaining how Rust programmers should *think* about the feature, and how it should impact the way
  they use Rust. It should explain the impact as concretely as possible.
- If applicable, provide sample error messages, deprecation warnings, or migration guidance.
- If applicable, describe the differences between teaching this to existing Rust programmers and new
  Rust programmers.

For implementation-oriented RFCs (e.g. for compiler internals), this section should focus on how
compiler contributors should think about the change, and give examples of its concrete impact. For
policy RFCs, this section should provide an example-driven introduction to the policy, and explain
its impact in concrete terms.

# Reference-level explanation

This is the technical portion of the RFC. Explain the design in sufficient detail that:

- Its interaction with other features is clear.
- It is reasonably clear how the feature would be implemented.
- Corner cases are dissected by example.

The section should return to the examples given in the previous section, and explain more fully how
the detailed proposal makes those examples work.

# Drawbacks

Why should we *not* do this?

# Rationale and alternatives

- Why is this design the best in the space of possible designs?
- What other designs have been considered and what is the rationale for not choosing them?
- What is the impact of not doing this?

# Prior art

Discuss prior art, both the good and the bad, in relation to this proposal. A few examples of what
this can include are:

- For language, library, cargo, tools, and compiler proposals: Does this feature exist in other
  programming languages and what experience have their community had?
- For community proposals: Is this done by some other community and what were their experiences with
  it?
- For other teams: What lessons can we learn from what other communities have done here?
- Papers: Are there any published papers or great posts that discuss this? If you have some relevant
  papers to refer to, this can serve as a more detailed theoretical background.

This section is intended to encourage you as an author to think about the lessons from other
languages, provide readers of your RFC with a fuller picture. If there is no prior art, that is fine
\- your ideas are interesting to us whether they are brand new or if it is an adaptation from other
languages.

Note that while precedent set by other languages is some motivation, it does not on its own motivate
an RFC. Please also take into consideration that rust sometimes intentionally diverges from common
language features.

# Unresolved questions

- What parts of the design do you expect to resolve through the RFC process before this gets merged?
- What parts of the design do you expect to resolve through the implementation of this feature
  before stabilization?
- What related issues do you consider out of scope for this RFC that could be addressed in the
  future independently of the solution that comes out of this RFC?

# Future possibilities

Think about what the natural extension and evolution of your proposal would be and how it would
affect the language and project as a whole in a holistic way. Try to use this section as a tool to
more fully consider all possible interactions with the project and language in your proposal. Also
consider how this all fits into the roadmap for the project and of the relevant sub-team.

This is also a good place to "dump ideas", if they are out of scope for the RFC you are writing but
otherwise related.

If you have tried and cannot think of any future possibilities, you may simply state that you cannot
think of anything.

Note that having something written down in the future-possibilities section is not a reason to
accept the current or a future RFC; such notes should be in the section on motivation or rationale
in this or subsequent RFCs. The section merely provides additional information.

Case study openssl-src le mieux pour l'instant

etude quantitative et qualitative

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


# NOTES

TODO parallele avec vendoring



I agree with pretty much everything! That sounds like something I would have done, and I mean that
in the best possible way. I believe the problem is real and what you propose is a reasonable
solution. I'm not entirely sold on having the license and upstream repo metadata in a third-party
repository. I'd rather have it right in the -src crate. I wonder if we can (ab)use the existing
Cargo.toml format for that? After all, it is needed for an upload to crates.io regardless, and e.g.
openssl-src ships it.

I'm also not convinced that submodules are a good idea. There are a lot of pitfalls around them; for
one, a repo with submodules is no longer defined by its commit hash, which makes reproducibility a
lot harder. Also, it turns out that C/C++ projects often have different contents in git compared to
release tarballs, and require different procedures to build from git vs release tarballs.

I strongly support the -src crate convention, for all the reasons you've listed. Automatic detection
of CVEs sounds great, and relatively easy to implement.

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

I believe the best way to make progress on this is get a project group going. You can find out more
about those here The goals would be something along the lines of creating guidelines for handling
externally imported code and developing the supporting tooling (automatic import of new releases,
automatic import of CVEs to RustSec, etc) Or, in terms of problems rather than solutions - make it
easier to import C/C++ code in a secure and reliable manner and keep it up-to-date

I would be happy to act as the liason for RustSec and cargo-supply-chain, but my availability during
the rest of the summer may be spotty.

Oh, putting the upstream version in build metadata (i.e. after +) is not a great idea because
according to the semver spec there is no defined ordering for versions that only differ by build
metadata. Meaning it might not be possible to match on some build versions but not others, which
would be necessary for RustSec. But that's details.
