import csv

def load(path):
    with open(path) as handle:
        rows = list(csv.DictReader(handle))
    return [(float(r['T']), float(r['sigma'])) for r in rows if float(r['T']) >= 850]
