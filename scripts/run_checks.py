#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    commands=[[sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],[sys.executable,'-m','json.tool','assets/task-result.schema.json'],[sys.executable,'-m','json.tool','assets/task-manifest.schema.json'],[sys.executable,'-m','json.tool','assets/research-contract.schema.json'],[sys.executable,'-m','json.tool','assets/research-review.schema.json']]
    failed=[]
    for command in commands:
        p=subprocess.run(command,cwd=ROOT,stdout=subprocess.DEVNULL if 'json.tool' in command else None)
        if p.returncode: failed.append({'command':command,'exit_code':p.returncode})
    print(json.dumps({'passed':not failed,'failures':failed}))
    raise SystemExit(1 if failed else 0)
if __name__=='__main__': main()
