# Verification record — React migration

Checked on 30 October 2026. Python 3.14.0, Node 24.11.1; no estimator fitting or
inference was performed on this device.

## Verified

- `python -m pytest -q`: **46 passed**. Tests cover strict source/data validation,
  real returned-case integrity, CSV/JSON result imports, complete study bundle
  import, actual regional aggregation, current notebook syntax/guard and the
  FastAPI endpoint contract, including no-data and malformed-upload behavior.
- `npm test` in `frontend`: **7 passed**. These cover line gaps, matched metrics,
  chronological descriptive slopes, CSV escaping/nulls, selected target/region
  filters, numeric observation counting and cross-target metadata separation.
- `npm run test:render`: all four populated React views render using the actual
  validated study. Regression scenarios cover sparse history, model availability
  fallback, provenance, target-specific labels and missing observations. This
  does not simulate browser layout or claim browser interaction testing.
- `npm run build`: production native esbuild build succeeds. JS approximately
  244 KB and CSS approximately 35 KB before HTTP compression. No CDN or external
  font/image request is required by the interface.
- The local HTTP API serves actual observations and downloadable CSV results.
  Live checks returned HTTP 200 for production JS/CSS, the current notebook and
  the analysis report, validated the 31/15 observation/forecast counts, checked
  forecast CSV labels, and confirmed invalid ZIP import returns HTTP 400.
  The source notebook's saved outputs show a completed Colab run; its original
  SHA-256 input matches the returned manifest and provided CSV.
- Independent static review identified target-label, null-observation,
  cross-target coverage and unavailable-model issues. Regression checks were
  added and those issues were corrected.
  Follow-up review confirmed the fixes; source period/date labels were also
  restricted to the selected modeling target.

## Scientific evidence

### Compact dashboard and parameter help (30 October 2026)

Shortened view and panel headings, removed repeated prose and permanent metric
captions, and collapsed model methodology into a native disclosure. Important
values and table parameters now expose brief descriptions through hover, keyboard
focus, or tap. Help supports Escape, outside-tap dismissal, viewport positioning,
pointer movement into the description, and reduced motion. Experimental labels,
source access, and missing-data states remain visible.

Render regressions verify accessible description links on metric values and table
headings/cells, the MAE/RMSE definitions, retained eligibility context, and initially
collapsed methodology. The production build and seven frontend logic tests pass.
The optional CDP script now includes keyboard, hover, and touch help checks; these
interaction checks have not run here because of the existing browser IPC restriction.

407 national observations, 95 countries, 31 eligible regional medians over
2016–2022; nine backtest rows and 15 experimental 2023 forecast rows. The 2022
holdout compares five identical cases per method. Naïve MAE 9.612 pp; linear
11.816933 pp; Ridge 12.247360 pp. These are returned Colab results validated with
arithmetic, not a local rerun of the experiment. Source authenticity/publication
revision remain explicitly user-supplied/unknown in provenance.

## Verification limits

Chrome and Edge are installed, but dedicated headless processes fail during
Windows Mojo/Crashpad IPC creation with Access Denied. Browser screenshots and
live desktop/mobile visual checks could not be completed. A single-process
headless attempt also could not expose a debugging endpoint. No sandbox
elevation or user-browser session was used. An optional CDP browser smoke script
is provided for an unrestricted environment.

The package index is unavailable in this environment; exact existing npm cache
tarballs supplied React/esbuild and their runtime dependencies. The Python/native
build wrapper avoids Node's blocked piped child process. This is distinct from
real-browser QA and is not represented as visual verification.

Streamlit-only tests and stale references to the removed notebook filename were
replaced with checks for the current React API and user's executed notebook.
The notebook and original Colab export have not been modified by this migration.
