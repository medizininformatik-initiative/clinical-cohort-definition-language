# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),

## [UNRELEASED] - yyyy-mm-dd

### Added
- Add GitHub Pages documentation site built with VitePress (`docs/`), published via `.github/workflows/docs.yml`
### Changed
- **Breaking:** `$id` changed from a full-semver URL to a major-only one (`.../ClinicalCohortDefinitionLanguage/v2/schema`), so the schema URI only changes on breaking releases
- **Breaking:** `version` is now a semver string matching `^2\.\d+\.\d+$` instead of a free-form URI-typed string; existing documents must update their `version` value to a `2.x.y` release
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
