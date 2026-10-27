# Physics and engineering measurement probes

概要(日本語): 物理・機械・電気・土木などの測定と工学的設計で確認する項目です。単位、誤差、有効数字、校正、スケーリングを点検します。

> 注意: この確認項目は文献と一般的な指針から合成した目安で、この分野の専門家による確認はまだ受けていません。分野の慣習と食い違う場合は、指導教員や専門家の判断を優先してください。

Apply to measurements, instrumentation, device or structural experiments and engineering analysis.

- **Units and dimensions**: every quantity has a unit; equations are dimensionally consistent; conversions are correct; log or exponential fits are interpreted with the right error model.
- **Uncertainty**: type A and type B uncertainty, error propagation (first-order or Monte Carlo), correlated errors, and whether reported uncertainties are standard or expanded (k factor).
- **Calibration and traceability**: calibration date and standard, zero offset, drift, sensor linearity, and whether calibration covers the measurement range.
- **Significant figures**: reported digits match the precision of the measurement; avoid spurious digits from software output.
- **Signal quality**: signal-to-noise ratio, sampling rate versus signal frequency (aliasing), filtering that changes the result, and detection or quantification limits.
- **Scaling and similitude**: whether scaled models (wind tunnel, small specimen, reduced model) preserve the relevant dimensionless numbers, and the validity range of scaling laws.
- **Safety factors and design margins**: loads, boundary conditions and failure criteria as stated; cyclic, thermal or environmental effects not omitted silently.
- **Repeatability**: number of trials, scatter between specimens, and whether outliers were removed with a stated rule.
- **Tools** (optional, `requirements/base.txt`): `tools/dimcheck.py` for dimensional consistency, `tools/uncertainty.py` for error propagation and reporting digits.
