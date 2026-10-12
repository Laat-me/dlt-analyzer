import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from site_schema import canonicalize_url, registrable_domain, is_allowed_result_url, site_from_url, dedupe_sites

def test_url_normalize():
    assert canonicalize_url('HTTPS://WWW.Example.COM:443/a?utm_source=x&x=1#frag') == 'https://www.example.com/a?x=1'
def test_domain():
    assert registrable_domain('m.example.com') == 'example.com'
    assert registrable_domain('x.example.com.cn') == 'example.com.cn'
def test_filter():
    assert not is_allowed_result_url('https://www.bing.com/search?q=x')
    assert not is_allowed_result_url('https://lottery.gov.cn/dlt')
    assert is_allowed_result_url('https://m.example.com/article/1')
def test_merge_and_limit():
    a=site_from_url('https://a.example.com/1','q1','26117','t'); b=site_from_url('https://www.example.com/2','q2','26117','t'); c=site_from_url('https://b.test/3','q3','26117','t')
    out=dedupe_sites([a,b,c],1); assert len(out)==1
    assert out[0]['domain'] in {'b.test','example.com'}
    both=dedupe_sites([a,b]); assert both[0]['queries']==['q1','q2']
if __name__=='__main__':
    test_url_normalize(); test_domain(); test_filter(); test_merge_and_limit(); print('site tests passed')
