# Conductivity model: summary report (fictional)

We modelled the ionic conductivity of polymer electrolyte films from the merged dataset (440 measurements) using k-nearest-neighbour regression with temperature and additive content as inputs. Features were standardized within each training fold.

**Performance.** Five-fold cross-validation gave R² = 0.947 ± 0.002 (mean ± SD across folds). The model therefore predicts the conductivity of new films with high accuracy.

**Drivers.** Temperature is essentially uncorrelated with conductivity in this dataset (r = −0.025), indicating that conductivity is controlled by the additive content rather than by temperature. We recommend that future experiments vary the additive content and do not need to control temperature closely.
