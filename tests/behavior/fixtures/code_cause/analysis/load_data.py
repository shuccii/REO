import csv

def load(path):
    with open(path) as handle:
        return [(float(r['T']), float(r.get('sigma') or 'nan')) for r in csv.DictReader(handle)]
