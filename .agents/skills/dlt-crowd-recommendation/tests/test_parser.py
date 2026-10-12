import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from schemas import extract_numbers, validate, parse_source

def test_extract_labeled():
    f,b=extract_numbers('前区：01 04 15 27 35 + 后区：03 06')
    assert f==[1,4,15,27,35] and b==[3,6]
def test_extract_chinese_punctuation():
    f,b=extract_numbers('前区 1、4、15、27、35；后区 3、6')
    assert f==[1,4,15,27,35] and b==[3,6]
def test_reject_bad_range():
    assert validate([1,2,3,4,36],[1,2])[0] is False
def test_parse_source():
    s={'platform':'x','author':'a','title':'26115预测','url':'https://x.test/a','targetDrawNum':'26115','publishedAt':'2026-10-09T08:00:00+08:00','rawText':'大乐透26115期 前区 01 04 15 27 35 后区 03 06'}
    src,r=parse_source(s); assert src['parseStatus']=='parsed'; assert r['front']==[1,4,15,27,35]
def test_cutoff_and_missing_time_confidence():
    base={'platform':'x','author':'a','title':'26115预测','url':'https://x.test/a','targetDrawNum':'26115','rawText':'前区 01 04 15 27 35 + 后区 03 06'}
    src,r=parse_source(dict(base, cutoffAt='2026-10-09T12:00:00+08:00', publishedAt='2026-10-10T12:00:00+08:00'))
    assert src['parseStatus']=='rejected' and r is None
    src,r=parse_source(base); assert r['parseConfidence']==0
def test_pool_and_danma():
    src,r=parse_source({'platform':'x','author':'a','title':'26116五胆后三胆','url':'https://x.test/b','targetDrawNum':'26116','publishedAt':'2026-10-11','rawText':'前区五胆：07 09 17 18 26；后区三胆：04 10 12'})
    assert src['parseStatus']=='parsed' and r['kind']=='front_pool_back_pool' and r['front']==[7,9,17,18,26] and r['back']==[4,10,12]
if __name__ == '__main__':
    test_extract_labeled(); test_extract_chinese_punctuation(); test_reject_bad_range(); test_parse_source(); test_cutoff_and_missing_time_confidence(); test_pool_and_danma()
    print('parser tests passed')
