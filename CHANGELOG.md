# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),

## [2.0.0] - 2026-08-18

### Added
- Add GitHub Pages documentation site built with VitePress (`docs/`), published via `.github/workflows/docs.yml`
- Add per-version documentation with a version switcher (`dev`, `stable`, and tagged releases), deployed to the `gh-pages` branch

### Changed
- `$id` changed from `.../ClinicalCohortDefinitionLanguage/v1/schema` to `.../ClinicalCohortDefinitionLanguage/v2/schema`; the schema URI now only changes on breaking releases instead of every release. Only affects consumers that resolve the schema by its `$id` URL rather than fetching the latest version
- **Breaking:** `version` is now a fixed `const` value (`"2"`) instead of a free-form URI-typed string; it no longer follows semver and only changes when the schema's major version changes, so existing documents must update their `version` value to `"2"`
- Removed `additionalProperties: false` from the schema and all its definitions; documents with unrecognized properties are no longer rejected
- Move CCDL documentation and CCDL generator usage instructions out of `README.md`/`documentation/Documentation.md` into the docs site; `README.md` now links to it
### Deprecated
### Removed
### Fixed
### Security

## [1.0.0] - 2024-03-15

### Added
- Add `Changelog.md`
- Add `Development.md`
- Add CCDL generator
- Add meta profiles for CCDL generator
- Add test data for CCDL generator
- Add tests for CCDL generator
- Add github workflow for testing CCDL generator
    
### Changed
- Change SQ to CCDL
- Update Readme
- Update Documentation
- Update example CCDL
- Update json schema
- Rename and move files for better file structure
