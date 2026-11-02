"""Zero-model, deterministic example receipt adapter."""
import json
import sys
from pathlib import Path

request = json.load(sys.stdin)
result = {'characters': len(Path('input.txt').read_text(encoding='utf-8')),
          'input_sha256': request['inputs']['input.txt']}
Path('result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'passed', 'usage': {'llm_calls': 0, 'tokens': 0, 'cost_usd': 0}}))
