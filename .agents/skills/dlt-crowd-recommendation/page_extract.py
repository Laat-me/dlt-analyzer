"""Extract DLT recommendation records from visible HTML/text without storing page content."""
from __future__ import annotations
import re
from html.parser import HTMLParser
from schemas import validate, validate_pool

class TextParser(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag.lower() in {'script','style','nav','footer','header'}: self.skip+=1
    def handle_endtag(self,tag):
        if tag.lower() in {'script','style','nav','footer','header'} and self.skip: self.skip-=1
    def handle_data(self,data):
        if not self.skip: self.parts.append(data)

def visible_text(value):
    p=TextParser(); p.feed(value or ''); return re.sub(r'\s+',' ', ' '.join(p.parts)).strip()

def target_mentions(text,target):
    found=set(re.findall(r'(?<!\d)(?:第|期号?\s*)?(26\d{3})(?!\d)',text))
    return str(target) in found, found

def nums(fragment,maxn):
    values=[int(x) for x in re.findall(r'(?<!\d)(\d{1,2})(?!\d)',fragment)]
    return values

def parse_segments(text,target):
    ok,found=target_mentions(text,target)
    if not ok: return [], 'target_missing_or_conflict'
    out=[]
    # Split explicit numbered tickets first; each + pair must be isolated.
    exact=re.compile(r'(?:前区\s*)?([0-9]{1,2}(?:\s*[,、， ]\s*[0-9]{1,2}){4})\s*(?:\+|加)\s*(?:后区\s*)?([0-9]{1,2}(?:\s*[,、， ]\s*[0-9]{1,2}){1})')
    for i,m in enumerate(exact.finditer(text),1):
        f=nums(m.group(1),35); b=nums(m.group(2),12)
        if len(f)==5 and len(b)==2 and validate(f,b)[0]: out.append({'kind':'exact_5_plus_2','front':sorted(f),'back':sorted(b),'ticketIndex':i,'confidence':.95,'evidenceQuote':m.group(0)[:180]})
    # Explicit front/back pools/dans; keep as one partial record.
    fm=re.search(r'(?:前区|前区号码)\s*(?:三胆|五胆|胆码|大底号|号码池|推荐号码)?\s*[:：]\s*([0-9\s,、，]{3,})',text)
    bm=re.search(r'(?:后区|后区号码)\s*(?:三胆|四码|五码|胆码|号码池|推荐号码)?\s*[:：]\s*([0-9\s,、，]{2,})',text)
    f=nums(fm.group(1),35) if fm else []; b=nums(bm.group(1),12) if bm else []
    if f and validate_pool(f,35,1)[0]: out.append({'kind':'front_pool','front':sorted(set(f)),'back':[],'confidence':.65,'evidenceQuote':fm.group(0)[:180]})
    if b and validate_pool(b,12,1)[0]: out.append({'kind':'back_pool','front':[],'back':sorted(set(b)),'confidence':.65,'evidenceQuote':bm.group(0)[:180]})
    return out, None
