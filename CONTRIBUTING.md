# Contributing to AMR Sentinel

Start with a data-free check. Python tests cover source validation and synthetic study contracts; frontend tests cover chart data and exports.

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
cd frontend
npm ci
npm test
npm run build
```

A complete local Colab export unlocks the optional integration tests. Do not commit the WHO source CSV, national observations, model outputs, OneDrive files, browser profiles, or generated builds. If a change affects a resistance percentage, keep the indicator definition, percentage scale, region mapping, year, and denominator visible in the pull request. Compare forecasts on identical cases and keep observed values separate from projections.

Open an issue with a synthetic reproduction for ordinary bugs. For a security report, use [SECURITY.md](SECURITY.md).
