# Materials, experiments, theory and ML probes

Apply the relevant probes; record why others do not apply. Do not impose random splitting, p-values or a predictive-model benchmark on a proof or literature study.

## Physical and chemical validity

- Define measured property versus proxy, measurement conditions (temperature, pressure, frequency, geometry, phase, orientation), units and transformation/inverse transformation. Compare like conditions.
- Check dimensions, signs, bounds, stoichiometry, charge balance, conservation, symmetry, boundary/initial conditions and limiting behavior where relevant. Identify which are hard constraints, approximations or empirical tendencies.
- Distinguish thermodynamic stability, kinetic accessibility, synthesis feasibility and measured functionality. A low predicted energy or formally valid composition is insufficient for all four.
- Trace instrument/background corrections, calibration, detection limits, saturation, noise floor, drift, sample preparation and batch/laboratory effects. Technical repeats cannot inflate the number of independently prepared materials.
- For simulations/theory, inspect model approximations, discretization/time-step/k-point/cutoff or solver convergence as relevant, finite-size effects, parameter sensitivity and numerical versus physical error. A solver finishing is not an independent benchmark against reality.
- For transport/conductivity, distinguish conductivity/resistivity, tensor/scalar, bulk/grain-boundary/contact contributions and measurement conditions. Do not assume an Arrhenius law or a single mechanism without checking regime and residuals. Inverse/log transforms change error interpretation.

## Predictive modelling and comparisons

Use existing strict leakage/reproducibility gates. Additionally inspect:

- Independent sample/group/structure/composition/source/batch units; multiple temperatures or fidelities for the same material must not bypass the intended holdout. Distinguish interpolation, new condition, new composition and new chemistry/structure.
- Fair baselines: simple/domain baseline, data-only, physics-only and integrated models as relevant; matched information, split, tuning opportunity, search budget and cost. A large candidate model versus an untuned weak baseline does not isolate a contribution.
- Ablations and sensitivity: remove the proposed contribution, vary consequential preprocessing, data quantity, priors and partition schemes. Avoid inspecting the final test to choose the favorable variant.
- Report paired effects on independent units, appropriate uncertainty and failure cases. Fold/seed dispersion captures particular variability and is not automatically a population confidence interval. Avoid thresholds as the sole decision criterion.
- Evaluate residuals, subgroup/regime behavior, outliers and data-density effects. Feature/target overlap, near duplicates and source artifacts can explain performance.
- UQ: separate measurement noise, model uncertainty and sampling variability; assess interval coverage/sharpness or suitable calibration on held-out data, including the claimed deployment domain. GP/ensemble variance alone does not demonstrate calibration.
- Interpretation: correlated descriptors and proxy variables can produce unstable explanations. SHAP/importance explains a fitted model under assumptions, not a causal mechanism. Compare models and independent mechanistic evidence.

## Multi-fidelity and data assimilation

State fidelity-specific targets, observation operators, state/parameters, error covariance/bias, discrepancy model and update assumptions. “High fidelity” is relative to the quantity/conditions and may still be biased. Audit data reuse/double counting and identifiability; inspect posterior sensitivity to priors and errors. Check low-only, high-only and integrated baselines under comparable access/cost. Validate assimilation on independent withheld observations, not just the data assimilated. More low-fidelity data need not improve a mismatched model.

## Bayesian optimization and discovery

Inspect objective units/direction, meaningful multi-objective tradeoffs, feasibility/domain constraints, acquisition definition and exploration/exploitation. The next point is not necessarily maximum uncertainty: verify the actual acquisition and plotting convention. Nominal labels are not numeric distances. Compare fixed-cost random/domain baselines and repeats as feasible. Separate retrospective replay, candidate recommendation, novelty search, synthesis and prospective independent measurement. Candidate novelty requires a bounded prior-art/training-overlap search; predicted improvement is not a validated discovery.

## Alternative experiments

For each material competing explanation, propose an intervention/control/measurement with different predicted outcomes. Include independent batches, another instrument/source/conditions, negative controls and boundary cases where appropriate. Specify feasibility, time/cost, safety/approval constraints already applicable, and how each outcome changes the central claim. Prefer the smallest experiment that resolves the most consequential uncertainty.
