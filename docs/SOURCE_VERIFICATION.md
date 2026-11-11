# WHO source verification — 29 October 2026

Reviewed official pages S1–S5 in the project spec:

- [S1 GLASS dashboard](https://worldhealthorg.shinyapps.io/glass-dashboard/):
  displayed update 25 September 2025, observations 2016–2023 submitted through
  end-2024. Underlying chart data are described as downloadable. Time-series
  selection is interactive, and this environment did not obtain a regional export.
  Time-series notes specify ≥10 infections with AST in ≥70% of years per CTA;
  median/IQR available with ≥5 CTAs.
- [S2 2025 report](https://www.who.int/publications/i/item/9789240116337):
  publication page displays 13 October 2025. Report modeling is separate from
  the unadjusted dashboard series and is not used as a training target.
- [S3 program overview](https://www.who.int/initiatives/glass): official system
  context, not itself a table of observations.
- [S4 E. coli](https://data.who.int/indicators/i/918081E/745F475) and
  [S5 MRSA](https://data.who.int/indicators/i/918081E/5DD9606): confirmed bloodstream
  indicator definitions, official estimate update 7 May 2025. A linked national
  CSV was found at the E. coli page. Browser extraction could not parse its CSV
  content; direct Python retrieval failed because the configured network proxy
  refused the connection. No national observations or mapping were imported.

Consequences: use the documented manual regional export/import path. Do not
report data coverage, resistance values, scores or forecasts until authentic
files are supplied. `data/source_manifest.json` currently lists zero inputs.
No claim is made that the primary regional target is downloadable or ML-eligible
until its actual chart export can be inspected. Recheck revision on download.

## End-to-end notebook acquisition revision

The notebook now implements the explicitly allowed national SDG fallback. The
official E. coli page identifies code **AMR_INFECT_ECOLI / 5751**, defines the
percentage scale and exposes the CSV download link. The notebook discovers that
link, retains its original payload and uses the verified blob URL as fallback.
If unavailable, it tries the corresponding documented GHO indicator route and
checks the returned indicator identity. This is not a claim that a live GHO
response was acquired in the implementation environment.

WHO's API documentation identifies COUNTRY/DimensionValues as the country
metadata route. The notebook uses explicit parent WHO region codes and a WHO
REFMART metadata fallback, validating actual returned fields and complete mapping.
It rejects missing or unknown mappings rather than guessing geographic regions.
Region codes use the metadata obtained at runtime, not a reconstructed historical
membership series; this limitation is recorded in the report.

Live endpoint availability and returned CSV headers remain to be confirmed in
Colab. Failed requests/schema changes produce diagnostics. No model findings or
actual acquisition success are claimed from offline schema tests.
