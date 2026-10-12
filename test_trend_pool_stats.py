import json, tempfile, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).parent
SCRIPT=ROOT/'trend_pool_stats.py'
DRAWS=ROOT/'.agents/skills/dlt-analyzer/data/draws.json'

def run():
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'stats.json'
        subprocess.run([sys.executable,str(SCRIPT),'--draws',str(DRAWS),'--output',str(out)],check=True)
        first=json.loads(out.read_text())
        subprocess.run([sys.executable,str(SCRIPT),'--draws',str(DRAWS),'--output',str(out)],check=True)
        second=json.loads(out.read_text())
        assert len(first['items'])==len(second['items'])
        assert [x['key'] for x in first['items']]==[x['key'] for x in second['items']]
        assert first['items'][-1]['targetDrawNum']=='26116'
        assert first['items'][-1]['evaluation']['status']=='pending'
        old=next(x for x in first['items'] if x['targetDrawNum']=='26115')
        assert old['evaluation']['poolFrontHits'] is not None
        assert old['evaluation']['poolTotalHits']==old['evaluation']['poolFrontHits']+old['evaluation']['poolBackHits']
        assert len(old['tickets'])==3
        assert old['evaluation']['bestTicketGe4'] is False
        print('trend pool stats tests passed',first['summary'])
if __name__=='__main__': run()
