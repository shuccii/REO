from pathlib import Path
from fit_ea import estimate_ea
EXPECTED_EA = 0.85
TOL = 0.02
value = estimate_ea(Path(__file__).parent / 'data/sampleA.csv')
print(f'Ea = {value:.8f} eV')
assert abs(value-EXPECTED_EA) < TOL, f'{value} differs from {EXPECTED_EA}'
print('OK')
