# Changelog

## v5.0 — Release Candidate / Public Release Package

### Added / improved

- Refactored sorter logic into cleaner engine, GUI, and shared modules.
- Added stronger preset workflow for different cabinet/controller goals.
- Added cleaner v5.0 release packaging plan for GitHub.
- Added preset sanitation expectation for public release packages.
- Improved output/log review workflow.
- Preserved the app's personality and TNT branding while keeping public docs clear.

### Important release notes

- Public release package should be clean and GitHub-ready, not a raw build folder.
- Release assets should include:
  - `MAME_Smart_ROM_Sorter_v5.0.exe`
  - `MAME_Smart_ROM_Sorter_v5.0_Source.zip`
- Public docs must clearly state that the project does not include ROMs, BIOS files, CHDs, samples, or download sources.

### Known limitations

- MAME metadata and ROM-set structure can still create edge cases.
- Non-merged sets are strongly recommended.
- Users are responsible for their own legal files and testing.

## Earlier project history

This project evolved from a script-based MAME ROM filtering helper into a GUI-focused arcade ROM curation tool. Earlier development work established XML-based MAME metadata parsing as more reliable than relying only on older control/category support files.
