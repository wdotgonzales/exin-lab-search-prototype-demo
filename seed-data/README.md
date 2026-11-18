# Seed data

**Fictional demo data generated for Exin Lab Search. Not real experimental results.** It imitates a small neuroscience lab so Exin Lab Search has realistic, linked files to ingest.

## The world
- 60 mice (`M-001` to `M-060`) in cohorts `C-01` to `C-08`
- Virus batches `V-011` to `V-020` (AAV vectors), experiments `EXP-001` to `EXP-009`
- The same IDs appear across PDFs, Word notes, spreadsheets, CSVs and Markdown, as in a real lab

## Files (22)
- `data/C-07_imaging_session_log.xlsx`
- `data/EXP-003_behaviour_scores.xlsx`
- `data/EXP-005_open_field_scores.xlsx`
- `data/EXP-007_dosing_schedule.csv`
- `data/EXP-009_photometry_summary.csv`
- `data/animal_weights_2026-10.csv`
- `data/mouse_colony_roster.xlsx`
- `data/virus_batches.csv`
- `notes/EXP-009_photometry_pilot_notes.docx`
- `notes/incident_2026-10-14_M-045_window.md`
- `notes/lab_id_conventions.md`
- `notes/lab_meeting_2026-10-22.docx`
- `notes/surgery_notes_2026-08_C-03.docx`
- `notes/surgery_notes_2026-09_C-07.docx`
- `notes/two-photon_microscope_log.txt`
- `notes/weekly_summary_2026-W41.md`
- `notes/weekly_summary_2026-W43.md`
- `protocols/EXP-003_protocol_optogenetic_stimulation.pdf`
- `protocols/EXP-007_protocol_two-photon_imaging.pdf`
- `protocols/SOP-02_stereotaxic_viral_injection.pdf`
- `reports/EXP-004_XN-214_dose_finding_summary.pdf`
- `reports/EXP-007_interim_report_2026-10.pdf`

## Ground truth (for testing search and Ask)
| Question | Expected answer |
|---|---|
| Which virus batch was M-042 injected with? | V-017 (AAV9-hSyn-jGCaMP8m), on 9 Sep 2026, left mPFC. |
| Which cohort is M-042 in? | C-07 (EXP-007, mice M-037 to M-048). |
| Why was M-045 excluded from EXP-007? | Its cranial window clouded on 14 Oct 2026, so imaging quality was too poor. |
| What happened to virus batch V-014? | It failed QC (titre 3.1e11 vg/mL, far below spec) and was discarded; V-016/V-017 replaced it. |
| What did XN-214 do to mPFC activity in EXP-007? | At 3 mg/kg, calcium event rate fell about 31% on average versus vehicle (M-042: about 34%). |
| Which virus is used for dopamine photometry? | V-019 (AAV9-hSyn-GRAB-DA3m) in EXP-009, cohort C-08. |
| Which mouse lost its headcap in EXP-003? | M-019, on 30 Aug 2026; it was removed from the study. |
| What dose of XN-214 was chosen after dose-finding? | 3 mg/kg i.p.; 10 mg/kg reduced locomotion (EXP-004). |
