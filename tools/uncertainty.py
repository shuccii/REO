#!/usr/bin/env python3
"""Propagate measurement uncertainty through a formula (first-order, uncertainties package).

Example:
    python tools/uncertainty.py "m / V" --var "m=12.31:0.02,V=4.52:0.05"

Variables are assumed independent unless the same symbol appears more than once
(that correlation is handled automatically). Prints JSON; exits 2 on invalid input.
Requires: uncertainties (requirements/base.txt).
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safe_expr import ExpressionError, evaluate, parse_assignments  # noqa: E402


def propagate(formula, variables):
    from uncertainties import ufloat, umath
    symbols = {}
    for name, text in variables.items():
        if ':' not in text:
            raise ExpressionError(f'{name}: expected value:standard_uncertainty')
        value, sigma = text.split(':', 1)
        try:
            symbols[name] = ufloat(float(value), float(sigma))
        except ValueError as error:
            raise ExpressionError(f'{name}: {error}') from error
        if symbols[name].std_dev < 0:
            raise ExpressionError(f'{name}: uncertainty must be non-negative')
    functions = {name: getattr(umath, name) for name in ('sqrt', 'exp', 'log', 'log10', 'sin', 'cos', 'tan')}
    result = evaluate(formula, symbols, functions=functions)
    value = float(getattr(result, 'nominal_value', result))
    sigma = float(getattr(result, 'std_dev', 0.0))
    contributions = {}
    if hasattr(result, 'error_components'):
        for variable, component in result.error_components().items():
            for name, symbol in symbols.items():
                if symbol is variable:
                    contributions[name] = abs(component)
    return {
        'formula': formula,
        'value': value,
        'standard_uncertainty': sigma,
        'relative_uncertainty': abs(sigma / value) if value else None,
        'reported': report_string(value, sigma),
        'contributions': contributions,
        'note': 'First-order (linear) propagation with independent inputs. Check large relative uncertainties or strong nonlinearity separately.',
    }


def report_string(value, sigma, digits=2):
    """Round the uncertainty to `digits` significant figures and the value to the same decimal place."""
    if sigma <= 0 or not math.isfinite(sigma):
        return f'{value:g}'
    exponent = math.floor(math.log10(sigma)) - (digits - 1)
    decimals = max(0, -exponent)
    rounded_sigma = round(sigma, -exponent)
    rounded_value = round(value, -exponent)
    return f'{rounded_value:.{decimals}f} ± {rounded_sigma:.{decimals}f}'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Propagate uncertainty through a formula.')
    parser.add_argument('formula', help='e.g. "m / V" or "sqrt(x**2 + y**2)"')
    parser.add_argument('--var', action='append', required=True,
                        help='name=value:standard_uncertainty, comma separated')
    args = parser.parse_args(argv)
    try:
        report = propagate(args.formula, parse_assignments(args.var, '='))
    except (ExpressionError, ZeroDivisionError, ValueError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
