use regex::Regex;
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, fs, io::prelude::*, path::Path, process::Command, time::Duration};

const DB_FILE: &str = "../db/source-crates.toml";
const TMP_REPOS: &str = "target/repos";

/// What this program does:
///
/// * load existing db
/// * find src crates in the crates index
/// * get information from crates.io API
/// * get information from advisory db
/// * clone repositories and get information about submodules
/// * update and extend the database
/// * render a dashboard about their current state

/// Data is currently very partial, due to hidden static binaries.
type SourceCrates = HashMap<String, SourceCrate>;

/// Information about the vendored third-party code
/// in a source crate.
#[derive(Deserialize, Serialize, Default)]
struct SourceCrate {
    comment: Option<String>,
    upstream_license: Option<String>,
    upstream_repository: Option<String>,
}

fn main() {
    // Read existing db to reuse existing content
    let db_path = Path::new(DB_FILE);
    let mut db: SourceCrates = if db_path.exists() {
        toml::from_str(&fs::read_to_string(db_path).unwrap()).unwrap()
    } else {
        HashMap::new()
    };

    let client = crates_io_api::SyncClient::new(
        "src-crates (https://github.com/amousset/source-crates)",
        Duration::from_secs(1),
    )
    .unwrap();

    // Update crates index
    let index = crates_index::Index::new_cargo_default();
    index.retrieve_or_update().unwrap();

    // Heuristic to find new source crates
    // Current source crates + crates containing "-src"
    /*
    for detected_crate in index
        // TODO: very inefficient way to get all crate names
        .crates()
        .filter(|c| c.name().contains("-src"))
        .map(|c| c.name().to_owned())
    {
        if !db.contains_key(&detected_crate) {
            // Add missing src crates
            db.insert(detected_crate.to_owned(), SourceCrate::default());
        }
    }
    */

    // Directory where to clone source crates repositories
    fs::create_dir_all(Path::new(TMP_REPOS)).unwrap();

    // Update crates information
    for (crate_, info) in db.iter_mut() {
        println!("Updating {}", crate_);
        let _index_info = index.crate_(crate_).unwrap();

        let api_info = client.get_crate(crate_).unwrap();
        let _downloads = api_info.crate_data.downloads;
        let _updated_at = api_info.crate_data.updated_at;

        let crate_repo = Path::new(TMP_REPOS).join(crate_);

        // Try to clone/update repository
        if let Some(repository) = api_info.crate_data.repository {
            if !crate_repo.exists() {
                println!("Cloning repo {}", crate_);
                Command::new("git")
                    .args(&["clone", "--depth", "1", &repository, crate_])
                    .current_dir(TMP_REPOS)
                    .status()
                    .unwrap();
            } else {
                println!("Updating repo {}", crate_);
                Command::new("git")
                    .args(&["pull"])
                    .current_dir(TMP_REPOS)
                    .status()
                    .unwrap();
            }
        }

        // Collect information from repository
        if crate_repo.join(".gitmodules").exists() {
            // Get submodule information
            let output = Command::new("git")
                .args(&["config", "-f", ".gitmodules", "-l"])
                .current_dir(crate_repo)
                .output()
                .unwrap();
            for property in String::from_utf8(output.stdout).unwrap().lines() {
                let url_regex = Regex::new(r"^submodule\..+\.url=(.+)$").unwrap();
                if let Some(caps) = url_regex.captures(property) {
                    let url = caps.get(1).unwrap().as_str();
                    println!("Setting repo {}", url);
                    info.upstream_repository = Some(url.to_owned());
                }
            }
        }
    }

    let mut out = fs::File::create(db_path).unwrap();
    out.write_all(toml::to_string(&db).unwrap().as_bytes())
        .unwrap();
}
