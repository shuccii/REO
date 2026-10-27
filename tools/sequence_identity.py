#!/usr/bin/env python3
"""Find test sequences that are too similar to training sequences (Biopython).

Example:
    python tools/sequence_identity.py train.fasta test.fasta --threshold 0.9

For each test sequence, reports the highest global-alignment identity to any training
sequence. Pairwise alignment is O(n_train x n_test); for large sets use a clustering
tool (for example, CD-HIT or MMseqs2) instead. Prints JSON; exits 1 when any pair is at
or above the threshold, 2 on invalid input. Requires: biopython (requirements/bio.txt).
"""
import argparse
import json


def read_fasta(path):
    records, name, chunks = [], None, []
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith('>'):
                if name is not None:
                    records.append((name, ''.join(chunks).upper()))
                name, chunks = line[1:].split()[0] if len(line) > 1 else f'seq{len(records) + 1}', []
            elif name is None:
                raise ValueError(f'{path}: sequence data before the first ">" header')
            else:
                chunks.append(line)
    if name is not None:
        records.append((name, ''.join(chunks).upper()))
    if not records:
        raise ValueError(f'{path}: no sequences found')
    return records


def identity(aligner, first, second):
    """Identical aligned positions divided by the length of the shorter sequence."""
    if not first or not second:
        return 0.0
    alignment = aligner.align(first, second)[0]
    matches = 0
    for (a_start, a_end), (b_start, b_end) in zip(*alignment.aligned):
        matches += sum(x == y for x, y in zip(first[a_start:a_end], second[b_start:b_end]))
    return matches / min(len(first), len(second))


def analyse(train, test, threshold=0.9):
    from Bio.Align import PairwiseAligner
    aligner = PairwiseAligner(mode='global', match_score=1, mismatch_score=0,
                              open_gap_score=-1, extend_gap_score=-0.5)
    rows = []
    for test_name, test_sequence in test:
        best_name, best = None, -1.0
        for train_name, train_sequence in train:
            value = identity(aligner, train_sequence, test_sequence)
            if value > best:
                best_name, best = train_name, value
        rows.append({'test': test_name, 'closest_train': best_name, 'identity': round(best, 4),
                     'above_threshold': best >= threshold})
    flagged = [row for row in rows if row['above_threshold']]
    return {'threshold': threshold, 'n_train': len(train), 'n_test': len(test), 'n_flagged': len(flagged),
            'flagged': flagged, 'all': rows,
            'note': 'High identity between splits inflates test performance. Choose the threshold that matches '
                    'the claim (new family, new protein, new variant) and state it.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Train/test sequence-identity leakage check.')
    parser.add_argument('train_fasta')
    parser.add_argument('test_fasta')
    parser.add_argument('--threshold', type=float, default=0.9)
    args = parser.parse_args(argv)
    try:
        import Bio  # noqa: F401
    except ImportError:
        print(json.dumps({'error': 'biopython is not installed. Install requirements/bio.txt.'}))
        return 2
    if not 0 < args.threshold <= 1:
        print(json.dumps({'error': 'threshold must be in (0, 1]'}))
        return 2
    try:
        report = analyse(read_fasta(args.train_fasta), read_fasta(args.test_fasta), args.threshold)
    except (OSError, ValueError) as error:
        print(json.dumps({'error': str(error)}))
        return 2
    print(json.dumps(report, indent=2))
    return 1 if report['n_flagged'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
