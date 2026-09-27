#!/usr/bin/env python3
"""Offline catalogs and build. No network, credentials, or model calls."""
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Comment
import argparse, hashlib, json, re, subprocess, zipfile
from urllib.parse import urlsplit,unquote
INLINE={'b','strong','i','em','span','a','br','code','small','mark','sup','sub','kbd','abbr'}
ATTRS=['alt','title','aria-label','placeholder','data-def','data-rotulo','data-fb','data-exlbl','data-cap']
LANGS={'pt':('pt-BR','Português'),'en':('en','English'),'es':('es','Español')}
def read(p):return p.read_text(encoding='utf-8')
def writejson(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def key(s):return hashlib.sha256(s.encode()).hexdigest()[:16]
def eligible(s):return isinstance(s,str) and bool(re.search('[A-Za-zÀ-ÿ]',s))
def inner(t):return t.decode_contents()
def leaf(t):
 if t.name in ['script','style','svg','head','html','body','br']:return False
 return any(str(x).strip() for x in t.children) and all(isinstance(x,NavigableString) or x.name in INLINE for x in t.children)
def blocks(soup):
 out=[]
 def walk(t):
  for c in list(t.children):
   if not getattr(c,'name',None) or c.name in ['script','style']:continue
   if leaf(c):out.append(c)
   else:walk(c)
 walk(soup.body or soup)
 if soup.title and not any(t is soup.title for t in out):out.append(soup.title)
 selected={id(x) for x in out}
 orphans=[n for n in (soup.body or soup).find_all(string=True) if not isinstance(n,Comment) and eligible(str(n)) and not n.find_parent(['script','style']) and not any(id(p) in selected for p in n.parents)]
 return out,orphans

def language_object(js):
 m=re.search(r'/\*L-INICIO.*?\*/\s*var L=(\{.*?\});\s*/\*L-FIM\*/',js,re.S)
 if not m:raise ValueError('Missing L block')
 return m,json.loads(m[1])
def stringvals(o):
 if isinstance(o,str):yield o
 elif isinstance(o,list):
  for v in o:yield from stringvals(v)
 elif isinstance(o,dict):
  for k,v in o.items():
   if k!='capRe':yield from stringvals(v)
def walkstrings(o,f):
 if isinstance(o,str):return f(o)
 if isinstance(o,list):return [walkstrings(v,f)for v in o]
 if isinstance(o,dict):return {k:walkstrings(v,f)if k!='capRe' else v for k,v in o.items()}
 return o

def jsunits(code):
 return json.loads(subprocess.check_output(['node',str(Path(__file__).with_name('i18n_js.cjs'))],input=json.dumps({'code':code}),text=True))
def translate_js(code,tr):
 units=jsunits(code)
 for u in sorted(units,key=lambda u:u['start'],reverse=True):
  v=tr(u['value'])
  code=code[:u['start']]+(json.dumps(v,ensure_ascii=False)if u['kind']=='string' else v)+code[u['end']:]
 return code

def guard_support(code):
 # The planner/sprint store their own state independently of the course engine.
 # Reject another locale before assigning any imported or persisted fields.
 if '/*i18n-state*/'in code or not re.search(r'const KEY\s*=',code) or 'function valid(s){return 'not in code:return code
 code=code.replace('function valid(s){return ',"function valid(s){return /*i18n-state*/ s && (s.course ? s.course===KEY : document.documentElement.lang.slice(0,2)==='pt') && ",1)
 code=code.replace('JSON.stringify(state', 'JSON.stringify(Object.assign({},state,{course:KEY,locale:document.documentElement.lang})')
 return code

def guarded_engine(js):
 old='JSON.stringify(state,null,2)'
 js=js.replace(old,'JSON.stringify(Object.assign({},state,{course:CK,locale:document.documentElement.lang}),null,2)')
 old="if(!p||typeof p.aulas==='object')"
 guard="if(!p||typeof p.aulas!=='object') throw 0;"
 replacement="if(!p||typeof p.aulas!=='object'||Array.isArray(p.aulas)|| (p.course ? p.course!==CK : (document.documentElement.lang||'pt').slice(0,2)!=='pt')) throw 0;"
 assert guard in js
 return js.replace(guard,replacement)

def text_assets(root):
 # Translate explicitly linked text downloads in the project root as well.
 # Do not include maintainer documentation or private context files.
 linked=set()
 for page in root.glob('*.html'):
  soup=BeautifulSoup(read(page),'html.parser')
  for a in soup.select('a[href]'):
   u=urlsplit(a['href'])
   if u.scheme or u.netloc or not u.path:continue
   p=(root/unquote(u.path)).resolve()
   if p.parent==root and p.is_file()and p.suffix.lower()in ['.txt','.md','.csv','.srt','.vtt']:linked.add(p)
 for p in sorted(linked):yield p.name,read(p)
 for p in (root/'assets').rglob('*'):
  if p.suffix.lower() in ['.txt','.md','.csv','.srt','.vtt']:
   yield str(p.relative_to(root)),read(p)
  elif p.suffix.lower()=='.zip':
   with zipfile.ZipFile(p)as z:
    for name in z.namelist():
     if Path(name).suffix.lower()in ['.txt','.md','.csv','.srt','.vtt']:
      yield str(p.relative_to(root))+'::'+name,z.read(name).decode('utf-8')
def translate_text(s,tr):
 out=[]
 for line in s.splitlines(keepends=True):
  if not eligible(line):out.append(line);continue
  ending='\r\n'if line.endswith('\r\n')else'\n'if line.endswith('\n')else'\r'if line.endswith('\r')else''
  indent=re.match(r'^[ \t]*',line)[0]
  out.append(indent+tr(line).lstrip(' \t').rstrip('\r\n')+ending)
 return ''.join(out)

def extract(root):
 units={};origins={}
 def add(s,origin):
  if eligible(s):units[key(s)]=s;origins.setdefault(key(s),[]).append(origin)
 for p in sorted(root.glob('*.html')):
  if p.name=='index.html':continue
  soup=BeautifulSoup(read(p),'html.parser')
  for old in soup.select('.langs,link[rel=alternate]'):old.decompose()
  bs,ns=blocks(soup)
  for t in bs:add(inner(t),p.name+':'+str((t.find_parent(attrs={'data-aula':True})or{}).get('data-aula','interface')))
  for n in ns:add(str(n),p.name+':text')
  for a in ATTRS:
   for t in soup.find_all(attrs={a:True}):add(t[a],p.name+':'+a)
  for t in soup.select('meta[name="description"],meta[property="og:title"],meta[property="og:description"]'):add(t.get('content',''),p.name+':meta')
  for t in soup.find_all('script',type='application/json'):
   for s in stringvals(json.loads(t.string or '{}')):add(s,p.name+':json')
  for t in soup.find_all('script'):
   if t.string and t.get('type')!='application/json' and p.name not in ['curso.html','landing.html']:
    for u in jsunits(t.string):add(u['value'],p.name+':javascript')
 for p in (root/'assets').glob('*.js'):
  if p.name not in ['curso.js','curso-i18n.js']:
   for u in jsunits(read(p)):add(u['value'],'assets/'+p.name)
 for name,txt in text_assets(root):
  for line in txt.splitlines(keepends=True):add(line,name)
 _,obj=language_object(read(root/'assets/curso.js'))
 for s in stringvals(obj):add(s,'assets/curso.js:L')
 writejson(root/'i18n/source.json',units);writejson(root/'i18n/origins.json',origins)
 # Contiguous batches preserve pedagogical context and keep each translator bounded.
 reused={'en':{},'es':{}}
 for previous in sorted(root.parent.glob('curso-*/i18n/source.json')):
  if previous.parent.parent==root:continue
  provenance=previous.parent/'provenance.json'
  if not provenance.exists()or json.loads(read(provenance)).get('model')!='gpt-6-luna':continue
  for lang in reused:
   cache=previous.parent/f'{lang}.json'
   if cache.exists():
    values=json.loads(read(cache))
    for k,v in values.items():
     if k in units and validate(units[k],v) is None:reused[lang].setdefault(k,v)
 for lang,v in reused.items():writejson(root/f'i18n/reused-{lang}.json',v)
 shared=set(reused['en'])&set(reused['es'])
 items=[(k,v)for k,v in units.items()if k not in shared];n=3;size=(len(items)+n-1)//n
 for i in range(n):writejson(root/f'i18n/source-{i+1}.json',dict(items[i*size:(i+1)*size]))
 writejson(root/'i18n/provenance.json',{'model':'gpt-6-luna','execution':'Codex subscription; no external model API','source_hashes':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in list(root.glob('*.html'))+[root/'assets/curso.js']},'units':len(units)})
 print(root.name,len(units),'units',sum(len(s)for s in units.values()),'characters')

def validate(src,dst):
 if not isinstance(dst,str)or not dst.strip():return 'empty'
 if re.findall(r'\d+',src)!=re.findall(r'\d+',dst):return 'numbers changed'
 if re.findall(r'R\$|US\$|\b(?:USD|BRL|EUR)\b|[€£$]',src)!=re.findall(r'R\$|US\$|\b(?:USD|BRL|EUR)\b|[€£$]',dst):return 'currency changed'
 if src.count('&lt;')!=dst.count('&lt;')or src.count('&gt;')!=dst.count('&gt;'):return 'escaped hints changed'
 if re.findall(r'</?[A-Za-z][^>]*>',src)!=re.findall(r'</?[A-Za-z][^>]*>',dst):return 'HTML tags or attributes changed'
 for pattern in [r'\{[a-zA-Z_]+\}',r'https?://[^\s<>"\']+']:
  if sorted(re.findall(pattern,src))!=sorted(re.findall(pattern,dst)):return 'placeholder or URL changed'
 return None

def alternates(soup,page,lang):
 if soup.head is None:
  head=soup.new_tag('head');soup.html.insert(0,head)
  for t in list(soup.html.children):
   if getattr(t,'name',None)in ['meta','title','link','style']:head.append(t.extract())
 if soup.body is None:
  body=soup.new_tag('body')
  for t in list(soup.html.children):
   if t is not soup.head:body.append(t.extract())
  soup.html.append(body)
 for t in soup.select('link[rel=alternate],.langs'):t.decompose()
 for loc,(hl,label) in LANGS.items():
  href=page if loc==lang else (f'{loc}/{page}'if lang=='pt' else f'../{page}'if loc=='pt' else f'../{loc}/{page}')
  t=soup.new_tag('link',rel='alternate',hreflang=hl,href=href);t['data-nome']=label;soup.head.append(t)
 if page!='curso.html':
  bar=soup.select_one('.bar-inner')or soup.body
  nav=soup.new_tag('nav',attrs={'class':'langs','aria-label':{'pt':'Idioma','en':'Language','es':'Idioma'}[lang]})
  nav['style']='display:flex;gap:10px;flex-wrap:wrap;font-size:14px;padding:8px 0'
  for l in soup.select('link[rel=alternate]'):
   a=soup.new_tag('a',href=l['href']);a.string=l['data-nome']
   if l['hreflang']==LANGS[lang][0]:a['aria-current']='page'
   nav.append(a)
  bar.append(nav)

def build(root):
 src=json.loads(read(root/'i18n/source.json'))
 protected={p.name for p in (root/'assets').rglob('*')if p.is_file()}
 for name,_ in text_assets(root):protected.add(Path(name.split('::')[-1]).name)
 for p in (root/'assets').rglob('*.zip'):
  with zipfile.ZipFile(p)as z:protected.update(Path(n).name for n in z.namelist()if not n.endswith('/'))
 for lang in ['en','es']:
  reuse=root/f'i18n/reused-{lang}.json'
  trans=json.loads(read(reuse))if reuse.exists()else {}
  for i in range(1,4):trans.update(json.loads(read(root/f'i18n/{lang}-{i}.json')))
  override=root/f'i18n/{lang}-overrides.json'
  if override.exists():trans.update(json.loads(read(override)))
  hints=root/'i18n/human-placeholders.json'
  if hints.exists():
   phrases=json.loads(read(hints))['phrases']
   trans={k:re.sub(r'&lt;([^<>]*?)&gt;',lambda m:'&lt;'+phrases.get(m[1],{}).get(lang,m[1])+'&gt;',v)for k,v in trans.items()}
  missing=set(src)-set(trans)
  if missing:raise ValueError(f'{lang}: {len(missing)} missing: {list(missing)[:5]}')
  errors={k:validate(s,trans[k])for k,s in src.items()if validate(s,trans[k])}
  for k,s in src.items():
   if any(name in s and s.count(name)!=trans[k].count(name)for name in protected):errors[k]='download filename changed'
  if errors:writejson(root/f'i18n/{lang}-errors.json',errors);raise ValueError(f'{lang}: {len(errors)} invalid units')
  (root/f'i18n/{lang}-errors.json').unlink(missing_ok=True)
  writejson(root/f'i18n/{lang}.json',trans)
  def tr(s):return trans[key(s)]if eligible(s) else s
  localized_assets={name.split('::')[0]for name,_ in text_assets(root)}
  for name,txt in text_assets(root):
   if '::'not in name:
    dest=root/lang/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(translate_text(txt,tr))
  for name in sorted(localized_assets):
   if name.endswith('.zip'):
    dest=root/lang/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(root/name)as source,zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED)as z:
     for info in source.infolist():
      value=source.read(info.filename)
      if Path(info.filename).suffix.lower()in ['.txt','.md','.csv','.srt','.vtt']:value=translate_text(value.decode('utf-8'),tr).encode('utf-8')
      z.writestr(info,value)
  for p in sorted(root.glob('*.html')):
   if p.name=='index.html':continue
   soup=BeautifulSoup(read(p),'html.parser')
   for old in soup.select('.langs,link[rel=alternate]'):old.decompose()
   bs,ns=blocks(soup)
   for t in bs:
    frag=BeautifulSoup(tr(inner(t)),'html.parser');t.clear()
    for c in list(frag.contents):t.append(c)
   for n in ns:n.replace_with(tr(str(n)))
   for a in ATTRS:
    for t in soup.find_all(attrs={a:True}):t[a]=tr(t[a])
   for t in soup.select('meta[name="description"],meta[property="og:title"],meta[property="og:description"]'):t['content']=tr(t.get('content',''))
   for t in soup.find_all('script',type='application/json'):t.string=json.dumps(walkstrings(json.loads(t.string or '{}'),tr),ensure_ascii=False)
   for t in soup.find_all('script'):
    if t.string and t.get('type')!='application/json' and p.name not in ['curso.html','landing.html']:
     t.string=translate_js(t.string,tr)
     t.string=re.sub(r"(const KEY=)(['\"])([^'\"]+)\2",lambda m:m[1]+json.dumps(m[3]+'-'+lang),t.string)
     t.string=guard_support(t.string)
     t.string=t.string.replace("toLocaleString('pt-BR'", "toLocaleString("+json.dumps({'en':'en-US','es':'es-419'}[lang]))
   soup.html['lang']=LANGS[lang][0]
   mc=soup.find('meta',attrs={'name':'curso'})
   if mc:mc['content']+='-'+lang
   for t in soup.find_all(True):
    for a in ['src','href','poster']:
     v=t.get(a,'')
     if v=='assets/curso-i18n.js':t[a]='assets/curso.js';v='assets/curso.js'
     if v.startswith(('assets/','capa/')) and v not in localized_assets and v not in ['assets/curso.js','assets/curso-i18n.js'] and not(v.endswith('.js') and (root/v).exists()):t[a]='../'+v
   for t in soup.find_all('script'):
    if t.string and 'localStorage.getItem('in t.string and mc:
     t.string=re.sub(r'getItem\("([^\"]+)"\)',lambda m:f'getItem("{m[1]}-{lang}")',t.string)
   alternates(soup,p.name,lang)
   dest=root/lang/p.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(str(soup))
  js=guarded_engine(read(root/'assets/curso.js'));m,L=language_object(js);L=walkstrings(L,tr)
  L['capRe']={'en':'^(by the end of this lesson,? )?you (can|will be able to|have|will have) ','es':'^(al final de esta lección,? )?(ya )?(puedes|podrás|tienes|tendrás) '}[lang]
  p=root/lang/'assets/curso.js';p.parent.mkdir(exist_ok=True);p.write_text(js[:m.start(1)]+json.dumps(L,ensure_ascii=False)+js[m.end(1):])
  for f in (root/'assets').glob('*.js'):
   if f.name not in ['curso.js','curso-i18n.js']:
    code=translate_js(read(f),tr);code=re.sub(r"(const KEY=)(['\"])([^'\"]+)\2",lambda m:m[1]+json.dumps(m[3]+'-'+lang),code)
    (root/lang/'assets'/f.name).write_text(guard_support(code))
  (root/lang/'index.html').write_text(f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=landing.html"><title>{tr(BeautifulSoup(read(root/"landing.html"),"html.parser").title.string)}</title><a href="landing.html">{LANGS[lang][1]}</a></html>')
 (root/'assets/curso-i18n.js').write_text(guarded_engine(read(root/'assets/curso.js')))
 for p in sorted(root.glob('*.html')):
  if p.name=='index.html':continue
  soup=BeautifulSoup(read(p),'html.parser');alternates(soup,p.name,'pt')
  for t in soup.select('script[src="assets/curso.js"]'):t['src']='assets/curso-i18n.js'
  for t in soup.find_all('script'):
   if t.string and t.get('type')!='application/json':t.string=guard_support(t.string)
  p.write_text(str(soup))
 for p in (root/'assets').glob('*.js'):
  if p.name not in ['curso.js','curso-i18n.js']:
   before=read(p);after=guard_support(before)
   if before!=after:p.write_text(after)
 print('Built',root.name,'EN/ES; no model calls')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('command',choices=['extract','build']);ap.add_argument('root',type=Path);a=ap.parse_args();globals()[a.command](a.root.resolve())
