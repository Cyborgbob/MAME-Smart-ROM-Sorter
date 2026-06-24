# GitHub Upload Checklist — MAME Smart ROM Sorter v5.0

## Release assets

- [ ] Upload `MAME_Smart_ROM_Sorter_v5.0.exe`.
- [ ] Upload `MAME_Smart_ROM_Sorter_v5.0_Source.zip`.
- [ ] Upload `SHA256SUMS.txt`.

## Repo root files

- [ ] Copy `README.md` or `readme.md` into the GitHub repo root.
- [ ] Copy `CHANGELOG.md` into the GitHub repo root.
- [ ] Copy `LICENSE` into the GitHub repo root. This is the MIT source-code license.
- [ ] Copy `LICENSE_OVERVIEW.md` into the GitHub repo root. This explains the split-license model.
- [ ] Copy `ASSET_LICENSE_NOTES.md` into the GitHub repo root.
- [ ] Copy `THIRD_PARTY_NOTICES.md` into the GitHub repo root.
- [ ] Confirm the README license section says: MIT code, CC BY-NC-SA docs, TNT/assets reserved.
- [ ] Confirm public docs say no ROMs, BIOS files, CHDs, samples, or download sources are included.

## Release page

- [ ] Title: `MAME Smart ROM Sorter v5.0 — Stop Sorting ROMs Manually`.
- [ ] Use `docs/GITHUB_RELEASE_BODY_v5.0.md` as the release body draft.
- [ ] Mention non-merged MAME ROM set recommendation.
- [ ] Mention feedback will shape v5.5.
- [ ] Do not over-explain the Easter egg.

## README / repo polish

- [ ] Confirm whether old v4.x screenshots are acceptable for launch or replace them with v5.0 screenshots.
- [ ] Confirm download links point to the v5.0 GitHub release after upload.
- [ ] Confirm TNT/channel links are correct.

## Final smoke check

- [ ] EXE launches.
- [ ] App can select/source folders.
- [ ] App can run a known-good test case.
- [ ] Output folder and logs are created.
- [ ] Source ZIP includes presets, preset images, icons, sounds, and the PyInstaller spec file.
- [ ] No `__pycache__`, `.pyc`, local test logs, ROMs, BIOS files, CHDs, or samples are inside the release docs/source package.
