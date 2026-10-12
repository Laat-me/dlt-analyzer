import json,tempfile,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parent; SCRIPT=ROOT/'trend_single_shape.py'; DRAWS=ROOT/'.agents/skills/dlt-analyzer/data/draws.json'
def main():
 with tempfile.TemporaryDirectory() as td:
  out=Path(td)/'stats.json';subprocess.run([sys.executable,str(SCRIPT),'--draws',str(DRAWS),'--output',str(out)],check=True)
  x=json.loads(out.read_text()); assert len(x['items'])==980; assert x['items'][-1]['targetDrawNum']=='26116'; assert x['items'][-1]['evaluation']['status']=='pending'
  t=x['items'][-1]['ticket']; assert len(t['front'])==5 and len(set(t['front']))==5 and len(t['back'])==2 and len(set(t['back']))==2
  print('single shape tests passed',t,x['items'][-1]['shapeSpec'])
if __name__=='__main__':main()
