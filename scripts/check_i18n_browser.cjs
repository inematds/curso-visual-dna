const fs=require('fs'),path=require('path');
const {chromium}=require('/home/nmaldaner/projetos/agent-browser/node_modules/playwright');
const root=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({args:['--disable-gpu']});const checks=[];
 for(const locale of ['pt','en','es']){
  const base=locale==='pt'?root:path.join(root,locale);
  const ctx=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce',acceptDownloads:true});
  await ctx.route(/^https?:/,r=>r.abort()); // strictly offline; do not call font or other APIs
  const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.dismiss());
  await page.goto('file://'+path.join(base,'curso.html')+'#aula-1');await page.waitForTimeout(250);
  const ck=await page.$eval('meta[name=curso]',e=>e.content);
  const clk=sel=>page.$eval(sel,e=>e.click());
  await clk('#v-aula-1 .fecho-motor .big');
  await clk('#menubtn');await clk('#m-jor');
  const promise=page.waitForEvent('download');await clk('#expbtn');const download=await promise;
  const exportPath=path.join(out,'progress-'+locale+'.json');await download.saveAs(exportPath);
  const data=JSON.parse(fs.readFileSync(exportPath,'utf8'));
  if(data.course!==ck||!data.aulas['1'].done)throw Error(locale+': invalid export');
  const before=await page.evaluate(k=>localStorage.getItem(k),ck);
  const bad={...data,course:ck+'-other'};
  await page.setInputFiles('#impfile',{name:'wrong-language.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(bad))});await page.waitForTimeout(250);
  if(await page.evaluate(k=>localStorage.getItem(k),ck)!==before)throw Error(locale+': cross-language import changed state');
  await page.setInputFiles('#impfile',{name:'valid.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});await page.waitForTimeout(350);
  if(!(await page.evaluate(k=>JSON.parse(localStorage.getItem(k)).aulas['1'].done,ck)))throw Error(locale+': same-language import failed');
  await page.goto('file://'+path.join(base,'curso.html')+'#aula-5');await page.waitForTimeout(150);await clk('#menubtn');
  const links=await page.$$eval('#menu .langrow a',xs=>xs.map(a=>{a.addEventListener('click',e=>e.preventDefault(),{once:true});a.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));return {href:a.href,text:a.textContent}}));
  if(links.length!==3||links.some(a=>!a.href.endsWith('#aula-5')))throw Error(locale+': language links must preserve lesson');
  await page.keyboard.press('Escape');
  const lessons=await page.$$eval('.view[data-aula]',xs=>xs.map(e=>e.getAttribute('data-aula')));
  for(const n of lessons){await page.goto('file://'+path.join(base,'curso.html')+'#aula-'+n);await page.waitForTimeout(40);
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error(locale+' lesson '+n+': overflow');
   const img=await page.$eval('#v-aula-'+n+' .cena img',async e=>{try{await e.decode();return e.naturalWidth>0}catch{return false}});if(!img)throw Error(locale+' lesson '+n+': image missing');
  }
  for(const n of [1,Math.ceil(lessons.length/2),lessons.length]){
   await page.goto('file://'+path.join(base,'curso.html')+'#aula-'+n);await page.waitForTimeout(100);
   await page.screenshot({path:path.join(out,locale+'-aula-'+n+'.png'),fullPage:true});
  }
  const support=[];
  for(const f of fs.readdirSync(base).filter(f=>f.endsWith('.html')&&f!=='index.html')){
   await page.goto('file://'+path.join(base,f));await page.waitForTimeout(80);
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error(locale+' '+f+': overflow');
   if(await page.locator('#base').count()&&await page.locator('#acoes').count()){
    await page.locator('#base').fill('80');await page.locator('#acoes').fill('10');
    const expected=(12.5).toLocaleString({pt:'pt-BR',en:'en-US',es:'es-419'}[locale],{maximumFractionDigits:2})+'%';
    if(await page.locator('#taxa').textContent()!==expected)throw Error(locale+': rate calculation or formatting');
    for(const invalid of ['0','','1.5']){
     await page.locator('#base').fill(invalid);
     if((await page.locator('#taxa').textContent()).includes('%'))throw Error(locale+': rate accepted invalid base');
    }
    await page.locator('#base').fill('100');
    if(await page.locator('#taxa').textContent()!=='10%')throw Error(locale+': rate did not recover');
    support.push({file:f,rateCalculation:true,invalidBaseRejected:true});
   }
   if(f==='calculadora.html'){
    const formatLocale={pt:'pt-BR',en:'en-US',es:'es-419'}[locale];
    const money=n=>n.toLocaleString(formatLocale,{style:'currency',currency:'BRL'});
    for(const [option,cost] of [['A',600],['B',1170],['C',1740]]){
     await page.locator('#pacote').selectOption(option);
     if(await page.locator('#custo').textContent()!==money(cost)||await page.locator('#preco').textContent()!==money(cost/.7))throw Error(locale+': calculator amount or currency');
    }
    await page.locator('#taxas').fill('80');
    if(!(await page.locator('#erro').textContent()).trim()||(await page.locator('#formula').textContent()).trim())throw Error(locale+': calculator must reject 100%');
    await page.locator('#pacote').selectOption('A');await page.locator('#horas').fill('');
    if(!(await page.locator('#erro').textContent()).trim())throw Error(locale+': calculator accepted empty input');
    await page.locator('#pacote').selectOption('B');
    if(await page.locator('#preco').textContent()!==money(1170/.7))throw Error(locale+': calculator did not recover');
    support.push({file:f,knownAmounts:true,currency:'BRL',invalidInputsRejected:true});
   }
   if(['planner.html','sprint.html'].includes(f)){
    await page.locator('#projeto').fill('I18N verification');
    if(f==='sprint.html')await page.locator('#ultima input[type=checkbox]').check();
    const event=page.waitForEvent('download');await page.locator('#exportar').click();const d=await event;
    const exported=JSON.parse(fs.readFileSync(await d.path(),'utf8'));
    if(!exported.course||exported.locale.split('-')[0]!==locale)throw Error(f+': missing locale metadata');
    if(f==='sprint.html'&&!exported.ultima.realizada)throw Error(f+': state key changed');
    await page.reload();if(await page.locator('#projeto').inputValue()!=='I18N verification')throw Error(f+': persistence');
    const importState=async value=>{await page.setInputFiles('#importar',{name:'state.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});await page.waitForTimeout(100);};
    await importState({...exported,course:exported.course+'-other',projeto:'Wrong locale'});
    if(await page.locator('#projeto').inputValue()!=='I18N verification')throw Error(f+': accepted another locale');
    await importState({...exported,projeto:'Restored'});
    if(await page.locator('#projeto').inputValue()!=='Restored')throw Error(f+': import');
    support.push({file:f,persistence:true,exportImport:true,crossLanguageRejected:true});
   }
  }
  await page.setViewportSize({width:1440,height:1000});
  await page.goto('file://'+path.join(base,'curso.html')+'#aula-'+Math.ceil(lessons.length/2));
  for(const theme of ['papel','escuro','sepia']){
   await page.evaluate(t=>document.documentElement.setAttribute('data-theme',t),theme);
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error(locale+': desktop overflow');
   await page.screenshot({path:path.join(out,locale+'-desktop-'+theme+'.png')});
  }
  if(errors.length)throw Error(locale+': JS errors '+errors.join(';'));
  checks.push({locale,lessons:lessons.length,exportImport:true,crossLanguageRejected:true,languageLinks:true,mobile:true,desktopThemes:true,images:true,support,errors});await ctx.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'browser-checks.json'),JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));
})().catch(e=>{console.error(e);process.exit(1)});
