# Ionic conductivity dataset (fictional)

Conductivity of polymer electrolyte films with a salt additive, merged from two laboratories.

- `sample_id`: film identifier. Each film was measured four times (`replicate` 1–4) at nominally the same temperature.
- `source`: laboratory. Lab A logs temperature in degrees Celsius. Lab B's instrument logs temperature in kelvin.
- `temperature`: measurement temperature as logged by each laboratory's instrument.
- `additive_wt_pct`: salt additive content (wt%).
- `conductivity_mS_cm`: ionic conductivity (mS/cm).

The two laboratory exports were concatenated without further processing.
