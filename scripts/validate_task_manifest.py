#!/usr/bin/env python3
import argparse, json, sys
from manifest_helper import detect_write_conflicts, load_manifest, ready_tasks, validate_manifest

def main():
    p=argparse.ArgumentParser(); p.add_argument('--json',action='store_true'); p.add_argument('--completed',action='append',default=[]); p.add_argument('--operation-succeeded',action='append',default=[]); p.add_argument('manifest'); args=p.parse_args()
    try:
        data=load_manifest(args.manifest); errors=validate_manifest(data)
        result={'valid':not errors,'errors':errors,'ready_tasks':ready_tasks(data,set(args.completed),set(args.operation_succeeded)) if not errors else [],'write_conflicts':detect_write_conflicts(data['tasks']) if not errors else []}
    except Exception as exc:
        print(json.dumps({'internal_error':str(exc)}) if args.json else f'Validation error: {exc}',file=sys.stderr); raise SystemExit(2)
    print(json.dumps(result,indent=2) if args.json else (('VALID' if result['valid'] else 'INVALID')+'\n'+'\n'.join('  - '+e for e in errors)))
    raise SystemExit(0 if result['valid'] else 1)
if __name__=='__main__': main()
