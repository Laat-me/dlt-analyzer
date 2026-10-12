import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from page_extract import visible_text, parse_segments

def test_visible_and_target():
    text=visible_text('<html><script>x</script><p>大乐透26116期：前区 01 04 15 27 35 + 后区 03 06</p></html>')
    r,e=parse_segments(text,'26116'); assert e is None and r and r[0]['kind']=='exact_5_plus_2'
def test_pool_sections():
    r,e=parse_segments('大乐透26116期 前区五胆：07 09 17 18 26；后区三胆：04 10 12','26116')
    assert e is None and {x['kind'] for x in r}=={'front_pool','back_pool'}
def test_wrong_issue():
    r,e=parse_segments('大乐透26115期 前区 01 04 15 27 35 + 后区 03 06','26116'); assert not r and e
if __name__=='__main__': test_visible_and_target();test_pool_sections();test_wrong_issue();print('pipeline parser tests passed')
