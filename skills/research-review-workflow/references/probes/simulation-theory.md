# Simulation and theory probes

概要(日本語): 数値シミュレーション、解析的理論、数理モデルの研究で確認する項目です。極限との一致、収束、境界条件、保存則を点検します。

> 注意: この確認項目は文献と一般的な指針から合成した目安で、この分野の専門家による確認はまだ受けていません。分野の慣習と食い違う場合は、指導教員や専門家の判断を優先してください。

Apply to numerical simulations, analytic derivations and mathematical or physical models.

- **Limiting cases**: the model reproduces known analytic solutions or established results in the limits where they apply. A model that cannot recover a known limit needs an explanation.
- **Convergence**: mesh, grid, time step, particle number or basis size refined until the quantity of interest changes little; report the convergence study, not only the final run.
- **Boundary and initial conditions**: stated explicitly, physically justified, and tested for sensitivity. Artificial boundaries that drive the result need to be identified.
- **Conservation and symmetry**: mass, energy, momentum, charge or probability conserved where expected; symmetry used in the model is actually present in the problem.
- **Dimensional analysis**: dimensionless groups identify the regimes; conclusions are stated in those terms when scale matters.
- **Parameter sensitivity**: which parameters drive the result, their uncertainty, and whether the conclusion survives plausible ranges.
- **Verification versus validation**: verification asks whether the code solves the equations correctly; validation asks whether the equations describe reality. A converged solver is not an experimental comparison.
- **Reproducibility**: code version, random seeds, solver settings and computing environment recorded; results regenerated from the stated inputs.
- **Assumptions**: each simplifying assumption listed with the effect of relaxing it, if known.
- **Tools** (optional, `requirements/base.txt`): `tools/dimcheck.py` for dimensional consistency of model equations.
