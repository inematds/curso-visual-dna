// Offline JavaScript literal extraction. No network or model calls.
const fs=require('fs');
const parser=require('/home/nmaldaner/projetos/portal/node_modules/next/dist/compiled/babel/parser.js');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const ast=parser.parse(input.code,{sourceType:'unambiguous'}), out=[];
const WORDS=new Set(['Data','Dia','Tarefa','Formato','Situação','Imagem','Vídeo','imagem','vídeo','carrossel','planejado','pronto','publicado','concluído','agendada','realizada','pendente','registrada']);
function technical(n,p){
 if(!p)return false;
 if((p.type==='ObjectProperty'||p.type==='ObjectMethod')&&p.key===n)return true;
 if(p.type==='MemberExpression'&&p.property===n)return true;
 if(p.type==='CallExpression'){
  const name=p.callee.name||p.callee.property?.name,index=p.arguments.indexOf(n);
  if(['field','check','select'].includes(name)&&index===1)return true;
  if(['querySelector','querySelectorAll','getElementById','createElement','addEventListener','getAttribute','setAttribute','removeAttribute'].includes(name)&&index===0)return true;
 }
 if(p.type==='AssignmentExpression'&&['className','id','type'].includes(p.left.property?.name))return true;
 return false;
}
function walk(n,parent){if(!n||typeof n!=='object')return;
 if(n.type==='StringLiteral'){
  const v=n.value;
  const human=/[À-ÿ]/.test(v)||/[A-Za-z][ ]+[A-Za-z]/.test(v)||WORDS.has(v.trim());
  if(human&&!technical(n,parent)&&!/^https?:|^data:|^image\/|^application\/|^font/.test(v))out.push({start:n.start,end:n.end,value:v,kind:'string'});
 }
 if(n.type==='TemplateElement'&&/[A-Za-zÀ-ÿ]/.test(n.value.raw))out.push({start:n.start,end:n.end,value:n.value.raw,kind:'template'});
 for(const [k,v]of Object.entries(n)){if(['loc','extra','comments','tokens'].includes(k))continue;if(Array.isArray(v))v.forEach(x=>walk(x,n));else if(v&&typeof v==='object')walk(v,n);}
}
walk(ast);console.log(JSON.stringify(out));
