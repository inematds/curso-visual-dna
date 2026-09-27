#!/usr/bin/env python3
"""Static offline checks of localized course structure and local resources."""
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlsplit,unquote
import json,re,sys,subprocess,zipfile
root=Path(sys.argv[1]).resolve();results=[]
for lang in ['pt','en','es']:
 base=root if lang=='pt'else root/lang
 for pt in sorted(root.glob('*.html')):
  if pt.name=='index.html':continue
  p=base/pt.name;s=BeautifulSoup(p.read_text(),'html.parser');orig=BeautifulSoup(pt.read_text(),'html.parser')
  ids=[t['id']for t in s.select('[id]')];assert len(ids)==len(set(ids)),(p,'duplicate IDs')
  assert set(ids)=={t['id']for t in orig.select('[id]')},(p,'IDs changed')
  assert s.html['lang'].split('-')[0]==lang,(p,'lang')
  assert len(s.select('link[rel=alternate][hreflang]'))==3,(p,'alternates')
  for t in s.select('[href],[src],[poster]'):
   for attr in ['href','src','poster']:
    v=t.get(attr)
    if not v:continue
    u=urlsplit(v)
    if u.scheme or u.netloc:continue
    f=(p.parent/unquote(u.path)).resolve()if u.path else p
    assert f.exists(),(p,attr,v,'missing file')
    if u.fragment and f.suffix=='.html':
     target=s if f==p else BeautifulSoup(f.read_text(),'html.parser')
     assert target.find(id=u.fragment) or target.find(id='v-'+u.fragment),(p,v,'missing anchor')
  for t in s.find_all('script',type='application/json'):json.loads(t.string or '{}')
  if pt.name=='curso.html':
   assert len(s.select('.view[data-aula]'))==len(orig.select('.view[data-aula]'))
   ck=s.select_one('meta[name=curso]')['content'];assert lang=='pt'or ck.endswith('-'+lang)
   for q in orig.select('.quiz'):
    qid=q.find_parent(attrs={'data-aula':True})['id'];dst=s.select_one('#'+qid+' .quiz')
    assert dst.get('data-answer')==q.get('data-answer'),(qid,'quiz answer changed')
  results.append({'locale':lang,'file':pt.name,'ids':len(ids),'passed':True})
 for p in (base/'assets').glob('*.js'):subprocess.run(['node','--check',str(p)],check=True,capture_output=True)
 if lang!='pt':
  for archive in (base/'assets').rglob('*.zip'):
   original=root/archive.relative_to(base)
   with zipfile.ZipFile(original)as ptzip,zipfile.ZipFile(archive)as translated:
    assert translated.testzip()is None,(archive,'corrupt archive')
    assert ptzip.namelist()==translated.namelist(),(archive,'kit filenames changed')
    media=0
    for name in ptzip.namelist():
     if Path(name).suffix.lower()not in ['.txt','.md','.csv','.srt','.vtt']:
      assert ptzip.read(name)==translated.read(name),(archive,name,'media changed')
      media+=1
    results.append({'locale':lang,'file':str(archive.relative_to(base)),'mediaPreserved':media,'passed':True})
(root/'context/i18n-static-checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(results))
