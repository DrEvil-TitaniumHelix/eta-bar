# eta.py - busy / ready / ETA segment for the Claude Code status line. MIT, DrEvil.
# State: ~/.claude/eta/<session_id>.json, one file per session so parallel sessions never collide.
#  hooks : python eta.py busy          (UserPromptSubmit, stdin JSON)
#          python eta.py ready         (Stop, stdin JSON)
#          python eta.py brief         (SessionStart: prints the one-paragraph duty that tells Claude to set ETAs)
#  model : python eta.py set "what I'm doing" 8      minutes, or 07:48 clock time (needs CLAUDE_CODE_SESSION_ID, which Claude Code exports to its shell)
#  bar   : python eta.py line <session_id>           one coloured segment, or nothing if unknown
#  toast : python eta.py window <session_id>         optional topmost 'ready for you' window (Windows); only if ~/.claude/eta/TOAST_ON exists
#  check : python eta.py selftest
import sys,json,os,time,re,subprocess
from pathlib import Path
if sys.stdout:sys.stdout.reconfigure(encoding='utf-8')
D=Path.home()/'.claude/eta';D.mkdir(parents=True,exist_ok=True)
P=lambda sid:D/f'{sid}.json'
def load(sid):
  try:return json.load(open(P(sid),encoding='utf-8'))
  except Exception:return {}
def save(sid,s):json.dump(s,open(P(sid),'w',encoding='utf-8'))
who=lambda cwd:os.environ.get('ETA_WHO') or Path(cwd).name.upper() or 'CLAUDE'
hm=lambda t:time.strftime('%H:%M',time.localtime(t))
TOAST_MIN_S=45  # no toast for quick replies you were already watching
BRIEF=("ETA bar is on. Before any batch of tool calls that will take more than a few seconds, run "
 "`python \"%s\" set \"<3-6 word description>\" <minutes>` and run it again when a step finishes or the estimate slips. "
 "Estimate the long end. Short chat replies need nothing. An empty bar ('no ETA yet') is the failure this exists to remove.")
E='\x1b['
def segment(s,now):
  if not s:return ''
  if s.get('state')=='ready':return f"{E}1;32m✅ ready for you · since {hm(s.get('ready_at',now))}{E}0m"
  el=int(now-s.get('since',now));note=s.get('note') or 'working';eta=s.get('eta')
  if eta:
    rem=int((eta-now)/60+0.5)
    t=f"{E}1;33m⏳ {note} · ready ~{hm(eta)} ({rem} min)" if rem>=0 else f"{E}1;31m⏳ {note} · OVERDUE {-rem} min (said ~{hm(eta)})"
  else:t=f"{E}1;33m⏳ {note} · no ETA yet"
  return f"{t} · {el//60}m{el%60:02d}s{E}0m"
def main():
  cmd=sys.argv[1];now=time.time()
  if cmd in('busy','ready'):
    j=json.load(sys.stdin);sid=j.get('session_id') or os.environ.get('CLAUDE_CODE_SESSION_ID');cwd=j.get('cwd') or os.getcwd()
    if not sid:return
    s=load(sid)
    if cmd=='busy':s={'state':'busy','since':now,'note':'','eta':None,'who':who(cwd)}
    else:
      long=now-s.get('since',now)>=TOAST_MIN_S
      s.update(state='ready',ready_at=now);s.setdefault('who',who(cwd))
      if long and os.name=='nt' and (D/'TOAST_ON').exists():subprocess.Popen([sys.executable,__file__,'window',sid],creationflags=0x208,close_fds=True)
    save(sid,s)
  elif cmd=='set':
    sid=os.environ.get('CLAUDE_CODE_SESSION_ID') or sys.exit('no CLAUDE_CODE_SESSION_ID');s=load(sid) or {'state':'busy','since':now,'who':who(os.getcwd())}
    note=sys.argv[2];w=sys.argv[3] if len(sys.argv)>3 else '';m=re.fullmatch(r'(\d{1,2}):(\d{2})',w)
    if m:t=time.localtime(now);eta=time.mktime(t[:3]+(int(m[1]),int(m[2]),0)+t[6:]);eta+=86400*(eta<now-600)
    elif w:eta=now+60*float(w)
    else:eta=None
    s.update(note=note,eta=eta,state='busy');s.setdefault('since',now);save(sid,s);print('ETA set:',note,'->',hm(eta) if eta else 'none')
  elif cmd=='line':print(segment(load(sys.argv[2]),now))
  elif cmd=='brief':print(BRIEF%Path(__file__).resolve().as_posix())
  elif cmd=='window':window(sys.argv[2])
  elif cmd=='selftest':selftest()
def window(sid):
  import tkinter as tk,ctypes
  s=load(sid)
  if s.get('state')!='ready':return
  u=ctypes.windll.user32;prev=u.GetForegroundWindow()
  try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
  except Exception:pass
  r=tk.Tk();r.title('Ready: '+s.get('who','CLAUDE'));r.attributes('-topmost',1);r.configure(bg='#1e1e2e')
  w=int(time.time()-s.get('since',s['ready_at']))//60
  tk.Label(r,text=f"✅ {s.get('who','CLAUDE')} READY FOR YOU",font=('Segoe UI Emoji',18,'bold'),bg='#a6e3a1',fg='#11111b',pady=8,padx=16).pack(fill='x')
  tk.Label(r,text=(s.get('note') or 'done')+f"\nhanded back {hm(s['ready_at'])} · you waited {w} min\n(click to close; closes itself when you type the next prompt)",font=('Segoe UI',12),bg='#1e1e2e',fg='#cdd6f4',justify='left',padx=16,pady=10).pack(anchor='w')
  r.bind('<Button-1>',lambda _:r.destroy());r.protocol('WM_DELETE_WINDOW',r.destroy)
  r.update_idletasks();r.geometry(f'+{r.winfo_screenwidth()-r.winfo_width()-40}+60')
  h=int(r.wm_frame(),16);u.SetWindowLongW(h,-20,u.GetWindowLongW(h,-20)|0x08000000)  # WS_EX_NOACTIVATE: never steals focus
  r.after(50,lambda:u.GetForegroundWindow()!=prev and u.SetForegroundWindow(prev))
  def poll():
    if load(sid).get('state')!='ready':r.destroy()
    else:r.after(1000,poll)
  r.after(1000,poll);r.mainloop()
def selftest():
  import io
  sid='selftest';os.environ['CLAUDE_CODE_SESSION_ID']=sid;now=time.time()
  sys.stdin=io.StringIO(json.dumps({'session_id':sid,'cwd':'/home/x/myproject'}));sys.argv=['eta.py','busy'];main()
  assert load(sid)['state']=='busy' and load(sid)['who']=='MYPROJECT'
  sys.argv=['eta.py','set','printer diagnosis','8'];main();s=load(sid);assert 475<s['eta']-now<485 and s['note']=='printer diagnosis'
  assert 'printer diagnosis' in segment(s,now) and '(8 min)' in segment(s,now) and 'OVERDUE' in segment(s,now+900)
  sys.argv=['eta.py','set','x','23:59'];main();assert load(sid)['eta']>now
  sys.stdin=io.StringIO(json.dumps({'session_id':sid,'cwd':'/x'}));sys.argv=['eta.py','ready'];main();s=load(sid)
  assert s['state']=='ready' and 'ready for you' in segment(s,now)
  P(sid).unlink();print('eta selftest OK')
if __name__=='__main__':main()
