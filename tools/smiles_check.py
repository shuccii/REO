#!/usr/bin/env python3
"""Check a molecule table for invalid SMILES, duplicates and train/test leakage (RDKit).

Example:
    python tools/smiles_check.py data.csv --smiles-column smiles --split-column split

Reports invalid SMILES, duplicate molecules after canonicalisation, and molecules or
Bemis-Murcko scaffolds shared between splits. Prints JSON; exits 1 when leakage or
invalid rows are found, 2 on invalid input. Requires: rdkit (requirements/chem.txt).
"""
import argparse
import csv
import json
from collections import defaultdict


def analyse(rows, smiles_column='smiles', split_column=None):
    from rdkit import Chem, RDLogger
    from rdkit.Chem.Scaffolds import MurckoScaffold
    RDLogger.DisableLog('rdApp.*')
    invalid, canonical_rows = [], defaultdict(list)
    by_split = defaultdict(lambda: {'molecules': set(), 'scaffolds': set()})
    for index, row in enumerate(rows, start=2):  # row 1 is the header
        text = (row.get(smiles_column) or '').strip()
        molecule = Chem.MolFromSmiles(text) if text else None
        if molecule is None:
            invalid.append({'row': index, 'smiles': text})
            continue
        canonical = Chem.MolToSmiles(molecule)
        canonical_rows[canonical].append(index)
        if split_column:
            split = (row.get(split_column) or '').strip() or '(blank)'
            by_split[split]['molecules'].add(canonical)
            by_split[split]['scaffolds'].add(MurckoScaffold.MurckoScaffoldSmiles(mol=molecule))
    duplicates = [{'canonical_smiles': key, 'rows': value} for key, value in canonical_rows.items() if len(value) > 1]
    report = {'n_rows': len(rows), 'n_invalid': len(invalid), 'invalid': invalid[:50],
              'n_duplicate_groups': len(duplicates), 'duplicates': duplicates[:50]}
    leakage = []
    splits = sorted(by_split)
    for i, first in enumerate(splits):
        for second in splits[i + 1:]:
            shared_molecules = by_split[first]['molecules'] & by_split[second]['molecules']
            shared_scaffolds = by_split[first]['scaffolds'] & by_split[second]['scaffolds'] - {''}
            leakage.append({'splits': [first, second], 'shared_molecules': len(shared_molecules),
                            'shared_scaffolds': len(shared_scaffolds),
                            'examples': sorted(shared_molecules)[:10]})
    if split_column:
        report['split_overlap'] = leakage
        report['note'] = ('Shared molecules are direct leakage. Shared scaffolds mean the test set does not measure '
                          'generalisation to new scaffolds; use a scaffold split if that is the claim.')
    report['problems_found'] = bool(invalid) or any(item['shared_molecules'] for item in leakage)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='SMILES validity, duplicate and split-leakage check.')
    parser.add_argument('csv_file')
    parser.add_argument('--smiles-column', default='smiles')
    parser.add_argument('--split-column', help='column with train/test labels')
    args = parser.parse_args(argv)
    try:
        import rdkit  # noqa: F401
    except ImportError:
        print(json.dumps({'error': 'rdkit is not installed. Install requirements/chem.txt.'}))
        return 2
    try:
        with open(args.csv_file, newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            missing = [c for c in (args.smiles_column, args.split_column) if c and c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f'missing column(s): {", ".join(missing)}')
            rows = list(reader)
    except (OSError, ValueError) as error:
        print(json.dumps({'error': str(error)}))
        return 2
    report = analyse(rows, args.smiles_column, args.split_column)
    print(json.dumps(report, indent=2))
    return 1 if report['problems_found'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
