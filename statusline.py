# statusline.py - minimal Claude Code status line: directory | model | ETA segment. Stdlib only.
# settings.json:  "statusLine": {"type": "command", "command": "python \"<path>/statusline.py\"", "refreshInterval": 5}
# Already have a status line? Skip this file and append the output of  python eta.py line <session_id>  to yours.
import sys,json,subprocess
from pathlib import Path
if sys.stdout:sys.stdout.reconfigure(encoding='utf-8')
j=json.load(sys.stdin);E='\x1b[';sep=f'  {E}90m|{E}0m  '
d=j.get('workspace',{}).get('current_dir','').replace(str(Path.home()),'~');m=j.get('model',{}).get('display_name','')
eta=subprocess.run([sys.executable,str(Path(__file__).with_name('eta.py')),'line',j.get('session_id','')],capture_output=True,text=True,encoding='utf-8').stdout.strip()
print(sep.join(x for x in(f'{E}36m{d}{E}0m',f'{E}1;33m{m}{E}0m',eta)if x))
