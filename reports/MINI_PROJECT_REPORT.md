# AMR Sentinel: regional antibiotic resistance surveillance analytics

## Abstract and research question

AMR Sentinel examines whether pooled Ridge regression improves one-year forecasts
of reported regional E. coli bloodstream resistance percentages over transparent
baselines. A user-run Colab analysis supplied 407 national observations from 95
countries over 2016–2022. These produced 31 eligible derived regional medians.
On five matched regional holdout cases for 2022, naïve carry-forward had lower
MAE and RMSE than linear trend and Ridge. The React interface displays these
observations, limitations and returned forecasts; no local predictive fitting or
inference is performed.

## Data and statistical meaning

The input `745F475_ALL_LATEST.csv` was supplied by the user after downloading
WHO's [E. coli SDG 3.d.2 indicator](https://data.who.int/indicators/i/918081E/745F475).
The source describes third-generation-cephalosporin resistance among tested
bloodstream infections. The CSV has 421 rows and uses `RATE_PER_100_N` percentages
and M49 geography identifiers. Original bytes and SHA-256 hashes are retained.
Publisher authenticity and the file's publication revision have not been
independently authenticated; the manifest labels this explicitly.

The notebook excludes non-country geography rows and three unmapped country
observations with identifier `412`, leaving 407 national country/year values.
It uses its embedded May 2025 WHO region lookup, whose historical memberships
may differ. Country/year percentages are aggregated as unweighted regional
medians only when at least five countries report. All six WHO regions have some
eligible observations, but their usable histories differ.

These **derived_country_median** series are separate from the official GLASS
dashboard regional medians and WHO-adjusted estimates. They are not population
prevalence. Unknown infection/testing counts cannot reproduce WHO's chart
eligibility algorithm. Reporting-country composition and coverage are retained
as analytical context; changing composition can change a median.

## Methods

Annual change is measured in percentage points and requires adjacent observed
years. Slopes use at least three consecutive observations. Direction thresholds
of ±1 pp/year are descriptive application heuristics, not significance tests.

Main one-step evaluation cases require four consecutive prior observations.
Naïve uses the preceding observation; linear extrapolates the uninterrupted
history. Pooled Ridge uses year, two annual lags, their difference and one-hot WHO
region, with numeric scaling and encoding fitted inside the training pipeline.
Rows and transformations use only years before each target year. Chronological
validation precedes the final untouched 2022 holdout. Ridge required at least 12
complete training rows across three regions; default alpha 1 was used because
earlier Ridge validation coverage was insufficient for tuning.

Errors use the same five held-out regional cases for every method, with
percentages consistently bounded to [0,100] and clipping diagnostics retained.
Final preferred-method selection uses pre-holdout validation. Final projections
refit in Colab on permitted history only; there are no manufactured confidence
intervals.

## Results

The source/processed hashes, regional medians and counts, chronological case set,
actual holdout values, prediction boundaries and matched error calculations pass
local checks without re-running an estimator.

| Model | Holdout MAE (pp) | Holdout RMSE (pp) | Matched cases |
|---|---:|---:|---:|
| Naïve carry-forward | 9.612 | 11.604 | 5 |
| Linear trend | 11.817 | 15.277 | 5 |
| Ridge regression | 12.247 | 14.781 | 5 |

The eligible 2022 holdout regions were AFR, EMR, EUR, SEAR and WPR. AMR had only
two eligible annual regional observations and was excluded from the main
forecast/evaluation. Ridge did not improve over naïve on these matched cases.
This small single-year comparison does not establish broad predictive superiority.

The returned forecast table has 15 rows: three methods across five regions,
projecting **2023** from histories ending in **2022**. Those points remain
experimental and are not observed WHO 2023 values or current-year forecasts.

The complete Colab report, national EDA, country participation/composition,
figures, observations, backtests and forecasts are preserved under
`notebooks/amr_project_bundle/`. The user-updated notebook retains its executed
outputs and `RATE_PER_100_N` mapping patch.

## React application and reproducibility

The dashboard replaces Streamlit with React and a local FastAPI plain-data
service. Its four views cover regional comparison, historical trends,
experimental forecasts and chronological evaluation. A source/data-quality dialog
shows definitions, counts, missingness, exclusions and provenance. Filters and
CSV exports share the selected target, years and regions. Line gaps remain
visible; projected diamonds are distinct from observed points. Raw import and
complete Colab study imports reuse the Python validation contracts and do not
load fitted artifacts.

Automated API, data-function and React rendering checks pass. Real-browser
visual/mobile QA is unverified in this restricted environment because installed
browsers fail during Windows IPC initialization. The implementation includes
responsive layouts, keyboard focus and reduced-motion rules, but those checks
are not presented as proof of browser visual quality.

## Limitations and conclusion

Short histories, a five-case holdout, unknown infection counts, static region
membership, unmapped identifiers and changing surveillance participation limit
interpretation. Differences may reflect surveillance changes rather than changes
in underlying resistance. The study provides no clinical recommendations,
patient-level risks, outbreak alerts, causal estimates or validated current-year
predictions. The observed result favors a simple baseline in this particular
study; it does not imply that additional model complexity will improve accuracy.

References: [WHO GLASS](https://worldhealthorg.shinyapps.io/glass-dashboard/),
[WHO E. coli indicator](https://data.who.int/indicators/i/918081E/745F475),
[WHO 2025 report](https://www.who.int/publications/i/item/9789240116337).
