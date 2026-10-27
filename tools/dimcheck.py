#!/usr/bin/env python3
"""Check that both sides of an equation have the same physical dimension.

Example:
    python tools/dimcheck.py "E = 0.5*m*v**2" --units "E:J,m:kg,v:m/s"

Prints JSON and exits 0 when consistent, 1 when inconsistent, 2 on invalid input.
Requires: pint (requirements/base.txt).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safe_expr import ExpressionError, evaluate, parse_assignments  # noqa: E402


def check(equation, units):
    import pint
    registry = pint.UnitRegistry()
    if equation.count('=') != 1:
        raise ExpressionError('equation must contain exactly one "="')
    try:
        symbols = {name: registry.Quantity(1, unit) for name, unit in units.items()}
    except (pint.errors.UndefinedUnitError, AttributeError, ValueError) as error:
        raise ExpressionError(f'unknown unit: {error}') from error
    number = lambda value: registry.Quantity(value, 'dimensionless')
    sides = {}
    errors = []
    for label, text in zip(('lhs', 'rhs'), equation.split('=')):
        try:
            sides[label] = evaluate(text, symbols, number=number)
        except pint.errors.DimensionalityError as error:
            errors.append(f'{label}: terms with different dimensions are added or subtracted ({error})')
    report = {'equation': equation, 'units': units, 'errors': errors}
    for label, quantity in sides.items():
        report[f'{label}_dimension'] = str(quantity.dimensionality) or 'dimensionless'
    report['consistent'] = not errors and len(sides) == 2 and (
        sides['lhs'].dimensionality == sides['rhs'].dimensionality)
    if len(sides) == 2 and not report['consistent'] and not errors:
        report['errors'].append('left and right sides have different dimensions')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Check dimensional consistency of an equation (pint).')
    parser.add_argument('equation', help='e.g. "F = m*a"')
    parser.add_argument('--units', action='append', required=True,
                        help='symbol:unit pairs, comma separated, e.g. "F:N,m:kg,a:m/s**2"')
    args = parser.parse_args(argv)
    try:
        report = check(args.equation, parse_assignments(args.units, ':'))
    except ExpressionError as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['consistent'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
