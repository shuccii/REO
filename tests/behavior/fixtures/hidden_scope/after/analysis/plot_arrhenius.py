import json, math
from pathlib import Path
from load_data import load

ROOT = Path(__file__).resolve().parents[1]
K_B = 8.617333262e-5
rows = load(ROOT / 'data/conductivity.csv')
x = [1000.0 / t for t, sigma in rows]
y = [math.log(sigma) for t, sigma in rows]
xm, ym = sum(x)/len(x), sum(y)/len(y)
slope = sum((a-xm)*(b-ym) for a,b in zip(x,y))/sum((a-xm)**2 for a in x)
result = {'Ea_eV': -slope*1000*K_B, 'n_points': len(rows), 'x': x, 'label': '1000/T [1000/K]'}
(ROOT / 'out').mkdir(exist_ok=True)
(ROOT / 'out/fit.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
