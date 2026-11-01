"""Oyun salonu oyunları (tam ekran HTML/JS). app.py ile AYNI klasörde durmalıdır."""

ARCADE_SHARED = r'''<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#04252b;--bg2:#073b44;--card:#0b4a55;--line:rgba(94,234,212,.28);--t:#e6fffb;--mut:#8fd9cf;--ac:#2dd4bf;--ac2:#22d3ee;--bad:#fb7185;--ok:#4ade80;--gold:#fbbf24}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:radial-gradient(1200px 700px at 20% -10%,#0e6b73 0,transparent 60%),linear-gradient(160deg,#04252b,#06323a 60%,#041f26);color:var(--t);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;overflow:hidden}
#app{position:absolute;inset:0;display:flex;flex-direction:column;padding:10px 14px 12px;gap:8px;overflow:auto}
.top{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.top h2{margin:0;font-size:19px;letter-spacing:.2px}
.sp{flex:1}
.chip{background:rgba(255,255,255,.08);border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-weight:700;font-size:14px}
.btn{border:0;border-radius:14px;padding:10px 16px;font-weight:800;font-size:15px;cursor:pointer;color:#042f2e;background:linear-gradient(135deg,#5eead4,#22d3ee);box-shadow:0 4px 0 #0f766e;font-family:inherit}
.btn:active{transform:translateY(3px);box-shadow:0 1px 0 #0f766e}
.btn.alt{background:rgba(255,255,255,.1);color:var(--t);box-shadow:0 4px 0 rgba(0,0,0,.35);border:1px solid var(--line)}
.btn.bad{background:linear-gradient(135deg,#fda4af,#fb7185);box-shadow:0 4px 0 #9f1239}
.btn[disabled]{opacity:.45;cursor:not-allowed}
.panel{background:rgba(255,255,255,.06);border:1px solid var(--line);border-radius:20px;padding:12px}
.center{display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;gap:12px;text-align:center}
.msg{min-height:24px;font-weight:700;color:var(--mut);text-align:center}
.msg.ok{color:var(--ok)}.msg.bad{color:var(--bad)}
.row{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;align-items:center}
.big{font-size:clamp(28px,6vw,52px);font-weight:900}
.stars{font-size:34px;letter-spacing:4px}
.pop{animation:pop .35s ease}
@keyframes pop{0%{transform:scale(.6);opacity:0}70%{transform:scale(1.08)}100%{transform:scale(1);opacity:1}}
.shake{animation:shake .35s}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-7px)}75%{transform:translateX(7px)}}
</style>
<script>
window.onerror=function(m){try{document.title='JSERR:'+m}catch(e){}};
const $=(s,r)=> (r||document).querySelector(s);
function h(tag,attrs,...kids){const e=document.createElement(tag);for(const k in (attrs||{})){const v=attrs[k];if(k==='class')e.className=v;else if(k==='style')e.style.cssText=v;else if(k.startsWith('on'))e[k]=v;else if(k==='html')e.innerHTML=v;else if(v===false||v==null)continue;else if(v===true)e.setAttribute(k,'');else e.setAttribute(k,v)}for(const c of kids.flat()){if(c==null||c===false)continue;e.append(c.nodeType?c:document.createTextNode(c))}return e}
const rnd=(a,b)=>a+Math.floor(Math.random()*(b-a+1));
const pick=a=>a[Math.floor(Math.random()*a.length)];
function shuf(a){a=a.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let _ac=null;
function beep(f,d,t,v){try{_ac=_ac||new (window.AudioContext||window.webkitAudioContext)();const o=_ac.createOscillator(),g=_ac.createGain();o.type=t||'sine';o.frequency.value=f;g.gain.value=v||.05;o.connect(g);g.connect(_ac.destination);o.start();g.gain.exponentialRampToValueAtTime(.0001,_ac.currentTime+(d||.15));o.stop(_ac.currentTime+(d||.15))}catch(e){}}
const sfx={ok(){beep(660,.12);setTimeout(()=>beep(880,.15),110)},bad(){beep(180,.25,'sawtooth',.04)},tap(){beep(520,.05,'square',.025)},win(){[523,659,784,1046].forEach((f,i)=>setTimeout(()=>beep(f,.2),i*120))}};
function store(k,v){try{if(v===undefined){return JSON.parse(localStorage.getItem('adenmind_'+k))}localStorage.setItem('adenmind_'+k,JSON.stringify(v))}catch(e){return null}}
</script>
'''

ARCADE_HTML = {}
ARCADE_HTML['uno'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.card{width:62px;height:92px;border-radius:10px;border:3px solid #fff;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:28px;color:#fff;position:relative;cursor:pointer;flex:none;box-shadow:0 4px 8px rgba(0,0,0,.4);transition:transform .15s;user-select:none;text-shadow:0 2px 0 rgba(0,0,0,.35)}
.card.R{background:#e11d48}.card.Y{background:#eab308;color:#422006;text-shadow:none}.card.G{background:#16a34a}.card.B{background:#2563eb}.card.W{background:linear-gradient(135deg,#e11d48 25%,#eab308 25% 50%,#16a34a 50% 75%,#2563eb 75%)}
.card.back{background:#111;border-color:#fff;color:#f43f5e;font-size:15px}
.card.can{transform:translateY(-12px);box-shadow:0 0 0 3px var(--gold),0 6px 12px rgba(0,0,0,.5)}
.card.no{opacity:.55;cursor:not-allowed}
.card small{position:absolute;top:3px;left:5px;font-size:12px}
.hand{display:flex;gap:-18px;justify-content:center;flex-wrap:wrap;gap:6px;padding:14px 4px 6px;max-height:210px;overflow:auto}
.bots{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.bot{padding:8px 12px;border-radius:16px;background:rgba(255,255,255,.07);border:2px solid transparent;text-align:center;min-width:110px}
.bot.act{border-color:var(--gold);background:rgba(251,191,36,.15)}
.mid{display:flex;align-items:center;justify-content:center;gap:22px}
.col{width:34px;height:34px;border-radius:50%;border:3px solid #fff;display:inline-block;vertical-align:middle}
.cp{display:flex;gap:10px;justify-content:center}.cp .col{width:54px;height:54px;cursor:pointer}
</style></head><body><div id="app"></div><script>
const app=$('#app');const COL=['R','Y','G','B'],CN={R:'Kırmızı',Y:'Sarı',G:'Yeşil',B:'Mavi'},CH={R:'#e11d48',Y:'#eab308',G:'#16a34a',B:'#2563eb'};
function deck(){const d=[];for(const c of COL){d.push({c,v:'0'});for(let n=1;n<=9;n++)d.push({c,v:''+n},{c,v:''+n});for(const v of['⊘','⇄','+2'])d.push({c,v},{c,v})}
 for(let i=0;i<4;i++)d.push({c:'W',v:'W'},{c:'W',v:'+4'});return d}
let P,draw_,disc,tp,cur,dir,color,over,busy,mustPick,names,stats={w:0,g:0},pend,unoMsg='';
function start(n){names=['Sen','Robo Ada','Robo Can','Robo Ege'].slice(0,n);draw_=shuf(deck());P=names.map(()=>[]);for(let i=0;i<7;i++)P.forEach(h=>h.push(draw_.pop()));
 while(true){tp=draw_.pop();if(tp.c==='W'||['⊘','⇄','+2'].includes(tp.v))draw_.unshift(tp);else break}
 disc=[tp];color=tp.c;cur=0;dir=1;over=false;busy=false;mustPick=false;pend=null;unoMsg='İlk kart açıldı. Sıra sende!';render()}
function total(){return draw_.length+disc.length+P.reduce((a,h)=>a+h.length,0)}
function drawCard(i){if(!draw_.length){const keep=disc.pop();draw_=shuf(disc);disc=[keep]}if(!draw_.length)return null;const c=draw_.pop();P[i].push(c);return c}
function playable(c){return c.c==='W'||c.c===color||c.v===tp.v}
function nxt(i,k=1){const n=names.length;return((i+dir*k)%n+n)%n}
function label(c){return c.v==='W'?'🌈':c.v}
function cardEl(c,opt){const e=h('div',{class:'card '+c.c+(opt.can?' can':'')+(opt.no?' no':''),onclick:opt.click},h('small',{},label(c)),label(c));return e}
function render(){app.innerHTML='';
 app.append(h('div',{class:'top'},h('h2',{},'🃏 UNO · Yapay zekâya karşı'),h('span',{class:'sp'}),h('span',{class:'chip'},'🏆 '+stats.w+' / '+stats.g),h('button',{class:'btn alt',onclick:menu},'☰ Menü')));
 app.append(h('div',{class:'bots'},names.slice(1).map((n,k)=>h('div',{class:'bot'+(cur===k+1&&!over?' act':'')},h('div',{},'🤖 '+n),h('div',{style:'font-weight:800'},'🂠 '+P[k+1].length+(P[k+1].length===1?'  UNO!':''))))));
 const topEl=cardEl(tp,{});const pile=h('div',{class:'card back',onclick:()=>{if(cur===0&&!over&&!busy&&!mustPick&&!pend)humanDraw()}},'UNO');
 app.append(h('div',{class:'mid'},h('div',{style:'text-align:center'},pile,h('div',{class:'msg'},'Deste '+draw_.length)),topEl,h('div',{style:'text-align:center'},h('span',{class:'col',style:'background:'+CH[color]}),h('div',{class:'msg'},CN[color],' · ',dir===1?'↻':'↺'))));
 app.append(h('div',{class:'msg '+(over?'ok':''),id:'ms'},unoMsg));
 if(pend){const cp=h('div',{class:'cp'},COL.map(c=>h('span',{class:'col',style:'background:'+CH[c],onclick:()=>chooseColor(c)})));app.append(h('div',{class:'msg'},'Renk seç:'),cp)}
 const my=P[0];const myTurn=cur===0&&!over&&!busy&&!pend;
 app.append(h('div',{class:'hand'},my.map((c,i)=>{const ok=myTurn&&playable(c)&&(!mustPick||i===my.length-1);return cardEl(c,{can:ok,no:myTurn&&!ok,click:()=>humanPlay(i)})})));
 if(mustPick&&myTurn)app.append(h('div',{class:'row'},h('button',{class:'btn alt',onclick:()=>{mustPick=false;advance(0)}},'Pas geç')));
 if(over)app.append(h('div',{class:'row'},h('button',{class:'btn',onclick:()=>start(names.length)},'Yeni el')))}
function say(s){unoMsg=s}
function humanDraw(){const c=drawCard(0);sfx.tap();if(c&&playable(c)){mustPick=true;say('Çektiğin kart oynanabilir: oyna ya da pas geç.');render()}else{say('Oynanacak kart yok, pas.');render();setTimeout(()=>advance(0),500)}}
function humanPlay(i){if(over||busy||cur!==0||pend)return;const c=P[0][i];if(!playable(c)||(mustPick&&i!==P[0].length-1))return;mustPick=false;sfx.tap();P[0].splice(i,1);place(0,c)}
function place(i,c){disc.push(c);tp=c;if(c.c!=='W')color=c.c;
 if(!P[i].length){over=true;if(i===0)stats.w++;stats.g++;say(i===0?'🎉 Kazandın!':'😅 '+names[i]+' kazandı');i===0?sfx.win():sfx.bad();render();return}
 let m=names[i]+': '+label(c)+' oynadı';if(P[i].length===1)m+=' – UNO!';say(m);
 if(c.c==='W'){if(i===0){pend=c;render();return}color=bestColor(P[i]);say(m+' · renk '+CN[color])}
 effect(i,c)}
function chooseColor(c){color=c;const card=pend;pend=null;effect(0,card)}
function effect(i,c){let skip=0,n=names.length;
 if(c.v==='⇄'){dir*=-1;if(n===2)skip=1}else if(c.v==='⊘')skip=1;
 else if(c.v==='+2'){const v=nxt(i);for(let k=0;k<2;k++)drawCard(v);skip=1}
 else if(c.v==='+4'){const v=nxt(i);for(let k=0;k<4;k++)drawCard(v);skip=1}
 render();advance(i,skip)}
function advance(i,skip=0){cur=nxt(i,1+skip);render();if(cur!==0&&!over){busy=true;setTimeout(botTurn,900)}}
function bestColor(h2){const cnt={R:0,Y:0,G:0,B:0};h2.forEach(c=>{if(cnt[c.c]!==undefined)cnt[c.c]++});return COL.reduce((a,b)=>cnt[b]>cnt[a]?b:a,pick(COL))}
function botTurn(){busy=false;if(over)return;const i=cur,hand=P[i];
 let opts=hand.map((c,k)=>({c,k})).filter(o=>playable(o.c));
 if(!opts.length){const c=drawCard(i);say(names[i]+' kart çekti');if(c&&playable(c))opts=[{c,k:hand.length-1}];else{render();return setTimeout(()=>advance(i),600)}}
 const nextN=P[nxt(i)].length;
 opts.sort((a,b)=>sc(b.c,nextN,hand)-sc(a.c,nextN,hand));const o=opts[0];hand.splice(o.k,1);sfx.tap();place(i,o.c)}
function sc(c,nextN,hand){let s=0;if(c.c==='W')s-=5;if(['+2','+4','⊘','⇄'].includes(c.v))s+=(nextN<=2?8:2);if(c.v==='+4')s-=(hand.length>3?6:0);
 if(c.c!=='W'&&hand.filter(x=>x.c===c.c).length>2)s+=3;if(/\d/.test(c.v))s+=+c.v/10;return s+Math.random()}
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'🃏 UNO'),h('div',{class:'msg'},'Rengi ya da sayıyı eşleştir; özel kartları akıllıca kullan. İlk bitiren kazanır!'),
 h('div',{class:'row'},[[2,'1 rakip'],[3,'2 rakip'],[4,'3 rakip']].map(([n,l])=>h('button',{class:'btn',onclick:()=>start(n)},l)))))}
menu();
</script></body></html>
'''

ARCADE_HTML['sudoku'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.grid{display:grid;gap:0;border:3px solid var(--ac);border-radius:12px;overflow:hidden;background:#052f37;margin:auto}
.c{display:flex;align-items:center;justify-content:center;font-weight:800;cursor:pointer;border:1px solid rgba(94,234,212,.18);user-select:none;position:relative}
.c.given{color:#fff;background:rgba(255,255,255,.07)}
.c.mine{color:var(--ac2)}
.c.sel{background:rgba(45,212,191,.35)}
.c.peer{background:rgba(45,212,191,.12)}
.c.same{background:rgba(251,191,36,.28)}
.c.err{color:var(--bad)!important;background:rgba(251,113,133,.25)}
.c.bR{border-right:3px solid var(--ac)}.c.bB{border-bottom:3px solid var(--ac)}
.c .nt{position:absolute;inset:1px;display:grid;font-size:.38em;color:var(--mut);font-weight:600;line-height:1}
.pad .btn{min-width:46px;padding:10px 0}
</style></head><body><div id="app"></div><script>
const app=$('#app');
let N=9,BR=3,BC=3,sol,puz,cur,sel=-1,notes=false,nt,mist=0,t0=0,tm=null,hints=0,done=false;
function boxOf(r,c){return Math.floor(r/BR)*(N/BC)+Math.floor(c/BC)}
function ok(g,i,v){const r=Math.floor(i/N),c=i%N;for(let k=0;k<N;k++){if(g[r*N+k]===v&&k!==c)return false;if(g[k*N+c]===v&&k!==r)return false}
 const br=Math.floor(r/BR)*BR,bc=Math.floor(c/BC)*BC;for(let a=0;a<BR;a++)for(let b=0;b<BC;b++){const j=(br+a)*N+bc+b;if(j!==i&&g[j]===v)return false}return true}
function solve(g,limit,randomize){let count=0,res=null;
 function rec(){let best=-1,bc=99,bo=null;
  for(let i=0;i<N*N;i++)if(!g[i]){const o=[];for(let v=1;v<=N;v++)if(ok(g,i,v))o.push(v);if(o.length<bc){bc=o.length;best=i;bo=o;if(bc===0)return}}
  if(best<0){count++;if(!res)res=g.slice();return}
  if(randomize)bo=shuf(bo);
  for(const v of bo){g[best]=v;rec();g[best]=0;if(count>=limit)return}}
 rec();return{count,res}}
function gen(diff){const full=solve(new Array(N*N).fill(0),1,true).res;sol=full;
 const holes={4:[6,8,10],6:[16,20,24],9:[38,46,52]}[N][diff];
 let p=full.slice();const order=shuf([...Array(N*N).keys()]);let removed=0;
 for(const i of order){if(removed>=holes)break;const v=p[i];p[i]=0;const t=p.slice();if(solve(t,2).count!==1)p[i]=v;else removed++}
 puz=p;cur=p.slice();nt=Array.from({length:N*N},()=>new Set())}
function menu(){clearInterval(tm);app.innerHTML='';app.append(h('div',{class:'center'},
 h('div',{class:'big'},'🔢 Sudoku'),h('div',{class:'msg'},'Her satır, sütun ve kutuda sayılar bir kez geçmeli. Tek çözümlü yeni bulmaca her seferinde!'),
 h('div',{class:'row'},[[4,'Mini 4×4'],[6,'Orta 6×6'],[9,'Klasik 9×9']].map(([n,l])=>h('button',{class:'btn',onclick:()=>{N=n;BR=n===9?3:2;BC=n===4?2:3;pick2()}},l)))))}
function pick2(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'Zorluk'),h('div',{class:'row'},['Kolay','Orta','Zor'].map((l,i)=>h('button',{class:'btn',onclick:()=>start(i)},l)))))}
function start(d){app.innerHTML='<div class="center big">Hazırlanıyor…</div>';setTimeout(()=>{gen(d);sel=-1;mist=0;hints=0;done=false;t0=Date.now();draw();clearInterval(tm);tm=setInterval(tick,1000)},30)}
function tick(){const e=$('#tm');if(e)e.textContent='⏱ '+fmt((Date.now()-t0)/1000|0)}
function fmt(s){return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')}
function conflicts(i){return cur[i]&&!ok(cur,i,cur[i])}
function draw(){app.innerHTML='';
 app.append(h('div',{class:'top'},h('h2',{},'🔢 Sudoku '+N+'×'+N),h('span',{class:'sp'}),h('span',{class:'chip',id:'tm'},'⏱ 0:00'),h('span',{class:'chip'},'❌ '+mist),h('button',{class:'btn alt',onclick:menu},'☰ Menü')));
 const size=Math.min(innerHeight-250,innerWidth-40,560);const cs=Math.floor(size/N);
 const g=h('div',{class:'grid',style:`grid-template-columns:repeat(${N},${cs}px);font-size:${cs*.55}px`});
 for(let i=0;i<N*N;i++){const r=Math.floor(i/N),c=i%N;let cl='c '+(puz[i]?'given':(cur[i]?'mine':''));
  if(sel>=0){const sr=Math.floor(sel/N),sc=sel%N;if(i===sel)cl+=' sel';else if(cur[sel]&&cur[i]===cur[sel])cl+=' same';else if(sr===r||sc===c||boxOf(sr,sc)===boxOf(r,c))cl+=' peer'}
  if(conflicts(i))cl+=' err';if((c+1)%BC===0&&c<N-1)cl+=' bR';if((r+1)%BR===0&&r<N-1)cl+=' bB';
  const cell=h('div',{class:cl,style:`height:${cs}px`,onclick:()=>{sel=i;sfx.tap();draw()}},cur[i]||'');
  if(!cur[i]&&nt[i].size){const n=h('div',{class:'nt',style:`grid-template-columns:repeat(${BC},1fr)`});for(let v=1;v<=N;v++)n.append(h('span',{style:'text-align:center'},nt[i].has(v)?v:''));cell.append(n)}
  g.append(cell)}
 app.append(g);
 const pad=h('div',{class:'row pad'});for(let v=1;v<=N;v++)pad.append(h('button',{class:'btn',onclick:()=>put(v)},v));
 pad.append(h('button',{class:'btn alt',onclick:()=>put(0)},'⌫'));
 app.append(pad,h('div',{class:'row'},h('button',{class:'btn alt',onclick:()=>{notes=!notes;draw()}},notes?'✏️ Not: AÇIK':'✏️ Not: kapalı'),h('button',{class:'btn alt',onclick:hint},'💡 İpucu ('+hints+')'),h('button',{class:'btn alt',onclick:()=>start(0)},'🔄 Yeni')),h('div',{class:'msg',id:'ms'},''))}
function put(v){if(done||sel<0||puz[sel])return;
 if(notes&&v){nt[sel].has(v)?nt[sel].delete(v):nt[sel].add(v);cur[sel]=0;draw();return}
 cur[sel]=v;nt[sel].clear();if(v){if(sol[sel]!==v){mist++;sfx.bad()}else{sfx.ok();for(let i=0;i<N*N;i++)if(i!==sel)nt[i].delete(v)}}
 draw();check()}
function hint(){if(done)return;const empt=[];for(let i=0;i<N*N;i++)if(cur[i]!==sol[i])empt.push(i);if(!empt.length)return;const i=sel>=0&&cur[sel]!==sol[sel]?sel:pick(empt);cur[i]=sol[i];hints++;sel=i;draw();check()}
function check(){for(let i=0;i<N*N;i++)if(cur[i]!==sol[i])return;done=true;clearInterval(tm);sfx.win();
 const s=Math.max(1,3-Math.floor((mist+hints)/3));const secs=(Date.now()-t0)/1000|0;
 app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'stars'},'⭐'.repeat(s)+'☆'.repeat(3-s)),h('div',{class:'big'},'Bulmaca çözüldü! 🎉'),h('div',{class:'msg'},`Süre ${fmt(secs)} · Hata ${mist} · İpucu ${hints}`),h('div',{class:'row'},h('button',{class:'btn',onclick:()=>start(0)},'Yeni bulmaca'),h('button',{class:'btn alt',onclick:menu},'Menü'))));window.__won=true}
document.addEventListener('keydown',e=>{if(/^[1-9]$/.test(e.key)&&+e.key<=N)put(+e.key);else if(e.key==='Backspace'||e.key==='Delete')put(0);else if(sel>=0&&e.key.startsWith('Arrow')){const d={ArrowLeft:-1,ArrowRight:1,ArrowUp:-N,ArrowDown:N}[e.key];const n=sel+d;if(n>=0&&n<N*N&&!(Math.abs(d)===1&&Math.floor(n/N)!==Math.floor(sel/N))){sel=n;draw()}}});
menu();
</script></body></html>
'''

ARCADE_HTML['satranc'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.board{display:grid;grid-template-columns:repeat(8,1fr);border:3px solid var(--ac);border-radius:10px;overflow:hidden;margin:auto}
.sq{display:flex;align-items:center;justify-content:center;cursor:pointer;position:relative;user-select:none;line-height:1}
.sq.l{background:#cdeee8}.sq.d{background:#2a8f93}
.sq.sel{outline:4px solid var(--gold);outline-offset:-4px}
.sq.last{box-shadow:inset 0 0 0 100px rgba(251,191,36,.35)}
.sq.chk{box-shadow:inset 0 0 0 100px rgba(251,113,133,.65)}
.sq .dot{position:absolute;width:30%;height:30%;border-radius:50%;background:rgba(4,37,43,.45)}
.sq.cap::after{content:'';position:absolute;inset:3px;border:4px solid rgba(4,37,43,.5);border-radius:50%}
.pc{font-family:'Segoe UI Symbol','Noto Sans Symbols2','DejaVu Sans',serif;pointer-events:none}
.pc.w{color:#fff;text-shadow:0 0 2px #000,0 0 2px #000,0 0 3px #000,1px 1px 0 #000,-1px -1px 0 #000}
.pc.b{color:#0a1a1d;text-shadow:0 0 2px #7ee,0 0 1px #7ee}
</style></head><body><div id="app"></div><script>
// ===== MOTOR: 0..63, a8=0 ... h1=63; beyaz büyük harf, siyah küçük harf =====
const START='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const KN=[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]],KG=[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]];
const isW=p=>p&&p>='A'&&p<='Z';
function parse(fen){const [bd,t,c,ep,hm]=fen.split(' ');const b=[];for(const ch of bd){if(ch==='/')continue;if(/\d/.test(ch)){for(let i=0;i<+ch;i++)b.push('')}else b.push(ch)}
 return{b,turn:t,cr:{K:c.includes('K'),Q:c.includes('Q'),k:c.includes('k'),q:c.includes('q')},ep:ep==='-'?-1:('abcdefgh'.indexOf(ep[0])+(8-+ep[1])*8),hm:+hm||0}}
function attacked(b,sq,byWhite){const r=sq>>3,c=sq&7;
 const pr=byWhite?r+1:r-1;if(pr>=0&&pr<8){for(const dc of[-1,1]){const cc=c+dc;if(cc>=0&&cc<8&&b[pr*8+cc]===(byWhite?'P':'p'))return true}}
 for(const[dr,dc]of KN){const rr=r+dr,cc=c+dc;if(rr>=0&&rr<8&&cc>=0&&cc<8&&b[rr*8+cc]===(byWhite?'N':'n'))return true}
 for(const[dr,dc]of KG){const rr=r+dr,cc=c+dc;if(rr>=0&&rr<8&&cc>=0&&cc<8&&b[rr*8+cc]===(byWhite?'K':'k'))return true}
 for(const[dr,dc]of KG){let rr=r+dr,cc=c+dc;while(rr>=0&&rr<8&&cc>=0&&cc<8){const p=b[rr*8+cc];if(p){const diag=dr&&dc;const q=byWhite?'Q':'q',rk=byWhite?'R':'r',bs=byWhite?'B':'b';if(p===q||(diag?p===bs:p===rk))return true;break}rr+=dr;cc+=dc}}
 return false}
function kingSq(b,w){return b.indexOf(w?'K':'k')}
function pseudo(s){const{b,turn}=s,w=turn==='w',out=[];
 for(let i=0;i<64;i++){const p=b[i];if(!p||isW(p)!==w)continue;const r=i>>3,c=i&7,t=p.toLowerCase();
  if(t==='p'){const d=w?-1:1,start=w?6:1,last=w?0:7;const r1=r+d;
   if(r1>=0&&r1<8&&!b[r1*8+c]){const to=r1*8+c;if(r1===last)for(const pr of'qrbn')out.push({f:i,t:to,pr});else{out.push({f:i,t:to});if(r===start&&!b[(r+2*d)*8+c])out.push({f:i,t:(r+2*d)*8+c,dp:1})}}
   for(const dc of[-1,1]){const cc=c+dc;if(cc<0||cc>7||r1<0||r1>7)continue;const to=r1*8+cc,q=b[to];
    if(q&&isW(q)!==w){if(r1===last)for(const pr of'qrbn')out.push({f:i,t:to,pr});else out.push({f:i,t:to})}
    else if(!q&&to===s.ep)out.push({f:i,t:to,ep:1})}}
  else if(t==='n'||t==='k'){for(const[dr,dc]of(t==='n'?KN:KG)){const rr=r+dr,cc=c+dc;if(rr<0||rr>7||cc<0||cc>7)continue;const q=b[rr*8+cc];if(!q||isW(q)!==w)out.push({f:i,t:rr*8+cc})}
   if(t==='k'){const row=w?7:0;if(i===row*8+4&&!attacked(b,i,!w)){
     if(s.cr[w?'K':'k']&&!b[row*8+5]&&!b[row*8+6]&&b[row*8+7]===(w?'R':'r')&&!attacked(b,row*8+5,!w)&&!attacked(b,row*8+6,!w))out.push({f:i,t:row*8+6,cs:1});
     if(s.cr[w?'Q':'q']&&!b[row*8+3]&&!b[row*8+2]&&!b[row*8+1]&&b[row*8]===(w?'R':'r')&&!attacked(b,row*8+3,!w)&&!attacked(b,row*8+2,!w))out.push({f:i,t:row*8+2,cs:2})}}}
  else{const dirs=t==='r'?KG.filter(d=>!(d[0]&&d[1])):t==='b'?KG.filter(d=>d[0]&&d[1]):KG;
   for(const[dr,dc]of dirs){let rr=r+dr,cc=c+dc;while(rr>=0&&rr<8&&cc>=0&&cc<8){const q=b[rr*8+cc];if(!q)out.push({f:i,t:rr*8+cc});else{if(isW(q)!==w)out.push({f:i,t:rr*8+cc});break}rr+=dr;cc+=dc}}}}
 return out}
function make(s,m){const b=s.b.slice(),w=s.turn==='w',p=b[m.f];let cap=b[m.t];
 b[m.t]=m.pr?(w?m.pr.toUpperCase():m.pr):p;b[m.f]='';
 if(m.ep){b[m.t+(w?8:-8)]='';cap='p'}
 if(m.cs===1){b[m.t-1]=b[m.t+1];b[m.t+1]=''}if(m.cs===2){b[m.t+1]=b[m.t-2];b[m.t-2]=''}
 const cr={...s.cr};
 if(p==='K'){cr.K=cr.Q=false}if(p==='k'){cr.k=cr.q=false}
 if(m.f===63||m.t===63)cr.K=false;if(m.f===56||m.t===56)cr.Q=false;if(m.f===7||m.t===7)cr.k=false;if(m.f===0||m.t===0)cr.q=false;
 return{b,turn:w?'b':'w',cr,ep:m.dp?(m.f+m.t)/2:-1,hm:(p.toLowerCase()==='p'||cap)?0:s.hm+1,cap}}
function legal(s){const w=s.turn==='w',out=[];for(const m of pseudo(s)){const n=make(s,m);if(!attacked(n.b,kingSq(n.b,w),!w))out.push(m)}return out}
function inCheck(s){const w=s.turn==='w';return attacked(s.b,kingSq(s.b,w),!w)}
function perft(s,d){if(!d)return 1;let n=0;for(const m of legal(s)){n+=d===1?1:perft(make(s,m),d-1)}return n}
// ===== YZ: alfa-beta + taş-kare tabloları =====
const VAL={p:100,n:320,b:330,r:500,q:900,k:0};
const PST={p:[0,0,0,0,0,0,0,0,50,50,50,50,50,50,50,50,10,10,20,30,30,20,10,10,5,5,10,25,25,10,5,5,0,0,0,20,20,0,0,0,5,-5,-10,0,0,-10,-5,5,5,10,10,-20,-20,10,10,5,0,0,0,0,0,0,0,0],
 n:[-50,-40,-30,-30,-30,-30,-40,-50,-40,-20,0,0,0,0,-20,-40,-30,0,10,15,15,10,0,-30,-30,5,15,20,20,15,5,-30,-30,0,15,20,20,15,0,-30,-30,5,10,15,15,10,5,-30,-40,-20,0,5,5,0,-20,-40,-50,-40,-30,-30,-30,-30,-40,-50],
 b:[-20,-10,-10,-10,-10,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,10,10,5,0,-10,-10,5,5,10,10,5,5,-10,-10,0,10,10,10,10,0,-10,-10,10,10,10,10,10,10,-10,-10,5,0,0,0,0,5,-10,-20,-10,-10,-10,-10,-10,-10,-20],
 r:[0,0,0,0,0,0,0,0,5,10,10,10,10,10,10,5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,0,0,0,5,5,0,0,0],
 q:[-20,-10,-10,-5,-5,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,5,5,5,0,-10,-5,0,5,5,5,5,0,-5,0,0,5,5,5,5,0,-5,-10,5,5,5,5,5,0,-10,-10,0,5,0,0,0,0,-10,-20,-10,-10,-5,-5,-10,-10,-20],
 k:[-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-20,-30,-30,-40,-40,-30,-30,-20,-10,-20,-20,-20,-20,-20,-20,-10,20,20,0,0,0,0,20,20,20,30,10,0,0,10,30,20]};
function evalS(s){let v=0;for(let i=0;i<64;i++){const p=s.b[i];if(!p)continue;const t=p.toLowerCase();if(isW(p))v+=VAL[t]+PST[t][i];else v-=VAL[t]+PST[t][i^56]}return v}
function order(s,ms){return ms.map(m=>{let sc=0;const cap=s.b[m.t];if(cap)sc=10*VAL[cap.toLowerCase()]-VAL[s.b[m.f].toLowerCase()]/10;if(m.pr)sc+=800;if(m.ep)sc=900;return[sc,m]}).sort((a,b)=>b[0]-a[0]).map(x=>x[1])}
let nodes=0;
function ab(s,d,al,be){nodes++;const ms=legal(s);const w=s.turn==='w';
 if(!ms.length)return inCheck(s)?(w?-99999-d:99999+d):0;
 if(s.hm>=100)return 0;
 if(d===0)return evalS(s);
 if(w){let best=-1e9;for(const m of order(s,ms)){const v=ab(make(s,m),d-1,al,be);if(v>best)best=v;if(v>al)al=v;if(al>=be)break}return best}
 else{let best=1e9;for(const m of order(s,ms)){const v=ab(make(s,m),d-1,al,be);if(v<best)best=v;if(v<be)be=v;if(al>=be)break}return best}}
function aiMove(s,depth,noise){const ms=order(s,legal(s));const w=s.turn==='w';let best=null,bv=w?-1e9:1e9;
 for(const m of shuf(ms)){const v=ab(make(s,m),depth-1,-1e9,1e9)+(Math.random()-.5)*noise;if(w?v>bv:v<bv){bv=v;best=m}}return best}
// ===== ARAYÜZ =====
const app=$('#app');const GL={P:'♙',N:'♘',B:'♗',R:'♖',Q:'♕',K:'♔'};const GB={p:'♟',n:'♞',b:'♝',r:'♜',q:'♛',k:'♚'};
const glyph=p=>isW(p)?'♙♘♗♖♕♔'['PNBRQK'.indexOf(p)]:'♟♞♝♜♛♚'['pnbrqk'.indexOf(p)];
let S,human='w',level=1,selSq=-1,lastM=null,over=false,thinking=false,hist=[],capW=[],capB=[],pendingPromo=null;
const LV=[{n:'Çaylak',d:1,z:120},{n:'Orta',d:2,z:30},{n:'Usta',d:3,z:8}];
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'♞ Satranç'),h('div',{class:'msg'},'Yapay zekâya karşı oyna. Rok, en passant ve vezir terfisi dahil tüm kurallar var.'),
 h('div',{class:'row'},LV.map((l,i)=>h('button',{class:'btn',onclick:()=>{level=i;side()}},l.n)))))}
function side(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'Rengini seç'),h('div',{class:'row'},h('button',{class:'btn',onclick:()=>start('w')},'⚪ Beyaz'),h('button',{class:'btn alt',onclick:()=>start('b')},'⚫ Siyah'),h('button',{class:'btn alt',onclick:()=>start(pick(['w','b']))},'🎲 Rastgele'))))}
function start(c){human=c;S=parse(START);selSq=-1;lastM=null;over=false;hist=[];capW=[];capB=[];pendingPromo=null;draw();maybeAI()}
function status(){const ms=legal(S);if(!ms.length){return inCheck(S)?(S.turn==='w'?'Şah mat! Siyah kazandı':'Şah mat! Beyaz kazandı'):'Pat – berabere'}
 if(S.hm>=100)return'50 hamle kuralı – berabere';const pcs=S.b.filter(x=>x&&x.toLowerCase()!=='k');if(!pcs.length)return'Yetersiz materyal – berabere';return inCheck(S)?'Şah!':''}
function draw(){app.innerHTML='';const st=status();const mate=/mat|berabere|Pat/.test(st);if(mate)over=true;
 app.append(h('div',{class:'top'},h('h2',{},'♞ Satranç · '+LV[level].n),h('span',{class:'sp'}),h('span',{class:'chip'},S.turn===human?'Sıra sende':'YZ düşünüyor…'),h('button',{class:'btn alt',onclick:()=>{if(hist.length>=2&&!thinking&&!over)undo()}},'↩ Geri al'),h('button',{class:'btn alt',onclick:menu},'☰ Menü')));
 const size=Math.min(innerHeight-190,innerWidth-30,640),cs=Math.floor(size/8);
 const flip=human==='b';const bd=h('div',{class:'board',style:`width:${cs*8+6}px;font-size:${cs*.78}px`});
 const tg=new Set(),caps=new Set();if(selSq>=0)for(const m of legal(S))if(m.f===selSq){tg.add(m.t);if(S.b[m.t]||m.ep)caps.add(m.t)}
 const ksq=inCheck(S)?kingSq(S.b,S.turn==='w'):-1;
 for(let k=0;k<64;k++){const i=flip?63-k:k,r=i>>3,c=i&7,p=S.b[i];
  let cl='sq '+((r+c)%2?'d':'l');if(i===selSq)cl+=' sel';if(lastM&&(i===lastM.f||i===lastM.t))cl+=' last';if(i===ksq)cl+=' chk';if(caps.has(i))cl+=' cap';
  const e=h('div',{class:cl,style:`height:${cs}px`,'data-sq':i,onclick:()=>click(i)});
  if(p)e.append(h('span',{class:'pc '+(isW(p)?'w':'b')},glyph(p)));if(tg.has(i)&&!caps.has(i))e.append(h('span',{class:'dot'}));bd.append(e)}
 app.append(bd);
 app.append(h('div',{class:'row'},h('span',{class:'chip'},'Aldıkların: '+(human==='w'?capW:capB).map(glyph).join('')),h('span',{class:'chip'},'YZ aldı: '+(human==='w'?capB:capW).map(glyph).join(''))));
 app.append(h('div',{class:'msg '+(mate?'ok':''),id:'ms'},st));
 if(pendingPromo){const o=h('div',{class:'row panel'},'Terfi: ',...['q','r','b','n'].map(x=>h('button',{class:'btn',onclick:()=>{const m={...pendingPromo,pr:x};pendingPromo=null;play(m)}},glyph(human==='w'?x.toUpperCase():x))));app.append(o)}}
function click(i){if(over||thinking||S.turn!==human||pendingPromo)return;const p=S.b[i];
 if(selSq>=0){const ms=legal(S).filter(m=>m.f===selSq&&m.t===i);if(ms.length){if(ms[0].pr){pendingPromo={f:selSq,t:i};selSq=-1;draw();return}play(ms[0]);return}}
 selSq=(p&&isW(p)===(human==='w'))?i:-1;sfx.tap();draw()}
function play(m){hist.push({S,lastM,capW:capW.slice(),capB:capB.slice()});const n=make(S,m);if(n.cap)(S.turn==='w'?capW:capB).push(n.cap);S=n;lastM=m;selSq=-1;n.cap?sfx.bad():sfx.tap();draw();maybeAI()}
function undo(){const k=S.turn===human?2:1;let h2;for(let i=0;i<k&&hist.length;i++)h2=hist.pop();if(h2){S=h2.S;lastM=h2.lastM;capW=h2.capW;capB=h2.capB}over=false;selSq=-1;draw()}
function maybeAI(){if(over||S.turn===human)return;thinking=true;setTimeout(()=>{const L=LV[level];const m=aiMove(S,L.d,L.z);thinking=false;if(m)play(m)},60)}
menu();
</script></body></html>
'''

ARCADE_HTML['kelimeler'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.gridw{display:grid;gap:3px;margin:auto;touch-action:none;user-select:none}
.lc{display:flex;align-items:center;justify-content:center;font-weight:800;border-radius:8px;background:rgba(255,255,255,.08);border:1px solid rgba(94,234,212,.2);cursor:pointer}
.lc.st{background:rgba(251,191,36,.45)}.lc.fd{background:rgba(74,222,128,.45);color:#052e16}
.wl{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;max-width:720px;margin:auto}
.wl span{padding:4px 10px;border-radius:999px;background:rgba(255,255,255,.08);border:1px solid var(--line);font-weight:700;font-size:13px}
.wl span.d{text-decoration:line-through;opacity:.5;background:rgba(74,222,128,.25)}
.cw{display:grid;gap:2px;margin:auto}
.cc{position:relative;background:rgba(255,255,255,.92);color:#042f2e;font-weight:900;display:flex;align-items:center;justify-content:center;border-radius:4px;cursor:pointer}
.cc.blk{background:transparent;cursor:default}
.cc.sel{background:#fde68a}.cc.row{background:#ccfbf1}.cc.bad{background:#fecdd3}.cc.ok{color:#047857}
.cc i{position:absolute;left:2px;top:0;font-size:9px;font-style:normal;font-weight:700;color:#0f766e}
.clues{max-width:760px;margin:auto;display:grid;grid-template-columns:1fr 1fr;gap:6px 18px;font-size:13px;text-align:left}
.clues b{color:var(--gold)}
.clue{cursor:pointer}.clue.a{background:rgba(251,191,36,.25);border-radius:6px}
.pad{display:flex;flex-wrap:wrap;gap:4px;justify-content:center;max-width:640px;margin:auto}
.pad .btn{padding:6px 0;width:38px;font-size:14px;box-shadow:0 2px 0 #0f766e}
.mt{display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:760px;margin:auto;width:100%}
.mt .btn{width:100%;text-align:center;font-size:14px}.mt .btn.sel{outline:3px solid var(--gold)}.mt .btn.done{opacity:.35;pointer-events:none;background:#4ade80}
</style></head><body><div id="app"></div><script>
const app=$('#app');
const TH={
'🔬 Fen Bilimleri':[['HÜCRE','Canlıların yapı taşı'],['MIKNATIS','Demiri çeken cisim'],['GÜNEŞ','Dünya\'ya ışık ve ısı veren yıldız'],['KÜTLE','Maddenin miktarı'],['ENERJİ','İş yapabilme yeteneği'],['ATOM','Maddenin en küçük yapı taşı'],['KUVVET','Cismin hareketini değiştiren etki'],['SÜRTÜNME','Hareketi zorlaştıran kuvvet'],['MERCEK','Işığı kıran saydam cisim'],['VOLKAN','Magmanın yeryüzüne çıktığı dağ'],['DEPREM','Yer kabuğunun sarsılması'],['İKLİM','Uzun yıllık hava olayları'],['MADDE','Kütlesi olan, yer kaplayan her şey'],['DEVRE','Elektriğin dolaştığı yol'],['PİL','Elektrik enerjisi kaynağı']],
'🌍 Sosyal Bilgiler':[['HARİTA','Yeryüzünün küçültülmüş çizimi'],['KITA','Büyük kara parçası'],['OKYANUS','Dünyanın en büyük su kütlesi'],['ATATÜRK','Cumhuriyetimizin kurucusu'],['ANITKABİR','Atatürk\'ün kabri'],['PUSULA','Yön bulmaya yarar'],['ENLEM','Ekvatora paralel hayali çizgi'],['BOYLAM','Kutupları birleştiren hayali çizgi'],['ÖLÇEK','Haritada küçültme oranı'],['ANADOLU','Türkiye\'nin Asya\'daki yarımadası'],['DEMOKRASİ','Halkın yönetimi'],['CUMHURİYET','29 Ekim 1923\'te ilan edildi'],['TARİH','Geçmişi inceleyen bilim'],['KÜLTÜR','Bir toplumun yaşam biçimi'],['ADALET','Hak ve hukuka uygunluk']],
'➗ Matematik':[['KESİR','Bütünün eşit parçaları'],['ÜÇGEN','Üç kenarlı şekil'],['ALAN','Bir yüzeyin kapladığı yer'],['ÇEVRE','Şeklin kenar uzunlukları toplamı'],['PAYDA','Kesirde alttaki sayı'],['ONDALIK','Virgüllü sayı'],['YÜZDE','Yüzde bir birimi (%)'],['SİMETRİ','Ayna yansıması'],['DİKDÖRTGEN','Karşılıklı kenarları eşit dört kenar'],['TOPLAMA','Sayıları birleştirme işlemi'],['ÇARPMA','Tekrarlı toplama'],['BÖLME','Eşit paylaştırma işlemi'],['AÇI','İki ışının birleşimi'],['DOĞRU','İki yana sınırsız uzanan çizgi'],['SAYI','Miktarı gösteren değer']],
'📝 Türkçe':[['SIFAT','İsmi niteleyen sözcük'],['ZAMİR','İsmin yerini tutan sözcük'],['ÖZNE','İşi yapan'],['YÜKLEM','Cümlenin yargı bildiren öğesi'],['FİİL','Eylem bildiren sözcük'],['DEYİM','Kalıplaşmış, mecaz anlamlı söz'],['ATASÖZÜ','Öğüt veren kalıp söz'],['KAFİYE','Uyak'],['METİN','Yazılı anlatım parçası'],['ŞİİR','Dizelerden oluşan edebi tür'],['NOKTA','Cümleyi bitiren işaret'],['VİRGÜL','Sıralamada kullanılan işaret'],['ANLAM','Sözcüğün karşıladığı kavram'],['HİKÂYE','Olay anlatan yazı'],['ROMAN','Uzun kurmaca eser']],
'🇬🇧 İngilizce':[['APPLE','elma'],['SCHOOL','okul'],['FRIEND','arkadaş'],['FAMILY','aile'],['WINDOW','pencere'],['BANANA','muz'],['TEACHER','öğretmen'],['PENCIL','kurşun kalem'],['GARDEN','bahçe'],['SUMMER','yaz'],['MOTHER','anne'],['WINTER','kış'],['ORANGE','portakal / turuncu'],['YELLOW','sarı'],['BOOK','kitap']],
'🏛️ Dünya & Kültür':[['PİRAMİT','Mısır\'ın dev mezar yapıları'],['KAPADOKYA','Peri bacalarıyla ünlü bölge'],['GÖBEKLİTEPE','12 bin yıllık tapınak alanı'],['AYASOFYA','İstanbul\'daki tarihi kubbeli yapı'],['PAMUKKALE','Beyaz travertenleriyle ünlü'],['EFES','İzmir\'deki antik kent'],['EYFEL','Paris\'in demir kulesi'],['KOLEZYUM','Roma\'daki dev amfitiyatro'],['PETRA','Kayalara oyulmuş Ürdün kenti'],['TACMAHAL','Hindistan\'daki beyaz türbe'],['AMAZON','Dünyanın en büyük yağmur ormanı'],['SAHARA','Dünyanın en büyük sıcak çölü'],['EVEREST','Dünyanın en yüksek dağı'],['TUNA','Avrupa\'nın büyük nehri'],['NİL','Afrika\'nın uzun nehri']]};
const TRU=s=>s.toLocaleUpperCase('tr-TR');
const AL_TR='ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ',AL_EN='ABCDEFGHIJKLMNOPQRSTUVWXYZ';
let theme,items,mode;
function menu(){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},'🔤 Kelime Bulmacaları')),h('div',{class:'center'},h('div',{class:'big'},'🔤 Wordwall tarzı kelime oyunları'),h('div',{class:'msg'},'Konu ve oyun türünü seç!'),
 h('div',{class:'row'},Object.keys(TH).map(t=>h('button',{class:'btn alt'+(theme===t?' on':''),style:theme===t?'outline:3px solid var(--gold)':'',onclick:()=>{theme=t;menu()}},t))),
 h('div',{class:'row'},[['search','🔎 Kelime Avı'],['cross','✏️ Çapraz Bulmaca'],['match','🔗 Kelime–Anlam Eşleştirme'],['anag','🔀 Karışık Harfler'],['miss','🔠 Eksik Harf'],['group','🗂️ Grupla (Sınıflandır)']].map(([m,l])=>h('button',{class:'btn',disabled:!theme&&m!=='group',onclick:()=>{mode=m;items=theme?shuf(TH[theme]).map(x=>[TRU(x[0]),x[1]]):[];GM[m]()}},l)))))}
const isEN=()=>theme&&theme.includes('İngilizce');
const alpha=()=>isEN()?AL_EN:AL_TR;
function head(t,extra){return h('div',{class:'top'},h('h2',{},t),h('span',{class:'sp'}),extra||'',h('button',{class:'btn alt',onclick:()=>GM[mode]()},'🔄 Yeni'),h('button',{class:'btn alt',onclick:menu},'☰'))}
function win(msg){sfx.win();window.__won=true;const m=$('#ms');if(m){m.className='msg ok pop';m.textContent=msg}}
// ---------- Kelime Avı
const DIRS=[[0,1],[1,0],[1,1],[0,-1],[-1,0],[-1,-1],[1,-1],[-1,1]];
function buildSearch(words,N,nd){const g=Array.from({length:N},()=>Array(N).fill(''));const placed=[];
 for(const w of words){let ok=false;for(let a=0;a<300&&!ok;a++){const d=pick(DIRS.slice(0,nd));const L=w.length;const r=rnd(0,N-1),c=rnd(0,N-1);const er=r+d[0]*(L-1),ec=c+d[1]*(L-1);if(er<0||er>=N||ec<0||ec>=N)continue;
  let f=true;for(let i=0;i<L;i++){const x=g[r+d[0]*i][c+d[1]*i];if(x&&x!==w[i]){f=false;break}}if(!f)continue;for(let i=0;i<L;i++)g[r+d[0]*i][c+d[1]*i]=w[i];placed.push({w,r,c,d});ok=true}
  if(!ok)return null}
 const al=alpha();for(let r=0;r<N;r++)for(let c=0;c<N;c++)if(!g[r][c])g[r][c]=al[rnd(0,al.length-1)];return{g,placed}}
let SG;
function search(){const N=12;const words=items.slice(0,8).map(x=>x[0]).filter(w=>w.length<=N);let res=null;for(let i=0;i<30&&!res;i++)res=buildSearch(words,N,5);SG={...res,N,found:new Set(),first:null,cells:new Set(),words};drawSearch()}
function drawSearch(){app.innerHTML='';app.append(head('🔎 Kelime Avı · '+theme,h('span',{class:'chip',id:'cnt'},SG.found.size+'/'+SG.words.length)));
 const cs=Math.floor(Math.min(innerHeight-250,innerWidth-30,520)/SG.N);const g=h('div',{class:'gridw',style:`grid-template-columns:repeat(${SG.N},${cs}px);font-size:${cs*.5}px`});
 for(let r=0;r<SG.N;r++)for(let c=0;c<SG.N;c++){const k=r*SG.N+c;g.append(h('div',{class:'lc'+(SG.cells.has(k)?' fd':'')+(SG.first===k?' st':''),'data-k':k,style:`height:${cs}px`,onclick:()=>tapS(r,c)},SG.g[r][c]))}
 app.append(g,h('div',{class:'wl'},SG.words.map(w=>h('span',{class:SG.found.has(w)?'d':''},w))),h('div',{class:'msg',id:'ms'},'Kelimenin ilk ve son harfine dokun.'))}
function tapS(r,c){const k=r*SG.N+c;if(SG.first===null){SG.first=k;sfx.tap();drawSearch();return}
 const r0=Math.floor(SG.first/SG.N),c0=SG.first%SG.N;SG.first=null;const dr=Math.sign(r-r0),dc=Math.sign(c-c0),L=Math.max(Math.abs(r-r0),Math.abs(c-c0))+1;
 if(!(r===r0||c===c0||Math.abs(r-r0)===Math.abs(c-c0))){drawSearch();return}
 let s='';const ks=[];for(let i=0;i<L;i++){s+=SG.g[r0+dr*i][c0+dc*i];ks.push((r0+dr*i)*SG.N+c0+dc*i)}
 const rev=[...s].reverse().join('');const w=SG.words.find(x=>(x===s||x===rev)&&!SG.found.has(x));
 if(w){SG.found.add(w);ks.forEach(x=>SG.cells.add(x));sfx.ok()}else sfx.bad();drawSearch();if(w&&SG.found.size===SG.words.length)win('🎉 Hepsini buldun!')}
// ---------- Çapraz Bulmaca
let CW;
function buildCross(words){const S=19;const g=Array.from({length:S},()=>Array(S).fill(''));const pl=[];
 const can=(w,r,c,h2)=>{const dr=h2?0:1,dc=h2?1:0;if(r<0||c<0||r+dr*(w.length-1)>=S||c+dc*(w.length-1)>=S)return false;
  const pr=r-dr,pc=c-dc;if(pr>=0&&pc>=0&&g[pr][pc])return false;const nr=r+dr*w.length,nc=c+dc*w.length;if(nr<S&&nc<S&&g[nr][nc])return false;let cross=0;
  for(let i=0;i<w.length;i++){const rr=r+dr*i,cc=c+dc*i,x=g[rr][cc];if(x){if(x!==w[i])return false;cross++}else{if(h2){if((rr>0&&g[rr-1][cc])||(rr<S-1&&g[rr+1][cc]))return false}else{if((cc>0&&g[rr][cc-1])||(cc<S-1&&g[rr][cc+1]))return false}}}return cross}
 const put=(w,r,c,h2)=>{const dr=h2?0:1,dc=h2?1:0;for(let i=0;i<w.length;i++)g[r+dr*i][c+dc*i]=w[i];pl.push({w,r,c,h:h2})};
 const ws=words.slice().sort((a,b)=>b[0].length-a[0].length);const f=ws.shift();put(f[0],9,Math.floor((S-f[0].length)/2),true);pl[0].clue=f[1];
 for(let round=0;round<3;round++)for(let i=0;i<ws.length;i++){const[w,cl]=ws[i];if(pl.some(p=>p.w===w))continue;let best=null;
  for(const p of pl){for(let a=0;a<w.length;a++)for(let b=0;b<p.w.length;b++){if(w[a]!==p.w[b])continue;const h2=!p.h;const r=h2?p.r+(p.h?b:0)*0+(p.h?0:b):p.r-a,c=h2?p.c-a:p.c+b;
    const rr=h2?p.r+b:p.r-a,cc=h2?p.c-a:p.c+b;const R=h2?(p.h?p.r:p.r+b):rr,C=h2?(p.h?p.c-a:p.c-a):cc;
    const rs=h2?p.r+b:p.r-a,cs2=h2?p.c-a:p.c+b;if(can(w,rs,cs2,h2)){best={w,cl,r:rs,c:cs2,h:h2};break}}if(best)break}
  if(best){put(best.w,best.r,best.c,best.h);pl[pl.length-1].clue=cl}}
 return{g,pl}}
function cross(){let res;for(let i=0;i<25;i++){res=buildCross(items.slice(0,12));if(res.pl.length>=7)break;items=shuf(items)}
 let r0=99,r1=0,c0=99,c1=0;res.pl.forEach(p=>{r0=Math.min(r0,p.r);c0=Math.min(c0,p.c);r1=Math.max(r1,p.r+(p.h?0:p.w.length-1));c1=Math.max(c1,p.c+(p.h?p.w.length-1:0))});
 const H=r1-r0+1,W=c1-c0+1;const ans=Array.from({length:H},()=>Array(W).fill(''));const num=Array.from({length:H},()=>Array(W).fill(0));
 res.pl.forEach(p=>{p.r-=r0;p.c-=c0;for(let i=0;i<p.w.length;i++)ans[p.r+(p.h?0:i)][p.c+(p.h?i:0)]=p.w[i]});
 let n=0;const order=res.pl.slice().sort((a,b)=>a.r-b.r||a.c-b.c);order.forEach(p=>{if(!num[p.r][p.c])num[p.r][p.c]=++n;p.n=num[p.r][p.c]});
 CW={H,W,ans,num,pl:res.pl,inp:Array.from({length:H},()=>Array(W).fill('')),sel:null,dir:true,bad:new Set()};drawCross()}
function curWord(){if(!CW.sel)return null;const[r,c]=CW.sel;return CW.pl.find(p=>p.h===CW.dir&&((p.h&&p.r===r&&c>=p.c&&c<p.c+p.w.length)||(!p.h&&p.c===c&&r>=p.r&&r<p.r+p.w.length)))||CW.pl.find(p=>((p.h&&p.r===r&&c>=p.c&&c<p.c+p.w.length)||(!p.h&&p.c===c&&r>=p.r&&r<p.r+p.w.length)))}
function drawCross(){app.innerHTML='';const cw=curWord();app.append(head('✏️ Çapraz Bulmaca · '+theme));
 const cs=Math.floor(Math.min((innerHeight-330),innerWidth-30,560)/Math.max(CW.H,CW.W));const g=h('div',{class:'cw',style:`grid-template-columns:repeat(${CW.W},${cs}px);font-size:${cs*.55}px`});
 for(let r=0;r<CW.H;r++)for(let c=0;c<CW.W;c++){if(!CW.ans[r][c]){g.append(h('div',{class:'cc blk',style:`height:${cs}px`}));continue}
  const inW=cw&&((cw.h&&cw.r===r&&c>=cw.c&&c<cw.c+cw.w.length)||(!cw.h&&cw.c===c&&r>=cw.r&&r<cw.r+cw.w.length));const sel=CW.sel&&CW.sel[0]===r&&CW.sel[1]===c;
  g.append(h('div',{class:'cc'+(sel?' sel':inW?' row':'')+(CW.bad.has(r*99+c)?' bad':''),'data-r':r,'data-c':c,style:`height:${cs}px`,onclick:()=>{if(CW.sel&&CW.sel[0]===r&&CW.sel[1]===c)CW.dir=!CW.dir;CW.sel=[r,c];drawCross()}},CW.num[r][c]?h('i',{},CW.num[r][c]):'',CW.inp[r][c]))}
 app.append(g);
 const clue=(h2)=>CW.pl.filter(p=>p.h===h2).sort((a,b)=>a.n-b.n).map(p=>h('div',{class:'clue'+(cw===p?' a':''),onclick:()=>{CW.sel=[p.r,p.c];CW.dir=p.h;drawCross()}},h('b',{},p.n+'.'),' '+p.clue+' ('+p.w.length+')'));
 app.append(h('div',{class:'clues'},h('div',{},h('b',{},'→ Soldan sağa'),clue(true)),h('div',{},h('b',{},'↓ Yukarıdan aşağı'),clue(false))));
 const pad=h('div',{class:'pad'});[...alpha()].forEach(ch=>pad.append(h('button',{class:'btn',onclick:()=>typeL(ch)},ch)));pad.append(h('button',{class:'btn alt',onclick:()=>typeL('')},'⌫'));
 app.append(pad,h('div',{class:'row'},h('button',{class:'btn',onclick:checkC},'✓ Kontrol'),h('button',{class:'btn alt',onclick:hintC},'💡 Harf ipucu')),h('div',{class:'msg',id:'ms'},''))}
function typeL(ch){if(!CW.sel)return;const[r,c]=CW.sel;CW.inp[r][c]=ch;CW.bad.delete(r*99+c);sfx.tap();if(ch){const nr=CW.dir?r:r+1,nc=CW.dir?c+1:c;if(CW.ans[nr]&&CW.ans[nr][nc])CW.sel=[nr,nc]}drawCross();if(solvedC())win('🎉 Bulmacayı çözdün!')}
function solvedC(){for(let r=0;r<CW.H;r++)for(let c=0;c<CW.W;c++)if(CW.ans[r][c]&&CW.inp[r][c]!==CW.ans[r][c])return false;return true}
function checkC(){CW.bad=new Set();let ok=true;for(let r=0;r<CW.H;r++)for(let c=0;c<CW.W;c++){if(CW.ans[r][c]&&CW.inp[r][c]&&CW.inp[r][c]!==CW.ans[r][c]){CW.bad.add(r*99+c);ok=false}}drawCross();$('#ms').textContent=CW.bad.size?'Kırmızı kutular yanlış.':'Şimdilik hatasız!';CW.bad.size?sfx.bad():sfx.ok()}
function hintC(){const w=curWord();if(!w)return;for(let i=0;i<w.w.length;i++){const r=w.r+(w.h?0:i),c=w.c+(w.h?i:0);if(CW.inp[r][c]!==CW.ans[r][c]){CW.inp[r][c]=CW.ans[r][c];break}}drawCross();if(solvedC())win('🎉 Bulmacayı çözdün!')}
// ---------- Eşleştirme
function match(){const it=items.slice(0,7);const L=shuf(it.map((x,i)=>({i,t:x[0]})));const R=shuf(it.map((x,i)=>({i,t:x[1]})));let selL=null,done=0,mist=0;
 function draw(){app.innerHTML='';app.append(head('🔗 Kelime–Anlam · '+theme,h('span',{class:'chip'},'❌ '+mist)));
  app.append(h('div',{class:'mt'},h('div',{class:'center',style:'gap:8px'},L.map(x=>h('button',{class:'btn'+(selL===x?' sel':'')+(x.d?' done':''),onclick:()=>{selL=x;sfx.tap();draw()}},x.t))),
   h('div',{class:'center',style:'gap:8px'},R.map(x=>h('button',{class:'btn alt'+(x.d?' done':''),onclick:()=>{if(!selL)return;if(selL.i===x.i){selL.d=x.d=true;done++;sfx.ok();selL=null;draw();if(done===it.length)win('🎉 Hepsini eşleştirdin!')}else{mist++;sfx.bad();selL=null;draw()}}},x.t)))),h('div',{class:'msg',id:'ms'},'Önce kelimeyi, sonra anlamını seç.'))}
 draw()}
// ---------- Karışık harfler
function anag(){let i=0,pts=0;function nx(){if(i>=Math.min(8,items.length)){app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🎉 Tamamlandı!'),h('div',{class:'msg'},'Puan: '+pts),h('button',{class:'btn',onclick:anag},'Tekrar')));window.__won=true;return}
  const[w,cl]=items[i];let sh;do{sh=shuf([...w])}while(sh.join('')===w&&w.length>2);let g=[],used=[];
  function draw(){app.innerHTML='';app.append(head('🔀 Karışık Harfler',h('span',{class:'chip'},'Puan '+pts)));app.append(h('div',{class:'center'},h('div',{class:'msg'},'💡 '+cl+' ('+w.length+' harf)'),h('div',{class:'big',style:'letter-spacing:6px'},g.join('')||'…'),
   h('div',{class:'row'},sh.map((ch,k)=>h('button',{class:'btn',disabled:used.includes(k),onclick:()=>{g.push(ch);used.push(k);sfx.tap();if(g.length===w.length){if(g.join('')===w){pts+=10;sfx.ok();i++;setTimeout(nx,500)}else{sfx.bad();g=[];used=[];draw()}}else draw()}},ch))),
   h('div',{class:'row'},h('button',{class:'btn alt',onclick:()=>{g=[];used=[];draw()}},'Temizle'),h('button',{class:'btn alt',onclick:()=>{i++;nx()}},'Geç'))))}
  draw()}nx()}

// ---------- Eksik Harf
function miss(){let i=0,pts=0;const N=Math.min(8,items.length);function nx(){if(i>=N){app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🎉 Tamamlandı!'),h('div',{class:'msg'},'Puan: '+pts+' / '+N*10),h('button',{class:'btn',onclick:()=>{items=shuf(items);miss()}},'Tekrar')));window.__won=true;return}
  const[w,cl]=items[i];const k=w.length<=5?1:2;const hole=shuf([...w].map((_,q)=>q)).slice(0,k).sort((a,b)=>a-b);let fill=[];
  function draw(){app.innerHTML='';app.append(head('🔠 Eksik Harf · '+theme,h('span',{class:'chip'},(i+1)+'/'+N+' · Puan '+pts)));
   const shown=[...w].map((ch,p)=>hole.includes(p)?(fill[hole.indexOf(p)]||'_'):ch).join(' ');
   const pad=h('div',{class:'pad'});[...alpha()].forEach(ch=>pad.append(h('button',{class:'btn',onclick:()=>{if(fill.length>=k)return;fill.push(ch);sfx.tap();if(fill.length===k){const ok=hole.every((p,j)=>fill[j]===w[p]);if(ok){pts+=10;sfx.ok();i++;draw();setTimeout(nx,600);return}sfx.bad();fill=[]}draw()}},ch)));
   app.append(h('div',{class:'center'},h('div',{class:'msg'},'💡 '+cl),h('div',{class:'big',style:'letter-spacing:4px'},shown),pad,h('div',{class:'row'},h('button',{class:'btn alt',onclick:()=>{fill=[];draw()}},'Temizle'),h('button',{class:'btn alt',onclick:()=>{i++;nx()}},'Geç')),h('div',{class:'msg',id:'ms'},'')))}
  draw()}nx()}
// ---------- Grupla (sınıflandırma)
const GROUPS=[
{t:'Canlı mı, cansız mı?',a:'🌱 Canlı',b:'🪨 Cansız',i:[['Kedi','a'],['Ağaç','a'],['Papatya','a'],['Balık','a'],['Mantar','a'],['Kaya','b'],['Su','b'],['Masa','b'],['Güneş','b'],['Kum','b']]},
{t:'Katı mı, sıvı mı?',a:'🧊 Katı',b:'💧 Sıvı',i:[['Buz','a'],['Taş','a'],['Odun','a'],['Demir','a'],['Tebeşir','a'],['Süt','b'],['Su','b'],['Zeytinyağı','b'],['Meyve suyu','b'],['Bal','b']]},
{t:'Tek mi, çift mi?',a:'1️⃣ Tek sayı',b:'2️⃣ Çift sayı',i:[['7','a'],['25','a'],['41','a'],['9','a'],['63','a'],['12','b'],['18','b'],['30','b'],['64','b'],['100','b']]},
{t:'Asal mı, değil mi?',a:'⭐ Asal',b:'❌ Asal değil',i:[['2','a'],['3','a'],['5','a'],['7','a'],['11','a'],['13','a'],['4','b'],['6','b'],['9','b'],['12','b'],['15','b']]},
{t:'Hangi ülkede?',a:'🇹🇷 Türkiye',b:'🌍 Başka ülke',i:[['Kapadokya','a'],['Pamukkale','a'],['Efes','a'],['Ayasofya','a'],['Göbeklitepe','a'],['Eyfel Kulesi','b'],['Kolezyum','b'],['Piramitler','b'],['Tac Mahal','b'],['Özgürlük Heykeli','b']]},
{t:'İsim mi, fiil mi?',a:'📦 İsim',b:'🏃 Fiil',i:[['kalem','a'],['deniz','a'],['okul','a'],['çiçek','a'],['masa','a'],['koşmak','b'],['yazmak','b'],['okumak','b'],['gülmek','b'],['yüzmek','b']]},
{t:'Enerji kaynağı',a:'♻️ Yenilenebilir',b:'🛢️ Yenilenemez',i:[['Güneş','a'],['Rüzgâr','a'],['Akarsu','a'],['Jeotermal','a'],['Kömür','b'],['Petrol','b'],['Doğalgaz','b'],['Taş kömürü','b']]},
{t:'Yaşam alanı',a:'🦁 Karada yaşar',b:'🐬 Suda yaşar',i:[['Aslan','a'],['Kedi','a'],['Tavşan','a'],['Fil','a'],['Zürafa','a'],['Balık','b'],['Yunus','b'],['Ahtapot','b'],['Köpekbalığı','b'],['Denizanası','b']]}];
function group(){const G=pick(GROUPS);const q=shuf(G.i);let i=0,ok=0,bad=0;
 function draw(){app.innerHTML='';app.append(head('🗂️ Grupla · '+G.t,h('span',{class:'chip'},'✅ '+ok+'  ❌ '+bad)));
  if(i>=q.length){const sc=Math.round(100*ok/q.length);app.append(h('div',{class:'center pop'},h('div',{class:'big'},sc>=80?'🏆 Harika!':'👍 İyi iş!'),h('div',{class:'msg'},ok+' / '+q.length+' doğru'),h('div',{class:'row'},h('button',{class:'btn',onclick:group},'Başka set'))));window.__won=true;sfx.win();return}
  app.append(h('div',{class:'center'},h('div',{class:'msg'},(i+1)+' / '+q.length+' — Bu hangisine ait?'),h('div',{class:'cardx pop',style:'width:min(90%,420px);border-radius:24px;border:3px solid var(--ac);padding:26px;font-size:clamp(26px,6vw,44px);font-weight:900;background:rgba(255,255,255,.07)'},q[i][0]),
   h('div',{class:'row'},[['a',G.a],['b',G.b]].map(([k,l])=>h('button',{class:'btn',style:'min-width:150px;font-size:18px',onclick:()=>{if(q[i][1]===k){ok++;sfx.ok()}else{bad++;sfx.bad()}i++;draw()}},l))),h('div',{class:'msg',id:'ms'},'')))}
 draw()}
const GM={search,cross,match,anag,miss,group};
menu();
</script></body></html>
'''

ARCADE_HTML['macera'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.story{width:min(96%,720px);margin:auto;border-radius:26px;border:3px solid var(--ac);background:linear-gradient(160deg,#0b4a55,#052a31);padding:20px;box-shadow:0 14px 40px rgba(0,0,0,.4)}
.story .em{font-size:64px;text-align:center}.story p{font-size:clamp(16px,2.6vw,20px);line-height:1.55;margin:10px 0}
.opt{display:block;width:100%;text-align:left;margin:8px 0;padding:12px 16px;border-radius:16px;border:2px solid var(--line);background:rgba(255,255,255,.08);color:var(--t);font-size:16px;font-weight:700;cursor:pointer;font-family:inherit}
.opt:hover{background:rgba(45,212,191,.25);border-color:var(--ac)}.opt.good{background:rgba(74,222,128,.35)}.opt.bad{background:rgba(251,113,133,.35)}
.learn{margin-top:10px;padding:10px 12px;border-radius:14px;background:rgba(251,191,36,.15);border:1px solid rgba(251,191,36,.5);font-size:14px}
.stats{display:flex;gap:8px}.cardA{width:230px;padding:16px;border-radius:22px;background:rgba(255,255,255,.07);border:2px solid var(--line);cursor:pointer;text-align:center}
.cardA:hover{border-color:var(--ac)}.cardA b{display:block;margin:6px 0 4px;font-size:18px}.cardA span{font-size:13px;color:var(--mut)}
</style></head><body><div id="app"></div><script>
const app=$('#app');
const ADV={
kapadokya:{t:'Kapadokya: Kayıp Balon Haritası',e:'🎈',d:'Peri bacaları arasında saklı bir haritayı bulmak için sabah balonuyla yola çık!',s:'a1',n:{
 a1:{e:'🌄',t:'Sabahın ilk ışıklarında Göreme\'desin. Rehberin Elif, eski bir haritanın peri bacalarından birinde saklı olduğunu söylüyor. Önce nereye gidersin?',c:[{t:'🎈 Balona binip yukarıdan bakarım',to:'a2'},{t:'🚶 Vadide yürüyerek incelerim',to:'a3'}]},
 a2:{e:'🎈',t:'Balon yükselirken aşağıda koni şeklinde kayalar görüyorsun. Elif soruyor:',q:{s:'Peri bacaları nasıl oluştu?',o:['Volkanik tüfün yağmur ve rüzgârla aşınmasıyla','İnsanlar tarafından inşa edilerek','Denizin çekilmesiyle'],a:0,ok:'a4',no:'a4',learn:'Peri bacaları, volkanlardan çıkan yumuşak tüf tabakasının yağmur ve rüzgârla yüzyıllarca aşınmasıyla oluştu.'}},
 a3:{e:'🥾',t:'Vadide yürürken yerde bir delik buluyorsun: bir yeraltı şehrinin girişi! Elif "Dikkatli ol, burası çok derin" diyor.',c:[{t:'🔦 Fener alıp içeri inerim',to:'a5'},{t:'📸 Önce fotoğraf çekip haritaya bakarım',to:'a4',fx:{bilgi:1}}]},
 a4:{e:'🗺️',t:'Haritanın bir köşesini rüzgâr getirmiş! Üzerinde yazıyor: "Gerçek hazine, merak edenlerindir. Yeraltının kapısını Derinkuyu\'da ara."',c:[{t:'⬇️ Derinkuyu\'ya git',to:'a5'}]},
 a5:{e:'🕯️',t:'Yeraltı şehrinin dar koridorlarındasın. Duvarda havalandırma bacaları ve devasa yuvarlak taş kapılar var. Elif sorar:',q:{s:'Yeraltı şehirleri en çok ne amaçla kullanılmış?',o:['Saldırılardan korunmak ve saklanmak','Gökyüzünü gözlemlemek','Balık tutmak'],a:0,ok:'a6',no:'a6',learn:'Kapadokya\'daki yeraltı şehirleri (Derinkuyu, Kaymaklı) insanların saldırılardan korunmak için sığındığı çok katlı yerleşimlerdir.'}},
 a6:{e:'🚪',t:'Önünde iki yol var: sol koridor serin ve sessiz, sağ koridorda ışık sızıyor.',c:[{t:'⬅️ Sessiz koridor',to:'a7',fx:{enerji:-1}},{t:'➡️ Işıklı koridor',to:'a8',fx:{hazine:1}}]},
 a7:{e:'😮‍💨',t:'Koridor çıkmaz çıktı, geri dönmek seni yordu. Ama duvarda eski bir kabartma var: bir haritanın parçası!',c:[{t:'🧩 Parçayı al ve geri dön',to:'a9',fx:{hazine:1}}]},
 a8:{e:'💡',t:'Işık, tavandaki havalandırma bacasından geliyormuş. Yanında bir sandık var!',c:[{t:'📦 Sandığı aç',to:'a9'}]},
 a9:{e:'🔑',t:'Sandıkta harita parçası ve bir bilmece var: "Ben Kapadokya\'nın başkenti sayılırım, kayalara oyulmuş kiliselerim var. Müze olarak gezilirim. Neyim?"',q:{s:'Bilmecenin cevabı hangisi?',o:['Göreme Açık Hava Müzesi','Anıtkabir','Ayasofya'],a:0,ok:'a10',no:'a10',learn:'Göreme Açık Hava Müzesi, kayalara oyulmuş kiliseleri ve freskleriyle UNESCO Dünya Mirası Listesi\'ndedir (1985).'}},
 a10:{e:'🏆',end:'win',t:'Haritanın tüm parçalarını birleştirdin! Hazine; Kapadokya\'nın tarihini ve doğasını koruma sözü. Elif seni "Kapadokya Kâşifi" ilan ediyor.'},
 a11:{e:'💤',end:'lose',t:'Çok yoruldun ve enerjin bitti. Elif seni dinlenmeye götürüyor. Yarın yeniden dene!'}}},
gobekli:{t:'Göbeklitepe: Zamanın Sırrı',e:'🗿',d:'12 bin yıl öncesine yolculuk: T biçimli sütunların sırrını çöz!',s:'g1',n:{
 g1:{e:'🏜️',t:'Şanlıurfa\'da, Göbeklitepe kazı alanındasın. Arkeolog Zeynep elinde bir fırça ile sana bakıyor: "Burada yeryüzünün bilinen en eski anıtsal yapılarından biri var."',c:[{t:'🔍 Sütunları yakından incelerim',to:'g2'},{t:'📖 Önce kazı rehberini okurum',to:'g3',fx:{bilgi:1}}]},
 g2:{e:'🗿',t:'Dev sütunlar T harfine benziyor ve üzerlerinde hayvan kabartmaları var: tilki, yılan, akbaba...',q:{s:'Göbeklitepe yaklaşık kaç yıl öncesine aittir?',o:['Yaklaşık 12.000 yıl','Yaklaşık 2.000 yıl','Yaklaşık 500 yıl'],a:0,ok:'g4',no:'g4',learn:'Göbeklitepe yaklaşık 12.000 yıllıktır; Stonehenge ve piramitlerden çok daha eskidir.'}},
 g3:{e:'📘',t:'Rehberde şöyle yazıyor: "Burada yaşayan topluluklar henüz tarım yapmıyor, avcı-toplayıcıydı." Zeynep gülümsüyor: "Peki, bunu nasıl anlıyoruz?"',c:[{t:'🦴 Hayvan kemiklerinden',to:'g4',fx:{bilgi:1}},{t:'📜 Yazılı belgelerden',to:'g4'}]},
 g4:{e:'⛏️',t:'Zeynep sana bir kazı alanı verip "Haydi, ilk ipucunu bul!" diyor. İki bölge var.',c:[{t:'🧱 Daire biçimli yapının içi',to:'g5',fx:{hazine:1}},{t:'🌿 Tepenin çevresi',to:'g6',fx:{enerji:-1}}]},
 g5:{e:'🪨',t:'Dairenin ortasında iki büyük sütun duruyor. Zeynep: "Bunları kim dikti? O dönemde metal alet yoktu!"',q:{s:'O dönemde sütunlar hangi aletle işlenmiş olabilir?',o:['Çakmaktaşı gibi taş aletlerle','Elektrikli testereyle','Demir çekiçle'],a:0,ok:'g7',no:'g7',learn:'Göbeklitepe yapıcıları metal kullanmıyordu; sütunları çakmaktaşı gibi taş aletlerle yontuyorlardı.'}},
 g6:{e:'🥵',t:'Güneş çok sıcak; susadın. Yine de çevrede küçük taş aletler buldun!',c:[{t:'🧰 Aletleri Zeynep\'e götür',to:'g7',fx:{bilgi:1}}]},
 g7:{e:'🌍',t:'Zeynep, 2018\'de Göbeklitepe\'nin UNESCO Dünya Mirası Listesi\'ne alındığını anlatıyor. "Bu keşif insanlık tarihini yeniden yazdırdı. Çünkü..."',q:{s:'Göbeklitepe neden tarih kitaplarını değiştirdi?',o:['Tarım ve yerleşik hayattan önce de anıtsal yapılar yapıldığını gösterdi','Piramitlerden daha yüksek olduğu için','Bir şehir surunun kalıntısı olduğu için'],a:0,ok:'g8',no:'g8',learn:'Göbeklitepe, insanların yerleşik hayata ve tarıma geçmeden önce de büyük ortak yapılar inşa edebildiğini gösterdi.'}},
 g8:{e:'🏆',end:'win',t:'Zeynep sana "Genç Arkeolog" rozetini takıyor. Göbeklitepe\'nin sırrını çözmen insanlık tarihine ışık tuttu!'},
 g9:{e:'💤',end:'lose',t:'Enerjin bitti. Ekip seni gölgeye alıyor. Dinlenip tekrar deneyebilirsin!'}}},
uzay:{t:'Uzay İstasyonu: Acil Durum!',e:'🚀',d:'Güneş sisteminde yolunu bul, istasyonu kurtar!',s:'u1',n:{
 u1:{e:'🛰️',t:'Uluslararası uzay istasyonunda alarm çalıyor! Kaptan Ayşe: "Güneş fırtınası yaklaşıyor. Enerji panellerini yönlendirmeli ve Dünya\'ya haber vermeliyiz."',c:[{t:'☀️ Önce panelleri Güneş\'e çeviririm',to:'u2'},{t:'📡 Önce Dünya\'ya mesaj gönderirim',to:'u3'}]},
 u2:{e:'🔆',t:'Paneller dönerken Ayşe soruyor:',q:{s:'Işık Güneş\'ten Dünya\'ya yaklaşık kaç dakikada gelir?',o:['Yaklaşık 8 dakika','Yaklaşık 8 saniye','Yaklaşık 8 saat'],a:0,ok:'u4',no:'u4',learn:'Güneş ışığı Dünya\'ya yaklaşık 8 dakikada ulaşır.'}},
 u3:{e:'📡',t:'Mesaj gönderildi. Cevap beklerken Ayşe\'nin yüzü asılıyor: "Sinyal gecikmeli geliyor, o yüzden panelleri de çevirmeliyiz."',c:[{t:'☀️ Panelleri çevir',to:'u2',fx:{bilgi:1}}]},
 u4:{e:'🪐',t:'Fırtına geçti ama yönlendirme bilgisayarı bozuldu. Haritayı elle okumalısın. Önünde gezegenler var.',q:{s:'Güneş\'e en yakın gezegen hangisidir?',o:['Merkür','Venüs','Mars'],a:0,ok:'u5',no:'u5',learn:'Güneş\'e en yakın gezegen Merkür\'dür.'}},
 u5:{e:'🔴',t:'Bir sonraki görev Mars\'a veri göndermek. Mars neden kırmızı görünüyor?',q:{s:'Mars\'ın kırmızı renginin sebebi nedir?',o:['Yüzeyindeki demir oksit (pas)','Üzerindeki yanardağ lavları','Atmosferindeki kırmızı gaz'],a:0,ok:'u6',no:'u6',learn:'Mars\'ın yüzeyi demir oksit (pas) içerdiği için kırmızı görünür.'}},
 u6:{e:'🪐',t:'İstasyonun yakıtı azalıyor. İki seçeneğin var:',c:[{t:'♻️ Gereksiz cihazları kapatıp enerji tasarrufu yaparım',to:'u7',fx:{bilgi:1}},{t:'🚀 Tam güçle hızlı dönerim',to:'u7',fx:{enerji:-1}}]},
 u7:{e:'🌍',t:'Dünya\'ya yaklaşırken Ay\'ı da görüyorsun.',q:{s:'Ay, Dünya\'nın nesi sayılır?',o:['Doğal uydusu','Komşu gezegeni','Yıldızı'],a:0,ok:'u8',no:'u8',learn:'Ay, Dünya\'nın tek doğal uydusudur.'}},
 u8:{e:'🏆',end:'win',t:'İstasyon kurtuldu! Dünya\'daki merkez seni "Uzay Kahramanı" ilan ediyor.'},
 u9:{e:'💤',end:'lose',t:'Enerjin tükendi, istasyon otomatik pilota geçti. Bir dahaki sefere daha dikkatli ol!'}}},
su:{t:'Su Damlası Yolculuğu',e:'💧',d:'Bir su damlası olarak su döngüsünü baştan sona yaşa!',s:'s1',n:{
 s1:{e:'🌊',t:'Sen denizde yüzen küçük bir su damlasısın. Güneş ısınıyor ve içinde tuhaf bir hafiflik hissediyorsun.',q:{s:'Su damlası ısınıp gaz hâline geçerse bu olaya ne denir?',o:['Buharlaşma','Yoğuşma','Donma'],a:0,ok:'s2',no:'s2',learn:'Sıvı suyun ısınarak gaz (su buharı) hâline geçmesine buharlaşma denir.'}},
 s2:{e:'☁️',t:'Su buharı olarak yükseliyorsun. Yukarısı soğuk! Yanındaki damlalar bir araya toplanıp bulut oluşturuyor.',q:{s:'Su buharının soğuyarak sıvı damlacıklara dönüşmesine ne denir?',o:['Yoğuşma','Erime','Kaynama'],a:0,ok:'s3',no:'s3',learn:'Gazın soğuyarak sıvıya dönüşmesine yoğuşma denir; bulutlar böyle oluşur.'}},
 s3:{e:'🌬️',t:'Rüzgâr bulutu dağlara doğru itiyor. İki yol görüyorsun:',c:[{t:'⛰️ Yüksek dağın üstüne gideyim',to:'s4',fx:{bilgi:1}},{t:'🌾 Ovanın üstünde kalayım',to:'s4'}]},
 s4:{e:'🌧️',t:'Bulut ağırlaştı ve damlalar yağmur olarak düşmeye başladı! Çok yüksek ve soğuk bir yerde olsaydın başka bir hâlde düşebilirdin.',q:{s:'Çok soğuk havada yağış hangi hâlde yağabilir?',o:['Kar veya dolu','Sis','Çiy'],a:0,ok:'s5',no:'s5',learn:'Hava çok soğuksa su kar veya dolu olarak yeryüzüne düşer; bunların hepsi yağıştır.'}},
 s5:{e:'🏞️',t:'Bir dere yatağına düştün. Akıntı seni nehre, nehir de tekrar denize götürüyor. Yolda bir çiftçi seni tarlasını sulamak için kullanmak istiyor.',c:[{t:'🌱 Tarlaya karış, bitkiye yardım et',to:'s6',fx:{hazine:1}},{t:'🌊 Akıntıyla denize devam et',to:'s6'}]},
 s6:{e:'🔁',t:'Döngü tamamlanmak üzere. Son soru:',q:{s:'Dünya\'daki suyun büyük kısmı nerededir?',o:['Okyanus ve denizlerde','Nehirlerde','Bulutlarda'],a:0,ok:'s7',no:'s7',learn:'Dünya\'daki suyun yaklaşık %97\'si okyanus ve denizlerdedir; tatlı su çok daha azdır.'}},
 s7:{e:'🏆',end:'win',t:'Su döngüsünü tamamladın! Buharlaşma, yoğuşma ve yağışı birebir yaşadın. Suyu tasarruflu kullanmayı da unutma!'},
 s8:{e:'💤',end:'lose',t:'Çok yoruldun ve bir göle sıkıştın. Yeniden dene, döngü seni bekliyor!'}}},
cumhuriyet:{t:'Cumhuriyet Yolu: Tarih Dedektifi',e:'🇹🇷',d:'Zaman makinesiyle Cumhuriyet\'in kuruluş günlerini keşfet!',s:'c1',n:{
 c1:{e:'⏳',t:'Zaman makinen seni Ankara\'ya, 1920\'lere getirdi. Genç bir öğretmen olan Selim sana yardım edecek: "Burada tarih yazılıyor, ipuçlarını birleştirelim!"',c:[{t:'🏛️ Meclis binasına git',to:'c2'},{t:'📰 Gazete bayisine uğra',to:'c3',fx:{bilgi:1}}]},
 c2:{e:'🏛️',t:'Büyük Millet Meclisi\'nin önündesin. Selim anlatıyor:',q:{s:'TBMM hangi tarihte açıldı?',o:['23 Nisan 1920','29 Ekim 1923','30 Ağustos 1922'],a:0,ok:'c4',no:'c4',learn:'Türkiye Büyük Millet Meclisi 23 Nisan 1920\'de Ankara\'da açıldı; bu tarih Ulusal Egemenlik ve Çocuk Bayramı olarak kutlanır.'}},
 c3:{e:'📰',t:'Gazetede kalın harflerle şu yazıyor: "Millet iradesi egemenlik demektir." Selim gülümsüyor: "Haydi, Meclis\'e gidelim."',c:[{t:'🏛️ Meclis binasına git',to:'c2'}]},
 c4:{e:'🪖',t:'Selim seni bir müzeye götürüyor ve Kurtuluş Savaşı\'nın zaferini anlatıyor.',q:{s:'Başkomutanlık Meydan Muharebesi\'nin kazanıldığı gün hangi bayram olarak kutlanır?',o:['30 Ağustos Zafer Bayramı','19 Mayıs','10 Kasım'],a:0,ok:'c5',no:'c5',learn:'Büyük Taarruz sonrası kazanılan zafer, 30 Ağustos 1922 tarihiyle Zafer Bayramı olarak kutlanır.'}},
 c5:{e:'🏙️',t:'Zaman makinesi seni 1923 sonbaharına atıyor. Ankara\'da büyük bir heyecan var!',q:{s:'Cumhuriyet hangi tarihte ilan edildi?',o:['29 Ekim 1923','23 Nisan 1920','10 Kasım 1938'],a:0,ok:'c6',no:'c6',learn:'Cumhuriyet 29 Ekim 1923\'te ilan edildi ve Mustafa Kemal Atatürk ilk Cumhurbaşkanı seçildi.'}},
 c6:{e:'🗺️',t:'Selim sana bir harita veriyor. Ankara\'nın başkent oluşunun hikâyesini çözmen gerek.',c:[{t:'🔎 Haritada Ankara\'yı incele',to:'c7',fx:{bilgi:1}},{t:'🚂 Tren istasyonunu kontrol et',to:'c7',fx:{hazine:1}}]},
 c7:{e:'🏆',t:'Selim: "Son soru: Ankara ne zaman başkent oldu?"',q:{s:'Ankara\'nın başkent oluşu hangi tarihtir?',o:['13 Ekim 1923','29 Ekim 1923','23 Nisan 1920'],a:0,ok:'c8',no:'c8',learn:'Ankara, Cumhuriyet\'in ilanından 16 gün önce, 13 Ekim 1923\'te başkent oldu.'}},
 c8:{e:'🏆',end:'win',t:'Tarih dedektifliği tamam! Selim sana "Genç Tarihçi" madalyasını takıyor. Zaman makinen seni evine geri götürüyor.'},
 c9:{e:'💤',end:'lose',t:'Zaman makinesinin enerjisi bitti ve bugüne geri döndün. Yeniden deneyebilirsin!'}}},
matematik:{t:'Matematik Ormanı',e:'🌲',d:'Sayıları ve şekilleri kullanarak ormanın bekçisini bul!',s:'m1',n:{
 m1:{e:'🌲',t:'Matematik Ormanı\'nın girişindesin. Bilge Baykuş: "Ormandan çıkmak için üç kapıyı açmalısın. Hazır mısın?"',c:[{t:'🦉 Hazırım!',to:'m2'}]},
 m2:{e:'🍰',t:'Birinci kapıda bir pasta var. Baykuş: "Pastanın yarısı ve dörtte biri yenmiş."',q:{s:'1/2 + 1/4 kaç eder?',o:['3/4','2/6','1/8'],a:0,ok:'m3',no:'m3',learn:'Paydaları eşitle: 1/2 = 2/4; 2/4 + 1/4 = 3/4.'}},
 m3:{e:'🔺',t:'İkinci kapı üçgen biçiminde. Üzerinde iki açı yazıyor: 60° ve 70°.',q:{s:'Üçüncü açı kaç derecedir?',o:['50°','60°','70°'],a:0,ok:'m4',no:'m4',learn:'Üçgenin iç açıları toplamı 180°. 180 − (60 + 70) = 50.'}},
 m4:{e:'🛤️',t:'Önünde iki patika ayrılıyor.',c:[{t:'🌿 Gür otlu patika',to:'m5',fx:{enerji:-1}},{t:'🪨 Taşlı patika',to:'m5',fx:{hazine:1}}]},
 m5:{e:'📏',t:'Bir çit gördün: uzunluğu 8 m, genişliği 5 m olan dikdörtgen bahçeyi çevreliyor.',q:{s:'Bahçenin çevresi kaç metredir?',o:['26 m','40 m','13 m'],a:0,ok:'m6',no:'m6',learn:'Dikdörtgenin çevresi 2 × (8 + 5) = 26 m.'}},
 m6:{e:'🧮',t:'Son kapı: bir sandıkta 80 elmanın %50\'sini istiyor.',q:{s:'Kaç elma almalısın?',o:['40','50','30'],a:0,ok:'m7',no:'m7',learn:'%50 yarım demektir: 80 ÷ 2 = 40.'}},
 m7:{e:'🏆',end:'win',t:'Üç kapı da açıldı! Bilge Baykuş sana "Matematik Bekçisi" rozetini veriyor.'},
 m8:{e:'💤',end:'lose',t:'Çok yoruldun ve ormanda mola vermen gerekti. Yeniden deneyebilirsin!'}}}};
let A,node,st,learned,hist;
function menu(){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},'🧭 İnteraktif Macera')),h('div',{class:'center'},h('div',{class:'msg'},'Bir macera seç. Seçimlerin hikâyeyi değiştirir; bilgi sorularını doğru yanıtla!'),
 h('div',{class:'row'},Object.entries(ADV).map(([k,a])=>h('div',{class:'cardA',onclick:()=>start(k)},h('div',{style:'font-size:44px'},a.e),h('b',{},a.t),h('span',{},a.d))))))}
function start(k){A=ADV[k];node=A.s;st={enerji:3,bilgi:0,hazine:0};learned=[];draw()}
function fx(f){if(!f)return;for(const k in f)st[k]=(st[k]||0)+f[k]}
function bar(){return h('div',{class:'top'},h('h2',{},A.e+' '+A.t),h('span',{class:'sp'}),h('div',{class:'stats'},h('span',{class:'chip'},'❤️ '+st.enerji),h('span',{class:'chip'},'🧠 '+st.bilgi),h('span',{class:'chip'},'🪙 '+st.hazine)),h('button',{class:'btn alt',onclick:menu},'☰'))}
function go(to){if(st.enerji<=0){const L=Object.keys(A.n).find(k=>A.n[k].end==='lose');node=L;draw();return}node=to;draw()}
function draw(){app.innerHTML='';app.append(bar());const n=A.n[node];const box=h('div',{class:'story pop'},h('div',{class:'em'},n.e),h('p',{},n.t));
 if(n.end){sfx[n.end==='win'?'win':'bad']();const score=st.bilgi*10+st.hazine*5+st.enerji*5;
  box.append(h('div',{class:'msg '+(n.end==='win'?'ok':'bad')},n.end==='win'?'🎉 Macera tamamlandı! Puan: '+score:'Macera yarıda kaldı'),learned.length?h('div',{class:'learn'},h('b',{},'📚 Öğrendiklerin:'),h('ul',{},learned.map(x=>h('li',{},x)))):'',h('div',{class:'row'},h('button',{class:'btn',onclick:()=>start(Object.keys(ADV).find(k=>ADV[k]===A))},'🔄 Tekrar'),h('button',{class:'btn alt',onclick:menu},'Maceralar')));if(n.end==='win')window.__won=true}
 else if(n.q){const q=n.q;box.append(h('p',{style:'font-weight:800;color:var(--gold)'},'❓ '+q.s));const opts=shuf(q.o.map((t,i)=>({t,i})));let answered=false;
  const wrap=h('div');opts.forEach(o=>wrap.append(h('button',{class:'opt',onclick:e=>{if(answered)return;answered=true;const ok=o.i===q.a;e.target.classList.add(ok?'good':'bad');if(ok){st.bilgi++;sfx.ok()}else{st.enerji--;sfx.bad();[...wrap.children][opts.findIndex(x=>x.i===q.a)].classList.add('good')}
   learned.push(q.learn);box.append(h('div',{class:'learn'},(ok?'✅ Doğru! ':'❌ Doğrusu: '+q.o[q.a]+'. ')+q.learn),h('button',{class:'btn',style:'margin-top:10px',onclick:()=>go(ok?q.ok:q.no)},'Devam ▶'));$('#ms')}},o.t)));box.append(wrap)}
 else n.c.forEach(c=>box.append(h('button',{class:'opt',onclick:()=>{fx(c.fx);sfx.tap();go(c.to)}},c.t)));
 app.append(box,h('div',{class:'msg',id:'ms'},''))}
menu();
</script></body></html>
'''

ARCADE_HTML['kultur'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.gal{display:flex;gap:12px;flex-wrap:wrap;justify-content:center;max-width:900px;margin:auto}
.tile0{width:140px;cursor:pointer;text-align:center;font-size:13px;font-weight:700}
.tile0 .im{width:140px;height:140px;border-radius:18px;overflow:hidden;border:3px solid var(--line);position:relative}
.tile0:hover .im{border-color:var(--ac)}.tile0 .st{position:absolute;right:4px;top:4px;font-size:16px}
.pz{display:grid;gap:3px;margin:auto;border:3px solid var(--ac);border-radius:12px;padding:3px;background:#052f37}
.pt{overflow:hidden;cursor:pointer;border-radius:6px;position:relative;border:2px solid transparent}
.pt.empty{background:rgba(255,255,255,.05);cursor:default}.pt.sel{border-color:var(--gold)}.pt.ok{border-color:rgba(74,222,128,.7)}
.pt svg{display:block;width:100%;height:100%}.pt b{position:absolute;left:4px;top:2px;font-size:13px;color:#fff;text-shadow:0 1px 3px #000}
.info{width:min(96%,640px);margin:auto;border-radius:22px;border:3px solid var(--ac);background:linear-gradient(160deg,#0b4a55,#052a31);padding:16px;text-align:left}
.tabs .btn.on{outline:3px solid var(--gold)}
.prev{width:150px;height:150px;border-radius:14px;overflow:hidden;border:3px solid var(--line)}
</style></head><body><div id="app"></div><script>
const app=$('#app');
let _sk=0;const SK=(a,b)=>{const id="sk"+(++_sk);return `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient></defs><rect width="300" height="300" fill="url(#${id})"/>`};
const R=(x,y,w,h,f,x2='')=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${f}" ${x2}/>`;
const P=(pts,f)=>`<polygon points="${pts}" fill="${f}"/>`;
const C=(x,y,r,f)=>`<circle cx="${x}" cy="${y}" r="${r}" fill="${f}"/>`;
const E=(x,y,rx,ry,f)=>`<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="${f}"/>`;
const cols=(x0,y,n,gap,w,h,f)=>Array.from({length:n},(_,i)=>R(x0+i*gap,y,w,h,f)).join('');
const ART={
giza:()=>SK('#fde68a','#fb923c')+C(235,60,26,'#fff7ed')+R(0,210,300,90,'#f5c26b')+P('40,215 120,100 200,215','#d9a04a')+P('120,100 200,215 150,215','#b9822f')+P('150,215 220,130 290,215','#e2ad56')+P('220,130 290,215 250,215','#c18a35')+P('10,225 55,175 100,225','#e8b963'),
cin:()=>SK('#bae6fd','#e0f2fe')+P('0,300 0,150 90,110 170,160 260,90 300,120 300,300','#4d7c0f')+P('0,300 0,200 100,170 180,210 300,150 300,300','#65a30d')+'<path d="M0 230 L60 190 L100 205 L150 160 L200 170 L260 110 L300 120" stroke="#a8a29e" stroke-width="16" fill="none"/>'+[[60,190],[150,160],[260,110]].map(([x,y])=>R(x-12,y-34,24,34,'#78716c')+R(x-14,y-40,28,8,'#57534e')).join(''),
petra:()=>SK('#fed7aa','#fdba74')+P('0,300 0,60 70,40 70,300','#c2410c')+P('300,300 300,50 230,40 230,300','#c2410c')+R(70,90,160,210,'#e9967a')+R(100,120,100,180,'#f0a58a')+P('90,120 150,80 210,120','#e9967a')+cols(108,150,5,20,12,100,'#fbcfae')+R(130,230,40,70,'#7c2d12')+E(150,300,90,16,'#d97706'),
machu:()=>SK('#99f6e4','#ecfeff')+P('150,40 270,230 30,230','#365314')+P('150,40 190,100 110,100','#4d7c0f')+R(0,230,300,70,'#4d7c0f')+[0,1,2,3,4].map(i=>R(40+i*8,210-i*28,220-i*16,22,i%2?'#86a34a':'#a3b86c')).join('')+[0,1,2,3].map(i=>R(120+i*10,200-i*26,22,18,'#d6d3d1')).join('')+P('0,300 60,200 120,300','#3f6212')+P('180,300 250,190 300,300','#3f6212'),
chichen:()=>SK('#a7f3d0','#ecfccb')+R(0,240,300,60,'#65a30d')+[0,1,2,3,4,5,6].map(i=>R(50+i*10,230-i*24,200-i*20,24,i%2?'#d6d3d1':'#a8a29e')).join('')+R(130,85,40,30,'#78716c')+R(143,95,14,20,'#292524')+R(138,100,24,140,'#e7e5e4','opacity=".55"')+C(240,50,22,'#fde047'),
kolezyum:()=>SK('#fecaca','#fef3c7')+E(150,235,140,28,'#a8a29e')+R(15,120,270,115,'#d6c1a0')+[0,1,2].map(r=>Array.from({length:9},(_,i)=>`<path d="M${28+i*28} ${150+r*30} v-14 a10 10 0 0 1 20 0 v14z" fill="#7c5a3a"/>`).join('')).join('')+E(150,120,135,22,'#e7d3b0')+R(0,262,300,38,'#84cc16'),
tac:()=>SK('#c4b5fd','#fce7f3')+R(0,230,300,70,'#bae6fd')+R(70,150,160,80,'#fafafa')+`<path d="M95 150 a55 55 0 0 1 110 0z" fill="#fff"/>`+R(148,70,4,20,'#fde68a')+C(150,96,6,'#fde68a')+R(40,100,22,130,'#f5f5f4')+R(238,100,22,130,'#f5f5f4')+P('40,100 51,78 62,100','#f5f5f4')+P('238,100 249,78 260,100','#f5f5f4')+`<path d="M130 230 v-50 a20 20 0 0 1 40 0 v50z" fill="#94a3b8"/>`+R(60,250,180,8,'#e0f2fe','opacity=".6"'),
kapadokya:()=>SK('#fb923c','#fde68a')+P('0,300 0,190 120,150 300,200 300,300','#d9a066')+[[60,230,70],[120,240,90],[190,225,80],[250,245,60]].map(([x,y,h])=>P(`${x-16},${y+60} ${x},${y-h+60} ${x+16},${y+60}`,'#c98a52')+C(x,y-h+62,9,'#a96b3c')).join('')+[[70,70,'#ef4444'],[160,50,'#facc15'],[240,90,'#3b82f6']].map(([x,y,c])=>E(x,y,22,26,c)+R(x-6,y+26,12,10,'#78350f')).join(''),
gobekli:()=>SK('#fde68a','#fbbf24')+R(0,230,300,70,'#c9a26b')+E(150,235,130,30,'#b8905a')+[[60,200,80],[110,185,100],[190,185,100],[240,200,80]].map(([x,y,h])=>R(x-14,y-h+80,28,h,'#8d6e4a')+R(x-34,y-h+68,68,20,'#8d6e4a')).join('')+R(138,115,24,115,'#a8845a')+R(116,105,68,20,'#a8845a')+P('145,150 150,140 155,150','#5a4630')+C(235,55,24,'#fff7ed'),
ayasofya:()=>SK('#fdba74','#fed7aa')+R(0,250,300,50,'#78716c')+R(60,170,180,85,'#d6a77a')+`<path d="M85 170 a65 62 0 0 1 130 0z" fill="#b45f3a"/>`+`<path d="M60 190 a30 30 0 0 1 30-30 v30z" fill="#c0724a"/><path d="M240 190 a30 30 0 0 0 -30 -30 v30z" fill="#c0724a"/>`+[30,262].map(x=>R(x-6,100,12,150,'#e7e5e4')+P(`${x-9},100 ${x},60 ${x+9},100`,'#475569')).join('')+cols(80,200,6,26,12,50,'#8c4f2e')+R(147,92,6,16,'#fde047'),
pamukkale:()=>SK('#7dd3fc','#e0f2fe')+P('0,300 0,110 300,200 300,300','#f8fafc')+[[60,170],[130,195],[200,220],[260,240]].map(([x,y])=>E(x,y,52,16,'#67e8f9')+E(x,y-3,46,11,'#a5f3fc')).join('')+[[100,150],[170,175],[240,200]].map(([x,y])=>E(x,y,40,12,'#38bdf8')).join('')+P('0,300 0,260 80,300','#d6d3d1'),
efes:()=>SK('#bfdbfe','#fef9c3')+R(0,250,300,50,'#d6d3d1')+R(60,110,180,145,'#e9d5b0')+R(60,100,180,14,'#c8a96e')+P('55,100 150,60 245,100','#d9bd88')+cols(70,125,6,28,14,125,'#f5e6c4')+cols(70,125,6,28,14,3,'#a8905c')+[0,1,2].map(i=>`<path d="M${100+i*50} 250 v-45 a14 14 0 0 1 28 0 v45z" fill="#6b5a3a"/>`).join('')+R(60,184,180,6,'#c8a96e'),
anitkabir:()=>SK('#fecdd3','#ffe4e6')+R(0,255,300,45,'#a8a29e')+R(40,150,220,105,'#e7dcc6')+R(40,142,220,12,'#d6c7a3')+cols(52,158,10,21,12,95,'#f5ebd3')+R(130,70,40,80,'#e7dcc6')+R(125,62,50,10,'#d6c7a3')+P('130,62 150,40 170,62','#d6c7a3')+R(100,236,100,19,'#d1d5db')+R(20,262,260,6,'#78716c'),
eyfel:()=>SK('#a5b4fc','#fbcfe8')+R(0,265,300,35,'#65a30d')+P('150,30 120,265 180,265','#44403c')+`<path d="M139 110 H161 M130 160 H170 M118 215 H182" stroke="#78716c" stroke-width="5"/>`+`<path d="M120 265 q30 -60 60 0" fill="none" stroke="#78716c" stroke-width="6"/>`+R(128,130,44,5,'#78716c')+C(240,60,20,'#fff7ed'),
ozgurluk:()=>SK('#99f6e4','#e0f2fe')+R(0,255,300,45,'#0ea5e9')+R(105,200,90,55,'#a8a29e')+R(120,160,60,45,'#9ca3af')+P('120,160 180,160 170,90 130,90','#6ee7b7')+C(150,76,16,'#6ee7b7')+P('135,64 142,48 150,62 158,46 165,64','#6ee7b7')+R(168,70,10,6,'#6ee7b7')+R(172,30,8,50,'#6ee7b7')+P('170,30 176,8 182,30','#fde047')};
const LM=[
{k:'giza',g:0,n:'Gize Piramitleri',c:'Mısır',f:'Antik Dünyanın Yedi Harikası\'ndan günümüze ulaşan tek yapıdır; yaklaşık 4500 yıl önce yapıldı.'},
{k:'cin',g:0,n:'Çin Seddi',c:'Çin',f:'Yüzyıllar boyunca eklenen bölümleriyle binlerce kilometre uzanan dev bir savunma duvarıdır.'},
{k:'petra',g:0,n:'Petra',c:'Ürdün',f:'Nebatiler tarafından pembe kumtaşı kayalara oyulmuştur; "Gül Kenti" diye bilinir.'},
{k:'machu',g:0,n:'Machu Picchu',c:'Peru',f:'İnka uygarlığının And Dağları\'nda yaklaşık 2400 m yükseklikteki kenti, 15. yüzyıla aittir.'},
{k:'chichen',g:0,n:'Chichén Itzá (El Castillo)',c:'Meksika',f:'Maya uygarlığının önemli şehridir; basamaklı piramidi bir takvim gibi tasarlanmıştır.'},
{k:'kolezyum',g:0,n:'Kolezyum',c:'İtalya',f:'Roma\'daki bu dev amfitiyatro yaklaşık 50 bin seyirci alabiliyordu.'},
{k:'tac',g:0,n:'Tac Mahal',c:'Hindistan',f:'Agra\'da, Şah Cihan\'ın eşi Mümtaz Mahal için yaptırdığı beyaz mermer türbedir (17. yüzyıl).'},
{k:'kapadokya',g:1,n:'Kapadokya',c:'Türkiye',f:'Nevşehir çevresindeki peri bacaları volkanik tüfün aşınmasıyla oluştu; UNESCO Dünya Mirası\'dır (1985).'},
{k:'gobekli',g:1,n:'Göbeklitepe',c:'Türkiye',f:'Şanlıurfa\'da yaklaşık 12.000 yıllık, bilinen en eski anıtsal tapınak alanıdır; UNESCO listesine 2018\'de girdi.'},
{k:'ayasofya',g:1,n:'Ayasofya',c:'Türkiye',f:'İstanbul\'da 537 yılında tamamlanan devasa kubbeli yapı, mimarlık tarihinin başyapıtlarındandır.'},
{k:'pamukkale',g:1,n:'Pamukkale',c:'Türkiye',f:'Denizli\'de kalsiyum karbonat bakımından zengin termal sular beyaz travertenler oluşturmuştur.'},
{k:'efes',g:1,n:'Efes Antik Kenti',c:'Türkiye',f:'İzmir\'in Selçuk ilçesindedir; Celsus Kütüphanesi ile ünlüdür, Artemis Tapınağı antik dünyanın yedi harikasındandı.'},
{k:'anitkabir',g:1,n:'Anıtkabir',c:'Türkiye',f:'Ankara\'da, Atatürk\'ün anıt mezarıdır; 1953\'te tamamlanmıştır.'},
{k:'eyfel',g:2,n:'Eyfel Kulesi',c:'Fransa',f:'Paris\'te 1889 Dünya Fuarı için yapılmıştır; yaklaşık 330 m yüksekliğindedir.'},
{k:'ozgurluk',g:2,n:'Özgürlük Heykeli',c:'ABD',f:'New York\'ta, Fransa\'nın ABD\'ye hediyesidir ve 1886\'da açılmıştır.'}];

const PH={giza:['All_Gizah_Pyramids.jpg','Kheops-Pyramid.jpg'],cin:['The_Great_Wall_of_China_at_Jinshanling-edit.jpg','Great_Wall_of_China_July_2006.JPG'],petra:['Treasury_petra_crop.jpeg','Al_Khazneh_Petra.jpg'],
machu:['80_-_Machu_Picchu_-_Juin_2009_-_edit.jpg','Machu_Picchu,_Peru.jpg'],chichen:['Chichen_Itza_3.jpg','El_Castillo,_Chichen_Itza.jpg'],kolezyum:['Colosseo_2020.jpg','Colosseum_in_Rome,_Italy_-_April_2007.jpg'],
tac:['Taj_Mahal_(Edited).jpeg','Taj_Mahal,_Agra,_India_edit3.jpg'],kapadokya:['Cappadocia_Balloon_Inflating_Wikimedia_Commons.jpg','Goreme_Cappadocia.jpg','Cappadocia_Chimneys.jpg'],
gobekli:['Göbekli_Tepe,_Urfa.jpg','Gobekli_Tepe_(5).jpg','Göbekli_Tepe_2.jpg'],ayasofya:['Hagia_Sophia_Mars_2013.jpg','Aya_Sophia_(Hagia_Sophia).jpg'],
pamukkale:['Pamukkale_BW_2.jpg','Pamukkale_Travertines.jpg','Pamukkale_-_Travertine_Terrassen.jpg'],efes:['Celsus_Library_in_Ephesus,_Turkey.jpg','Library_of_Celsus_in_Ephesus.jpg','Celsus_Library,_Ephesus.jpg'],
anitkabir:['Anıtkabir.jpg','Anitkabir_-_panoramio.jpg'],eyfel:['Tour_Eiffel_Wikimedia_Commons.jpg','Eiffel_Tower_from_the_Tour_Montparnasse_3,_Paris_May_2008.jpg'],ozgurluk:['Statue_of_Liberty_7.jpg','Statue_of_Liberty_(new_york).jpg']};
const PI={};
function tryPhoto(k,i=0){const list=PH[k]||[];if(i>=list.length){PI[k]=false;return Promise.resolve(null)}
 return new Promise(res=>{const im=new Image();im.referrerPolicy='no-referrer';let done=false;const next=()=>{if(!done){done=true;res(tryPhoto(k,i+1))}};const to=setTimeout(next,7000);
  im.onload=()=>{if(done)return;done=true;clearTimeout(to);if(im.naturalWidth>200){PI[k]=im;const e=document.querySelector('.im[data-k="'+k+'"]');if(e)e.innerHTML=thumb(k);res(im)}else{done=false;next()}};
  im.onerror=()=>{clearTimeout(to);next()};im.src='https://commons.wikimedia.org/wiki/Special:FilePath/'+encodeURIComponent(list[i])+'?width=900'})}
const thumb=k=>PI[k] instanceof Image?`<img src="${PI[k].src}" style="width:100%;height:100%;object-fit:cover;display:block">`:svg(k);
function tileCanvas(im,r,c,cs){const cv=document.createElement('canvas');cv.width=cv.height=cs;const sw=Math.min(im.naturalWidth,im.naturalHeight),sx=(im.naturalWidth-sw)/2,sy=(im.naturalHeight-sw)/2,u=sw/N;cv.getContext('2d').drawImage(im,sx+c*u,sy+r*u,u,u,0,0,cs,cs);cv.style.cssText='width:100%;height:100%;display:block';return cv}
const GN=['🌍 Dünyanın Harikaları','🇹🇷 Türkiye','🗼 İkonik Yerler'];
let grp=0,L,mode,N,tiles,empty,moves,sel,t0,tm,done;
const stars=()=>store('lm')||{};
const FX='<defs><filter id="gr"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 .16 0"/></filter><radialGradient id="vg" cx=".5" cy=".5" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".38"/></radialGradient></defs><rect width="300" height="300" filter="url(#gr)"/><rect width="300" height="300" fill="url(#vg)"/>';
const svg=(k,vb)=>`<svg viewBox="${vb||'0 0 300 300'}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">${ART[k]()}${FX}</svg>`;
function menu(){clearInterval(tm);app.innerHTML='';const S=stars();
 app.append(h('div',{class:'top'},h('h2',{},'🗺️ Kültür & Coğrafya Puzzle')),h('div',{class:'center',style:'justify-content:flex-start'},h('div',{class:'msg'},'Bir yapı seç, puzzle\'ı tamamla ve hakkında ilginç bilgiler öğren!'),
 h('div',{class:'row tabs'},GN.map((t,i)=>h('button',{class:'btn alt'+(grp===i?' on':''),onclick:()=>{grp=i;menu()}},t))),
 h('div',{class:'gal'},LM.filter(x=>x.g===grp).map(x=>h('div',{class:'tile0',onclick:()=>choose(x)},h('div',{class:'im','data-k':x.k,html:thumb(x.k)+(S[x.k]?'<span class="st">'+'⭐'.repeat(S[x.k])+'</span>':'')}),x.n)))))}
function choose(x){L=x;app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},L.n),h('span',{class:'sp'}),h('button',{class:'btn alt',onclick:menu},'☰')),h('div',{class:'center'},h('div',{class:'prev',html:thumb(L.k)}),h('div',{class:'msg'},'Puzzle türünü seç'),
 h('div',{class:'row'},[['slide',3,'🔢 Kaydırmalı 3×3'],['slide',4,'🔢 Kaydırmalı 4×4'],['swap',3,'🧩 Yapboz 3×3'],['swap',4,'🧩 Yapboz 4×4']].map(([m,n,l])=>h('button',{class:'btn',onclick:()=>start(m,n)},l)))))}
async function start(m,n){mode=m;N=n;if(PH[L.k]&&PI[L.k]===undefined){app.innerHTML='<div class="center big">Fotoğraf yükleniyor…</div>';await Promise.race([tryPhoto(L.k),sleep(5000)])}moves=0;sel=null;done=false;t0=Date.now();
 tiles=[...Array(N*N).keys()];
 if(m==='slide'){empty=N*N-1;let last=-1;for(let i=0;i<N*N*14;i++){const nb=nbrs(empty).filter(x=>x!==last);const j=pick(nb);[tiles[empty],tiles[j]]=[tiles[j],tiles[empty]];last=empty;empty=j}if(tiles.every((v,i)=>v===i))return start(m,n)}
 else{do{tiles=shuf(tiles)}while(tiles.every((v,i)=>v===i)||tiles.some((v,i)=>false))}
 clearInterval(tm);tm=setInterval(()=>{const e=$('#tm');if(e&&!done)e.textContent='⏱ '+fmt((Date.now()-t0)/1000|0)},1000);draw()}
function fmt(s){return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')}
function nbrs(i){const r=Math.floor(i/N),c=i%N,o=[];if(r>0)o.push(i-N);if(r<N-1)o.push(i+N);if(c>0)o.push(i-1);if(c<N-1)o.push(i+1);return o}
function draw(){app.innerHTML='';const size=Math.min(innerHeight-210,innerWidth-40,520);const cs=Math.floor(size/N);
 app.append(h('div',{class:'top'},h('h2',{},L.n),h('span',{class:'sp'}),h('span',{class:'chip',id:'tm'},'⏱ '+fmt((Date.now()-t0)/1000|0)),h('span',{class:'chip'},'Hamle '+moves),h('button',{class:'btn alt',onclick:()=>choose(L)},'↩'),h('button',{class:'btn alt',onclick:menu},'☰')));
 const g=h('div',{class:'pz',style:`grid-template-columns:repeat(${N},${cs}px)`});
 tiles.forEach((v,i)=>{const isE=mode==='slide'&&i===empty;const el=h('div',{class:'pt'+(isE?' empty':'')+(sel===i?' sel':'')+(!isE&&v===i?' ok':''),'data-i':i,style:`width:${cs}px;height:${cs}px`,onclick:()=>tap(i)});
  if(!isE){const r=Math.floor(v/N),c=v%N,w=300/N;if(PI[L.k] instanceof Image){el.append(tileCanvas(PI[L.k],r,c,cs));if(mode==='slide')el.append(h('b',{},v+1))}else el.innerHTML=svg(L.k,`${c*w} ${r*w} ${w} ${w}`)+(mode==='slide'?`<b>${v+1}</b>`:'')}g.append(el)});
 app.append(g,h('div',{class:'msg',id:'ms'},mode==='slide'?'Parçaya dokun, boşluğa kayar.':'İki parçaya sırayla dokunarak yerlerini değiştir.'),h('div',{class:'row'},h('div',{class:'prev',style:'width:90px;height:90px',html:thumb(L.k)})))}
function tap(i){if(done)return;if(mode==='slide'){if(!nbrs(empty).includes(i))return;[tiles[empty],tiles[i]]=[tiles[i],tiles[empty]];empty=i;moves++;sfx.tap()}
 else{if(sel===null){sel=i;sfx.tap();draw();return}if(sel!==i){[tiles[sel],tiles[i]]=[tiles[i],tiles[sel]];moves++;sfx.tap()}sel=null}
 draw();if(tiles.every((v,i)=>v===i))finish()}
function finish(){done=true;clearInterval(tm);sfx.win();const secs=(Date.now()-t0)/1000|0;const par=N*N*(mode==='slide'?9:2);const s=moves<=par?3:moves<=par*2?2:1;const S=stars();S[L.k]=Math.max(S[L.k]||0,s);store('lm',S);
 const opts=shuf([L.c,...shuf([...new Set(LM.map(x=>x.c))].filter(c=>c!==L.c)).slice(0,2)]);
 app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},'🎉 Puzzle tamam!'),h('span',{class:'sp'}),h('button',{class:'btn alt',onclick:menu},'☰')),
  h('div',{class:'center'},h('div',{class:'prev',style:'width:min(80vw,280px);height:min(80vw,280px)',html:thumb(L.k)}),h('div',{class:'stars'},'⭐'.repeat(s)+'☆'.repeat(3-s)),
   h('div',{class:'info'},h('b',{style:'font-size:20px'},L.n),h('div',{class:'msg',style:'text-align:left'},`${moves} hamle · ${fmt(secs)}`),h('p',{},L.f),PI[L.k] instanceof Image?h('div',{class:'msg',style:'text-align:left;font-size:11px'},'Fotoğraf: Wikimedia Commons'):'',
    h('div',{class:'msg',style:'text-align:left'},'❓ Bu yapı hangi ülkede?'),h('div',{class:'row',id:'qo'},opts.map(o=>h('button',{class:'btn alt',onclick:e=>{const ok=o===L.c;e.target.className='btn '+(ok?'':'bad');ok?sfx.ok():sfx.bad();$('#qr').textContent=ok?'✅ Doğru! '+L.c:'❌ Doğrusu: '+L.c;if(ok)window.__won=true}},o))),h('div',{class:'msg',id:'qr'},'')),
   h('div',{class:'row'},h('button',{class:'btn',onclick:()=>start(mode,N)},'🔄 Tekrar'),h('button',{class:'btn alt',onclick:menu},'Diğer yapılar'))));window.__done=true}
menu();LM.forEach(x=>setTimeout(()=>tryPhoto(x.k),50));
</script></body></html>
'''

ARCADE_HTML['cark'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
canvas{display:block;margin:auto;max-width:100%}
.q{width:min(96%,640px);margin:auto;border-radius:24px;border:3px solid var(--ac);background:linear-gradient(160deg,#0b4a55,#052a31);padding:18px}
.q h3{margin:0 0 10px;font-size:clamp(18px,3vw,24px)}
.o{display:block;width:100%;text-align:left;margin:7px 0;padding:11px 14px;border-radius:14px;border:2px solid var(--line);background:rgba(255,255,255,.08);color:var(--t);font-size:16px;font-weight:700;cursor:pointer;font-family:inherit}
.o:hover{border-color:var(--ac)}.o.g{background:rgba(74,222,128,.4)}.o.b{background:rgba(251,113,133,.4)}
</style></head><body><div id="app"></div><script>
const app=$('#app');
const CATS=[{n:'Fen',e:'🔬',c:'#22c55e'},{n:'Sosyal',e:'🌍',c:'#3b82f6'},{n:'Matematik',e:'➗',c:'#f59e0b'},{n:'Türkçe',e:'📝',c:'#ec4899'},{n:'Genel Kültür',e:'🌟',c:'#a855f7'}];
// [soru, doğru, yanlış1, yanlış2, yanlış3]
const Q={
'Fen':[['Suyun deniz seviyesinde kaynama sıcaklığı kaç °C\'dir?','100','50','200','0'],['Bitkilerin güneş ışığıyla besin üretmesine ne denir?','Fotosentez','Solunum','Terleme','Çimlenme'],['Hangisi yenilenebilir enerji kaynağıdır?','Rüzgâr','Kömür','Petrol','Doğalgaz'],['Ay, Dünya\'nın etrafında yaklaşık ne kadar sürede bir tur atar?','Yaklaşık 1 ay','Yaklaşık 1 hafta','Yaklaşık 1 yıl','24 saat'],['Hangisi bir ışık kaynağıdır?','Güneş','Ay','Ayna','Gezegen'],['Mıknatıs hangi maddeyi çeker?','Demir','Plastik','Cam','Tahta'],['Kanı vücuda pompalayan organımız hangisidir?','Kalp','Akciğer','Mide','Karaciğer'],['Katı bir maddenin ısınarak sıvıya dönüşmesine ne denir?','Erime','Donma','Buharlaşma','Yoğuşma']],
'Sosyal':[['Türkiye\'nin başkenti neresidir?','Ankara','İstanbul','İzmir','Bursa'],['Cumhuriyet hangi yıl ilan edildi?','1923','1920','1938','1453'],['Dünyanın en büyük okyanusu hangisidir?','Büyük (Pasifik) Okyanus','Atlas Okyanusu','Hint Okyanusu','Arktik Okyanusu'],['Yön bulmaya yarayan alet hangisidir?','Pusula','Termometre','Barometre','Cetvel'],['Türkiye\'nin en uzun nehri hangisidir?','Kızılırmak','Fırat','Sakarya','Meriç'],['Türkiye kaç coğrafi bölgeye ayrılır?','7','5','9','12'],['Hangi kıta en kalabalık nüfusa sahiptir?','Asya','Avrupa','Afrika','Okyanusya'],['23 Nisan\'da hangi bayram kutlanır?','Ulusal Egemenlik ve Çocuk Bayramı','Zafer Bayramı','Cumhuriyet Bayramı','Gençlik ve Spor Bayramı']],
'Matematik':[['7 × 8 kaçtır?','56','54','48','63'],['Üçgenin iç açıları toplamı kaç derecedir?','180','90','360','120'],['3/4 + 1/4 kaçtır?','1','4/8','3/16','1/2'],['%25 hangi kesre eşittir?','1/4','1/2','2/5','3/4'],['Kenarı 5 cm olan karenin çevresi kaç cm\'dir?','20','25','10','15'],['Hangisi asal sayıdır?','13','9','15','21'],['144 ÷ 12 kaçtır?','12','14','11','13'],['Bir doğru parçasının orta noktası onu kaç eşit parçaya böler?','2','3','4','1']],
'Türkçe':[['"Mavi kalem" sözcüklerinden hangisi sıfattır?','Mavi','Kalem','İkisi de','Hiçbiri'],['Cümlede işi yapanı bildiren öğe hangisidir?','Özne','Yüklem','Nesne','Tümleç'],['"Büyük" sözcüğünün zıt anlamlısı hangisidir?','Küçük','Kocaman','Ağır','Uzun'],['Soru cümlesinin sonuna hangi işaret konur?','Soru işareti (?)','Nokta (.)','Virgül (,)','Ünlem (!)'],['"Elma" sözcüğü kaç hecelidir?','2','1','3','4'],['Hangi sözcük çoğul biçimdedir?','Kitaplar','Kitap','Kalem','Defter'],['Atasözü nedir?','Uzun deneyimlerden doğan öğüt veren kalıp söz','Mecaz anlamlı kalıp söz','Bir şiir türü','Bir noktalama işareti'],['Hangisi anlamdaş (eş anlamlı) bir çifttir?','Hasta – rahatsız','Sıcak – soğuk','Gece – gündüz','Uzun – kısa']],
'Genel Kültür':[['Dünyanın en yüksek dağı hangisidir?','Everest','Ağrı','Kilimanjaro','Alpler'],['Mona Lisa tablosunu kim yapmıştır?','Leonardo da Vinci','Picasso','Van Gogh','Michelangelo'],['Standart bir piyanoda kaç tuş vardır?','88','64','76','100'],['Satranç tahtasında kaç kare vardır?','64','36','81','100'],['Hangi gezegen "Kızıl Gezegen" olarak bilinir?','Mars','Venüs','Jüpiter','Satürn'],['Türkiye\'nin en kalabalık şehri hangisidir?','İstanbul','Ankara','İzmir','Bursa'],['Dünyanın en büyük sıcak çölü hangisidir?','Sahra','Gobi','Kalahari','Karakum'],['Eyfel Kulesi hangi şehirdedir?','Paris','Londra','Roma','Berlin']]};
let ang=0,spinning=false,score=0,turn=0,TOTAL=10,asked={},streak=0,cvs;
function menu(){app.innerHTML='';score=0;turn=0;streak=0;asked={};app.append(h('div',{class:'center'},h('div',{class:'big'},'🎡 Bilgi Çarkı'),h('div',{class:'msg'},'Çarkı çevir, gelen konudan soruyu bil! Doğru cevaplar puan ve seri bonusu kazandırır.'),h('button',{class:'btn',onclick:wheel},'Başla ▶')))}
function drawWheel(){const ctx=cvs.getContext('2d'),W=cvs.width,R=W/2-8;ctx.clearRect(0,0,W,W);ctx.save();ctx.translate(W/2,W/2);ctx.rotate(ang);const n=CATS.length,a=2*Math.PI/n;
 CATS.forEach((c,i)=>{ctx.beginPath();ctx.moveTo(0,0);ctx.arc(0,0,R,i*a,(i+1)*a);ctx.closePath();ctx.fillStyle=c.c;ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=4;ctx.stroke();
  ctx.save();ctx.rotate(i*a+a/2);ctx.fillStyle='#fff';ctx.font='bold '+W*.045+'px sans-serif';ctx.textAlign='right';ctx.fillText(c.e+' '+c.n,R-18,W*.016);ctx.restore()});
 ctx.restore();ctx.beginPath();ctx.moveTo(W-4,W/2);ctx.lineTo(W-34,W/2-16);ctx.lineTo(W-34,W/2+16);ctx.closePath();ctx.fillStyle='#fbbf24';ctx.fill();ctx.strokeStyle='#000';ctx.stroke();
 ctx.beginPath();ctx.arc(W/2,W/2,22,0,7);ctx.fillStyle='#052a31';ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=4;ctx.stroke()}
function wheel(){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},'🎡 Bilgi Çarkı'),h('span',{class:'sp'}),h('span',{class:'chip'},'Soru '+(Math.min(turn+1,TOTAL))+'/'+TOTAL),h('span',{class:'chip'},'⭐ '+score),streak>1?h('span',{class:'chip'},'🔥 '+streak):'',h('button',{class:'btn alt',onclick:menu},'☰')));
 const size=Math.min(innerHeight-190,innerWidth-30,460);cvs=h('canvas',{width:size,height:size});app.append(cvs,h('div',{class:'row'},h('button',{class:'btn',id:'sp',onclick:spin},'🎡 ÇEVİR')),h('div',{class:'msg',id:'ms'},''));drawWheel()}
function spin(){if(spinning)return;spinning=true;sfx.tap();$('#sp').disabled=true;const n=CATS.length,a=2*Math.PI/n;const idx=rnd(0,n-1);
 // işaretçi sağda (açı 0). idx diliminin ortası işaretçide dursun
 const target=-(idx*a+a/2)+Math.PI*2*rnd(4,6);const start=ang%(Math.PI*2),dur=3200,t0=performance.now();const end=target;
 (function f(t){const k=Math.min(1,(t-t0)/dur),e=1-Math.pow(1-k,3);ang=start+(end-start)*e;drawWheel();if(k%0.08<0.02)beep(300+Math.random()*80,.03,'square',.02);if(k<1)requestAnimationFrame(f);else{spinning=false;setTimeout(()=>ask(idx),400)}})(t0)}
function ask(idx){const cat=CATS[idx];const list=Q[cat.n];asked[cat.n]=asked[cat.n]||[];let pool=list.map((_,i)=>i).filter(i=>!asked[cat.n].includes(i));if(!pool.length){asked[cat.n]=[];pool=list.map((_,i)=>i)}
 const qi=pick(pool);asked[cat.n].push(qi);const [qs,...opts]=list[qi];const o=shuf(opts.map((t,i)=>({t,ok:i===0})));
 app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},cat.e+' '+cat.n),h('span',{class:'sp'}),h('span',{class:'chip'},'⭐ '+score)));
 const box=h('div',{class:'q pop'},h('h3',{},qs));let done=false;
 o.forEach(x=>box.append(h('button',{class:'o',onclick:e=>{if(done)return;done=true;const b=e.target;if(x.ok){b.classList.add('g');streak++;const pts=10+(streak>2?5:0);score+=pts;sfx.ok();$('#ms').textContent='✅ Doğru! +'+pts}else{b.classList.add('b');streak=0;sfx.bad();[...box.querySelectorAll('.o')].find(z=>z.textContent===opts[0]).classList.add('g');$('#ms').textContent='❌ Doğru cevap: '+opts[0]}
   turn++;setTimeout(()=>{if(turn>=TOTAL)end();else wheel()},1700)}},x.t)));
 app.append(box,h('div',{class:'msg',id:'ms'},''))}
function end(){app.innerHTML='';sfx.win();app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🏆 Çark durdu!'),h('div',{class:'msg'},'Toplam puan: '+score+' / '+TOTAL*10+'+'),h('button',{class:'btn',onclick:()=>{menu();wheel()}},'Tekrar çevir'),h('button',{class:'btn alt',onclick:menu},'Menü')));window.__won=true}
menu();
</script></body></html>
'''

ARCADE_HTML['sirala'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.line{width:min(96%,680px);margin:auto;display:flex;flex-direction:column;gap:8px}
.slot{min-height:46px;border-radius:14px;border:2px dashed var(--line);display:flex;align-items:center;gap:10px;padding:6px 12px;font-weight:700}
.slot .n{width:28px;height:28px;border-radius:50%;background:rgba(255,255,255,.12);display:flex;align-items:center;justify-content:center;font-size:13px;flex:none}
.slot.f{border-style:solid;border-color:var(--ok);background:rgba(74,222,128,.15)}.slot .yr{margin-left:auto;color:var(--gold);font-size:13px}
.pool{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;max-width:720px;margin:auto}
.pool .btn{font-size:14px;text-align:center;max-width:320px}
</style></head><body><div id="app"></div><script>
const app=$('#app');
const SETS=[
{t:'📜 Türkiye Tarihinde Dönüm Noktaları',h:'Olayları en eskiden en yeniye sırala',i:[['TBMM açıldı','23 Nisan 1920'],['Büyük Zafer (30 Ağustos)','1922'],['Cumhuriyet ilan edildi','29 Ekim 1923'],['Halifelik kaldırıldı','3 Mart 1924'],['Harf Devrimi (yeni Türk harfleri)','1 Kasım 1928'],['Atatürk\'ün vefatı','10 Kasım 1938']]},
{t:'🌍 Dünya Tarihinden Olaylar',h:'Olayları en eskiden en yeniye sırala',i:[['Göbeklitepe\'nin yapılması','yaklaşık MÖ 9500'],['Büyük Piramit\'in yapılması','yaklaşık MÖ 2560'],['İstanbul\'un fethi','1453'],['Kolomb\'un Amerika\'ya ulaşması','1492'],['Wright kardeşlerin ilk uçuşu','1903'],['İnsanın Ay\'a ilk adımı','1969']]},
{t:'🪐 Güneş\'e Yakınlığa Göre Gezegenler',h:'Güneş\'e en yakından en uzağa sırala',i:[['Merkür','1.'],['Venüs','2.'],['Dünya','3.'],['Mars','4.'],['Jüpiter','5.'],['Satürn','6.']]},
{t:'🐸 Kurbağanın Yaşam Döngüsü',h:'Gelişim sırasına koy',i:[['Yumurta','1. evre'],['İribaş (solungaçlı)','2. evre'],['Arka bacakları çıkan iribaş','3. evre'],['Ön bacakları çıkan genç kurbağa','4. evre'],['Yetişkin kurbağa','5. evre']]},
{t:'💧 Su Döngüsü',h:'Döngünün sırasına koy',i:[['Denizlerden buharlaşma','1'],['Su buharının yükselmesi','2'],['Bulutları oluşturan yoğuşma','3'],['Yağış (yağmur, kar)','4'],['Suyun akarsulara karışıp denize dönmesi','5']]},
{t:'🔢 Küçükten Büyüğe Kesirler',h:'Küçükten büyüğe sırala',i:[['1/8','0,125'],['1/4','0,25'],['1/2','0,5'],['3/4','0,75'],['1','1']]},
{t:'📏 Uzunluk Birimleri',h:'Küçükten büyüğe sırala',i:[['1 milimetre','mm'],['1 santimetre','cm'],['1 metre','m'],['1 kilometre','km']]},
{t:'🍃 Mevsimler ve Aylar',h:'Takvim sırasına göre sırala',i:[['Ocak (kış)','1'],['Nisan (ilkbahar)','4'],['Temmuz (yaz)','7'],['Ekim (sonbahar)','10']]}];
let S,placed,mist,pool;
function menu(){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},'⏳ Sırala')),h('div',{class:'center'},h('div',{class:'msg'},'Bir set seç ve doğru sıraya diz! Doğru sıradaki kartlara dokun.'),h('div',{class:'row'},SETS.map(s=>h('button',{class:'btn',onclick:()=>start(s)},s.t)))))}
function start(s){S=s;placed=[];mist=0;pool=shuf(s.i.map((x,k)=>({k,t:x[0]})));draw()}
function draw(){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},S.t),h('span',{class:'sp'}),h('span',{class:'chip'},'❌ '+mist),h('button',{class:'btn alt',onclick:()=>start(S)},'🔄'),h('button',{class:'btn alt',onclick:menu},'☰')));
 const line=h('div',{class:'line'});S.i.forEach((x,p)=>{const f=p<placed.length;line.append(h('div',{class:'slot'+(f?' f pop':'')},h('span',{class:'n'},p+1),f?[h('span',{},S.i[placed[p]][0]),h('span',{class:'yr'},S.i[placed[p]][1])]:''))});
 app.append(h('div',{class:'msg'},S.h),line,h('div',{class:'pool'},pool.filter(x=>!placed.includes(x.k)).map(x=>h('button',{class:'btn alt',onclick:()=>tap(x.k)},x.t))),h('div',{class:'msg',id:'ms'},''))}
function tap(k){if(k===placed.length){placed.push(k);sfx.ok();if(placed.length===S.i.length){draw();sfx.win();const m=$('#ms');m.className='msg ok pop';m.textContent=`🎉 Hepsi doğru! ${mist} hata`;app.append(h('div',{class:'row'},h('button',{class:'btn',onclick:menu},'Başka set')));window.__won=true;return}draw()}
 else{mist++;sfx.bad();draw();const m=$('#ms');m.className='msg bad shake';m.textContent='Bu sırada değil, tekrar dene!'}}
menu();
</script></body></html>
'''

ARCADE_HTML['sinema'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.word{font-size:clamp(34px,9vw,76px);font-weight:900;color:var(--gold);text-shadow:0 4px 0 rgba(0,0,0,.35);min-height:90px;display:flex;align-items:center;justify-content:center;text-align:center;padding:0 8px}
.cardx{width:min(94%,620px);border-radius:28px;border:3px solid var(--ac);background:linear-gradient(160deg,#0b4a55,#052a31);padding:22px 16px;text-align:center;box-shadow:0 14px 40px rgba(0,0,0,.4)}
.timer{font-size:clamp(40px,9vw,70px);font-weight:900}.timer.low{color:var(--bad);animation:pop .5s infinite alternate}
.tbar{height:10px;border-radius:99px;background:rgba(255,255,255,.12);overflow:hidden;width:min(90%,560px)}
.tbar i{display:block;height:100%;background:linear-gradient(90deg,#2dd4bf,#fbbf24,#fb7185);transition:width .2s linear}
.sel .btn{margin:3px}.sel .on{outline:3px solid var(--gold)}
.team{padding:8px 14px;border-radius:14px;background:rgba(255,255,255,.08);border:2px solid transparent;font-weight:800}
.team.act{border-color:var(--gold);background:rgba(251,191,36,.15)}
.hide{filter:blur(14px);user-select:none}
.mute{font-size:60px}
</style></head><body><div id="app"></div><script>
const app=$('#app');
const CATS={
 'Filmler & Çizgi Filmler':['Aslan Kral','Kayıp Balık Nemo','Örümcek Adam','Karlar Ülkesi','Shrek','Tom ve Jerry','Pamuk Prenses','Külkedisi','Yeşil Hayalet','Toy Story','Harry Potter','Maymun Kral','Alaaddin','Pinokyo','Cin Ali','Heidi','Susam Sokağı','Red Kit','Fareli Köyün Kavalcısı','Küçük Prens','Hababam Sınıfı','Kurtlar Vadisi','Yedi Cüceler','Dünyayı Kurtaran Adam'],
 'Hayvanlar':['Zürafa','Penguen','Kanguru','Yunus','Kaplumbağa','Aslan','Maymun','Kelebek','Kartal','Fil','Timsah','Yarasa','Ahtapot','Tavşan','Köpekbalığı','Deve','Papağan','Karınca','Panda','Kurbağa','Horoz','Arı','Kirpi','Tilki'],
 'Meslekler':['Doktor','Aşçı','Pilot','İtfaiyeci','Terzi','Berber','Futbolcu','Ressam','Öğretmen','Polis','Çiftçi','Fotoğrafçı','Astronot','Mimar','Marangoz','Garson','Şoför','Dişçi','Müzisyen','Balıkçı','Veteriner','Dalgıç','Posta Dağıtıcısı','Bilim İnsanı'],
 'Okul & Ders Kavramları':['Güneş Tutulması','Su Döngüsü','Fotosentez','Mıknatıs','Deprem','Harita Okumak','Kesir','Üçgen','Cumhuriyet Bayramı','Volkan','Ay\'ın Evreleri','Elektrik Devresi','Kıta','Orman Yangını','Geri Dönüşüm','Teneffüs','Mikroskop','Atatürk','Çevre Temizliği','Deney Yapmak','Zeka Küpü','Kütüphane','Okul Servisi','Pusula'],
 'Spor & Oyun':['Basketbol','Yüzme','Voleybol','Bisiklet','Futbol','Tenis','Satranç','Halat Çekme','Ip Atlama','Kayak','Boks','Okçuluk','Jimnastik','Golf','Gizli Saklambaç','Körebe','Uçurtma Uçurmak','Paten','Dart','Dağa Tırmanmak'],
 'Gezilecek Yerler':['Kapadokya','Ayasofya','Anıtkabir','Pamukkale','Galata Kulesi','Eiffel Kulesi','Çanakkale Şehitliği','Boğaz Köprüsü','Efes Antik Kenti','Sümela Manastırı','Nemrut Dağı','Pisa Kulesi','Piramitler','Çin Seddi','Özgürlük Heykeli','Topkapı Sarayı']};
let S={};
function menu(){app.innerHTML='';S={cat:'Karışık',teams:2,time:60,rounds:2};
 const sel=h('div',{class:'sel center',style:'gap:10px'});
 app.append(h('div',{class:'top'},h('h2',{},'🤫 Sessiz Sinema'),h('span',{class:'sp'})),sel);
 function draw(){sel.innerHTML='';sel.append(h('div',{class:'mute'},'🎭'),h('div',{class:'msg'},'Kelimeyi SESSİZCE, sadece mimikle anlat; takımın bilsin! Sözcük söylemek, parmakla yazmak yok.'),
  h('div',{class:'msg'},'Konu'),h('div',{class:'row'},['Karışık',...Object.keys(CATS)].map(c=>h('button',{class:'btn alt'+(S.cat===c?' on':''),onclick:()=>{S.cat=c;draw()}},c))),
  h('div',{class:'msg'},'Takım sayısı'),h('div',{class:'row'},[2,3,4].map(n=>h('button',{class:'btn alt'+(S.teams===n?' on':''),onclick:()=>{S.teams=n;draw()}},n))),
  h('div',{class:'msg'},'Tur süresi (sn)'),h('div',{class:'row'},[30,45,60,90].map(n=>h('button',{class:'btn alt'+(S.time===n?' on':''),onclick:()=>{S.time=n;draw()}},n))),
  h('div',{class:'msg'},'Tur sayısı (her takım kaç kez oynasın)'),h('div',{class:'row'},[1,2,3].map(n=>h('button',{class:'btn alt'+(S.rounds===n?' on':''),onclick:()=>{S.rounds=n;draw()}},n))),
  h('button',{class:'btn',style:'margin-top:8px',onclick:start},'Başla ▶'))}
 draw()}
function poolFor(){const all=S.cat==='Karışık'?Object.values(CATS).flat():CATS[S.cat];return all}
function nextWord(){const all=poolFor();let used=store('used_'+S.cat)||[];let left=all.filter(w=>!used.includes(w)&&!S.seen.has(w));if(!left.length){used=[];left=all.filter(w=>!S.seen.has(w));if(!left.length){S.seen.clear();left=all.slice()}}
 const w=pick(left);S.seen.add(w);used.push(w);store('used_'+S.cat,used.slice(-200));return w}
function start(){S.seen=new Set();S.names=['🔴 Kırmızı','🔵 Mavi','🟢 Yeşil','🟡 Sarı'].slice(0,S.teams);S.score=S.names.map(()=>0);S.turn=0;S.total=S.teams*S.rounds;ready()}
function board(){return h('div',{class:'row'},S.names.map((n,i)=>h('div',{class:'team'+(i===S.turn%S.teams?' act':'')},n+': '+S.score[i])))}
function ready(){clearInterval(S.tm);app.innerHTML='';const t=S.turn%S.teams;
 app.append(h('div',{class:'top'},h('h2',{},'🤫 Sessiz Sinema'),h('span',{class:'sp'}),h('span',{class:'chip'},'Tur '+(Math.floor(S.turn/S.teams)+1)+'/'+S.rounds),h('button',{class:'btn alt',onclick:menu},'☰')),board(),
  h('div',{class:'center pop'},h('div',{class:'mute'},'🎬'),h('div',{class:'big'},S.names[t]+' takımı sahnede!'),h('div',{class:'msg'},'Bir oyuncu seçilsin. Kelimeyi sadece o görecek; diğerleri ekrana bakmasın.'),h('button',{class:'btn',onclick:play},'Kelimeyi göster ve süreyi başlat ⏱')))}
function play(){S.ok=0;S.pass=0;S.word=nextWord();S.end=Date.now()+S.time*1000;render();clearInterval(S.tm);S.tm=setInterval(tick,200)}
function tick(){const l=Math.max(0,S.end-Date.now());const e=$('#tmr');if(e){e.textContent=Math.ceil(l/1000);e.className='timer'+(l<8000?' low':'')}const b=$('#tb');if(b)b.style.width=(l/(S.time*10))+'%';if(l<=0){clearInterval(S.tm);endTurn()}}
function render(){app.innerHTML='';const t=S.turn%S.teams;
 app.append(h('div',{class:'top'},h('h2',{},S.names[t]),h('span',{class:'sp'}),h('span',{class:'chip'},'✓ '+S.ok),h('span',{class:'chip'},'⏭ '+S.pass+'/3')),
 h('div',{class:'center'},h('div',{class:'tbar'},h('i',{id:'tb',style:'width:'+(Math.max(0,S.end-Date.now())/(S.time*10))+'%'})),h('div',{class:'timer',id:'tmr'},Math.ceil(Math.max(0,S.end-Date.now())/1000)),
  h('div',{class:'cardx'},h('div',{class:'msg'},'🤐 Sessiz anlat!'),h('div',{class:'word'+(S.hide?' hide':''),id:'w'},S.word),h('button',{class:'btn alt',onclick:()=>{S.hide=!S.hide;$('#w').classList.toggle('hide',S.hide)}},'👁 Göster / Gizle')),
  h('div',{class:'row'},h('button',{class:'btn',onclick:right},'✓ Bildiler'),h('button',{class:'btn alt',disabled:S.pass>=3,onclick:pass},'⏭ Pas'))))}
function right(){S.ok++;S.score[S.turn%S.teams]++;sfx.ok();S.word=nextWord();render()}
function pass(){if(S.pass>=3)return;S.pass++;sfx.tap();S.word=nextWord();render()}
function endTurn(){sfx.bad();const t=S.turn%S.teams;app.innerHTML='';S.turn++;const fin=S.turn>=S.total;
 app.append(h('div',{class:'center pop'},h('div',{class:'big'},'⏰ Süre bitti!'),h('div',{class:'msg'},S.names[t]+' takımı '+S.ok+' kelime bildi.'),board(),
  fin?h('button',{class:'btn',onclick:result},'Sonuçlar 🏆'):h('button',{class:'btn',onclick:ready},'Sıradaki takım ▶')))}
function result(){const mx=Math.max(...S.score);const w=S.names.filter((n,i)=>S.score[i]===mx);sfx.win();app.innerHTML='';
 app.append(h('div',{class:'center pop'},h('div',{class:'mute'},'🏆'),h('div',{class:'big'},w.length>1?'Berabere: '+w.join(' & '):w[0]+' kazandı!'),board(),h('div',{class:'row'},h('button',{class:'btn',onclick:start},'Tekrar oyna'),h('button',{class:'btn alt',onclick:menu},'Menü')))); window.__won=true}
menu();
</script></body></html>
'''

ARCADE_HTML['kesir'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.bar{display:flex;width:min(92%,640px);height:90px;border-radius:16px;overflow:hidden;border:3px solid #fff;margin:6px auto;position:relative;background:#7c4a1e}
.pc{flex:1;border-right:3px dashed rgba(255,255,255,.9);display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;cursor:pointer;background:linear-gradient(135deg,#a0602a,#7c4a1e);transition:.25s;color:#fde68a}
.pc:last-child{border-right:0}.pc.on{background:linear-gradient(135deg,#fde047,#f59e0b);color:#422006;transform:scaleY(1.06)}
.bar.mini{height:46px;width:min(80%,420px)}
.orders{font-size:22px;font-weight:800}
.fr{display:inline-flex;flex-direction:column;align-items:center;line-height:1.05;vertical-align:middle;margin:0 4px}
.fr i{display:block;border-top:3px solid currentColor;width:100%;margin:2px 0}
.cut{width:42px;height:42px;border-radius:50%;font-size:22px;padding:0}
</style></head><body><div id="app"></div><script>
const app=$('#app');
const fr=(a,b)=>h('span',{class:'fr'},h('span',{},a),h('i'),h('span',{},b));
const gcd=(a,b)=>b?gcd(b,a%b):a;
let lvl=0,score=0,L,parts=2,sel=new Set(),tries=0,done=false,streak=0,total=0;
function make(){const k=lvl%4;
 if(k===0){const d=rnd(2,8),n=rnd(1,d-1);return{kind:'cut',d,n,txt:'Çikolatayı eşit parçalara böl ve bir müşteriye tam olarak ',goal:true}}
 if(k===1){let d1=rnd(2,8),n1=rnd(1,d1-1),d2=rnd(2,8),n2=rnd(1,d2-1);while(n1*d2===n2*d1){d2=rnd(2,8);n2=rnd(1,d2-1)}return{kind:'cmp',a:[n1,d1],b:[n2,d2]}}
 if(k===2){const d=rnd(2,5),n=rnd(1,d-1),m=rnd(2,3);return{kind:'eq',d,n,m}}
 const d=rnd(3,8),a=rnd(1,d-2),b=rnd(1,d-1-a);return{kind:'add',d,a,b}}
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'🍫 Kesir Dilimleme'),h('div',{class:'msg'},'Çikolatayı kes, kesirleri bul, karşılaştır, topla. Sezgiyle kesir öğren!'),h('button',{class:'btn',onclick:()=>{lvl=0;score=0;streak=0;total=0;next()}},'Başla')))}
function next(){L=make();parts=1;sel=new Set();tries=0;done=false;view()}
function head(){return h('div',{class:'top'},h('h2',{},'🍫 Kesir Dilimleme'),h('span',{class:'sp'}),h('span',{class:'chip'},'Seviye '+(lvl+1)),h('span',{class:'chip'},'⭐ '+score),h('button',{class:'btn alt',onclick:menu},'☰'))}
function barEl(d,selSet,click,mini){const b=h('div',{class:'bar'+(mini?' mini':'')});for(let i=0;i<d;i++)b.append(h('div',{class:'pc'+(selSet&&selSet.has(i)?' on':''),onclick:click?()=>click(i):null},selSet&&selSet.has(i)?'':''));return b}
function view(){app.innerHTML='';app.append(head());const box=h('div',{class:'center'});app.append(box);
 if(L.kind==='cut'){box.append(h('div',{class:'orders'},'🧒 "Bana ',fr(L.n,L.d),' ver!"'),h('div',{class:'msg'},'Önce çikolatayı '+L.d+' eşit parçaya böl, sonra parçaları seç.'),barEl(parts,sel,i=>{sel.has(i)?sel.delete(i):sel.add(i);sfx.tap();view()}),
  h('div',{class:'row'},h('button',{class:'btn alt cut',onclick:()=>{if(parts>1){parts--;sel=new Set();sfx.tap();view()}}},'−'),h('span',{class:'chip'},'✂️ '+parts+' parça'),h('button',{class:'btn alt cut',onclick:()=>{if(parts<12){parts++;sel=new Set();sfx.tap();view()}}},'+')),
  h('div',{class:'row'},h('span',{class:'chip'},'Seçtiğin: ',fr(sel.size,parts)),h('button',{class:'btn',onclick:()=>check(parts===L.d&&sel.size===L.n)},'Ver ✓')))}
 else if(L.kind==='cmp'){const[a,b]=[L.a,L.b];box.append(h('div',{class:'orders'},'Hangisi daha büyük?'),h('div',{},fr(a[0],a[1]),barEl(a[1],new Set([...Array(a[0]).keys()]),null,true)),h('div',{},fr(b[0],b[1]),barEl(b[1],new Set([...Array(b[0]).keys()]),null,true)),
  h('div',{class:'row'},h('button',{class:'btn',onclick:()=>check(a[0]*b[1]>b[0]*a[1])},'Üstteki'),h('button',{class:'btn',onclick:()=>check(a[0]*b[1]<b[0]*a[1])},'Alttaki')))}
 else if(L.kind==='eq'){const t=L.d*L.m;box.append(h('div',{class:'orders'},fr(L.n,L.d),' = ',fr('?',t),' ?'),h('div',{class:'msg'},'Çikolatayı '+t+' eşit parçaya böl ve aynı miktarı seç. Kaç parça yeter?'),barEl(t,new Set([...Array(L.n*L.m).keys()]),null,true),barEl(L.d,new Set([...Array(L.n).keys()]),null,true),
  h('div',{class:'row'},[L.n*L.m,L.n*L.m+1,Math.max(1,L.n*L.m-1),L.n+L.d].filter((x,i,a)=>a.indexOf(x)===i).sort(()=>Math.random()-.5).map(v=>h('button',{class:'btn',onclick:()=>check(v===L.n*L.m)},v))))}
 else{box.append(h('div',{class:'orders'},fr(L.a,L.d),' + ',fr(L.b,L.d),' = ?'),h('div',{},barEl(L.d,new Set([...Array(L.a).keys()]),null,true),barEl(L.d,new Set([...Array(L.b).keys()]),null,true)),
  h('div',{class:'row'},[...new Set([L.a+L.b,L.a+L.b+1,Math.max(1,L.a+L.b-1),L.a*L.b+1])].sort(()=>Math.random()-.5).map(v=>h('button',{class:'btn',onclick:()=>check(v===L.a+L.b)},fr(v,L.d)))))}
 box.append(h('div',{class:'msg',id:'ms'},''))}
function check(ok){if(done)return;total++;const ms=$('#ms');
 if(ok){done=true;streak++;const g=Math.max(1,3-tries);score+=g*10;sfx.ok();lvl++;ms.className='msg ok pop';ms.textContent='Harika! '+'⭐'.repeat(g)+(streak>2?'  🔥 seri '+streak:'');setTimeout(()=>{if(lvl>=12)end();else next()},1100)}
 else{tries++;streak=0;sfx.bad();ms.className='msg bad shake';ms.textContent=L.kind==='cut'&&parts!==L.d?'Önce parça sayısı '+L.d+' olmalı (payda).':'Tekrar dene!'}}
function end(){app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🎉 Tüm seviyeler bitti!'),h('div',{class:'msg'},'Toplam puan: '+score),h('button',{class:'btn',onclick:menu},'Tekrar oyna')));window.__won=true}
menu();
</script></body></html>
'''

ARCADE_HTML['cebir'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.eq{display:flex;align-items:center;justify-content:center;gap:14px;font-size:clamp(26px,5vw,44px);font-weight:900;margin:8px 0}
.side{min-width:140px;min-height:84px;border:3px dashed var(--line);border-radius:20px;padding:8px 14px;display:flex;gap:8px;align-items:center;justify-content:center;flex-wrap:wrap;background:rgba(255,255,255,.05)}
.t{padding:6px 14px;border-radius:14px;background:#0f766e;border:2px solid #5eead4}
.t.x{background:linear-gradient(135deg,#a855f7,#6366f1);border-color:#c4b5fd}
.t.n{background:#b45309;border-color:#fcd34d}
.ops .btn{min-width:64px}
</style></head><body><div id="app"></div><script>
const app=$('#app');
let E,moves,opt,lvl=0,score=0,hist=[],maxL=10,done=false,opKind='+',useX;
// denklem: a*x + b = c*x + d
function gen(l){let a=1,b=0,c=0,d,x=rnd(1,9);
 if(l<2){b=rnd(1,9);d=x+b}
 else if(l<4){a=rnd(2,5);d=a*x}
 else if(l<6){a=rnd(2,5);b=rnd(1,9);d=a*x+b}
 else if(l<8){a=rnd(2,6);c=rnd(1,a-1);b=rnd(1,9);d=(a-c)*x+b;a=a;[b,d]=[b,d];}
 else{b=-rnd(1,9);a=rnd(2,5);d=a*x+b;if(Math.random()<.5){c=rnd(1,a-1);d=(a-c)*x+b}}
 if(l>=6&&l<8){/* a x + b = c x + d  ->  (a-c)x = d-b ; yeniden kur */const e=(a-c)*x;d=e+b}
 return{a,b,c,d,x}}
function fmt(a,b,isLeft){let t=[];if(a)t.push(h('span',{class:'t x'},(a===1?'':a)+(useX?'x':'🐉')));if(b!==0||!a)t.push(h('span',{class:'t n'},(b>0&&a?'+':'')+b));return t}
function side(a,b){const e=h('div',{class:'side'});const parts=[];if(a)parts.push(h('span',{class:'t x'},(a===1?'':a===-1?'−':a)+(useX?'x':'🐉')));if(b!==0||!a)parts.push(h('span',{class:'t n'},(b>0&&a?'+ '+b:b<0&&a?'− '+(-b):b)));e.append(...parts);return e}
function solved(){return(E.a===1&&E.b===0&&E.c===0)}
function start(l){lvl=l;useX=l>=4;E=gen(l);hist=[];moves=0;done=false;opt=plan(E);view()}
function plan(e){let n=0,{a,b,c,d}=e;if(c){n++;a-=c;c=0}if(b){n++;d-=b;b=0}if(a!==1)n++;return n}
function view(){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},'🐉 Ejderha Cebir'),h('span',{class:'sp'}),h('span',{class:'chip'},'Seviye '+(lvl+1)+'/'+maxL),h('span',{class:'chip'},'Hamle '+moves+' (en iyi '+opt+')'),h('button',{class:'btn alt',onclick:menu},'☰')));
 const c=h('div',{class:'center'});app.append(c);
 c.append(h('div',{class:'msg'},useX?'x yalnız kalsın (x = sayı). İki tarafa da aynı işlemi uygula.':'🐉 ejderha (bilinmeyen) tek başına kalsın! Her işlem iki tarafa da uygulanır.'),
 h('div',{class:'eq'},side(E.a,E.b),'=',side(E.c,E.d)));
 const ops=h('div',{class:'row'},['+','−','×','÷'].map(o=>h('button',{class:'btn '+(o===opKind?'':'alt'),onclick:()=>{opKind=o;view()}},o)));
 c.append(ops);
 const nums=new Set();[E.b,E.d,E.a,E.c].forEach(v=>{if(v)nums.add(Math.abs(v))});
 if(opKind==='+'||opKind==='−'){const xs=E.c?['x terimi ('+E.c+(useX?'x':'🐉')+')']:[];}
 const pal=h('div',{class:'row ops'});
 if(opKind==='+'||opKind==='−'){[...nums].sort((x,y)=>x-y).forEach(n=>pal.append(h('button',{class:'btn',onclick:()=>apply(opKind,n)},opKind+n)));
  if(E.c)pal.append(h('button',{class:'btn',onclick:()=>applyX(opKind)},opKind+E.c+(useX?'x':'🐉')),h('button',{class:'btn',onclick:()=>applyX(opKind,E.a)},opKind+E.a+(useX?'x':'🐉')))}
 else{const ns=new Set();[E.a,E.b,E.d,E.c,2,3].forEach(v=>{if(v&&Math.abs(v)>1&&Math.abs(v)<=12)ns.add(Math.abs(v))});[...ns].sort((x,y)=>x-y).forEach(n=>pal.append(h('button',{class:'btn',onclick:()=>apply(opKind,n)},opKind+n)))}
 c.append(pal,h('div',{class:'msg',id:'ms'},''),h('div',{class:'row'},h('button',{class:'btn alt',onclick:undo},'↩ Geri al'),h('button',{class:'btn alt',onclick:()=>start(lvl)},'🔄 Yeniden')))}
function applyX(o,k){const n=k===undefined?E.c:k;const e={...E};const s=o==='+'?1:-1;e.a+=s*n;e.c+=s*n;commit(e)}
function apply(o,n){const e={...E};
 if(o==='+'||o==='−'){const s=o==='+'?n:-n;e.b+=s;e.d+=s}
 else if(o==='×'){e.a*=n;e.b*=n;e.c*=n;e.d*=n}
 else{for(const v of[e.a,e.b,e.c,e.d])if(v%n!==0)return msg('Bu bölme sayıları kesirli yapar; başka işlem dene.',1);e.a/=n;e.b/=n;e.c/=n;e.d/=n}
 commit(e)}
function msg(t,bad){const m=$('#ms');m.textContent=t;m.className='msg '+(bad?'bad shake':'ok')}
function commit(e){if(Math.abs(e.a)>60||Math.abs(e.d)>400||Math.abs(e.b)>400)return msg('Sayılar çok büyüdü.',1);hist.push(E);E=e;moves++;sfx.tap();
 if(E.a===0&&E.c===0)return undo(),msg('Ejderha kayboldu! Geri alındı.',1);
 if(E.a<E.c&&E.c){/* x sağda biriksin: tarafları çevir */const t={a:E.c,b:E.d,c:E.a,d:E.b};E=t}
 if(solved()){done=true;sfx.win();const stars=moves<=opt?3:moves<=opt+2?2:1;score+=stars;view();
  $('#ms').className='msg ok pop';$('#ms').textContent=(useX?'x':'🐉')+' = '+E.d+'  '+'⭐'.repeat(stars)+'  ';
  const nb=h('button',{class:'btn',onclick:()=>{if(lvl+1>=maxL)end();else start(lvl+1)}},lvl+1>=maxL?'Bitir':'Sonraki seviye ▶');$('#ms').after(nb);window.__solved=true;return}
 view()}
function undo(){if(done||!hist.length)return;E=hist.pop();moves=Math.max(0,moves-1);view()}
function end(){app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🐉 Cebir ustası!'),h('div',{class:'msg'},'Toplam yıldız: '+score),h('button',{class:'btn',onclick:menu},'Başa dön')));window.__won=true}
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'🐉 Ejderha Cebir'),h('div',{class:'msg'},'Denklem çözmeyi oyun gibi öğren: ejderhayı (x) yalnız bırak. Bir tarafa yaptığını diğer tarafa da yap!'),h('button',{class:'btn',onclick:()=>{score=0;start(0)}},'Başla')))}
menu();
</script></body></html>
'''

ARCADE_HTML['canavar'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.rod{display:flex;flex-direction:column;align-items:center;gap:3px;padding:8px 10px;border-radius:14px;background:rgba(255,255,255,.08);border:2px solid var(--line);cursor:pointer;min-width:58px}
.rod .u{display:flex;flex-direction:column;gap:2px}
.rod .u i{display:block;width:26px;height:12px;border-radius:4px}
.rod b{font-size:18px}
.mon{width:min(92%,430px);border-radius:28px;border:4px solid var(--ac);background:rgba(45,212,191,.12);padding:14px;text-align:center}
.mon .face{font-size:64px;line-height:1}
.frame{display:grid;grid-template-columns:repeat(5,28px);gap:4px;justify-content:center;margin:8px 0}
.frame span{width:28px;height:28px;border-radius:50%;background:rgba(255,255,255,.12)}
.frame span.f{background:var(--gold)}
.tray{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;align-items:flex-end}
.dots{display:grid;grid-template-columns:repeat(5,18px);gap:3px;padding:6px}
.dots i{width:18px;height:18px;border-radius:50%;background:#fb7185}
</style></head><body><div id="app"></div><script>
const app=$('#app');const CLR=['#f87171','#fb923c','#facc15','#4ade80','#2dd4bf','#38bdf8','#818cf8','#c084fc','#f472b6','#94a3b8'];
let tgt,tray,got,lvl=0,score=0,moves,mode,cmp,done,msgT='',nextId=1;
function rod(v){return{id:nextId++,v}}
function newRound(){done=false;moves=0;mode=lvl%4===3?'cmp':'fill';
 if(mode==='cmp'){const a=rnd(2,10+Math.min(lvl,6)),b=rnd(2,10+Math.min(lvl,6));cmp={a,b:a===b?a+1:b}}
 else{const hi=Math.min(10,5+Math.floor(lvl/2)+1);tgt=rnd(4,hi+Math.floor(lvl/3));if(tgt>20)tgt=20;got=0;
  // havuz: toplam >= tgt, bazıları büyük (bölme gerektirir)
  tray=[];let sum=0;while(sum<tgt||tray.length<3){const v=rnd(1,Math.min(10,tgt+2));tray.push(rod(v));sum+=v;if(tray.length>6)break}
  if(sum<tgt)tray.push(rod(tgt-sum))}
 view()}
function dots(n){const d=h('div',{class:'dots'});for(let i=0;i<n;i++)d.append(h('i'));return d}
function head(){return h('div',{class:'top'},h('h2',{},'👾 Sayı Canavarları'),h('span',{class:'sp'}),h('span',{class:'chip'},'Tur '+(lvl+1)+'/12'),h('span',{class:'chip'},'⭐ '+score),h('button',{class:'btn alt',onclick:menu},'☰'))}
function rodEl(r,click){const u=h('div',{class:'u'});for(let i=0;i<r.v;i++)u.append(h('i',{style:'background:'+CLR[r.v-1]}));return h('div',{class:'rod',onclick:click},h('b',{},r.v),u)}
function view(){app.innerHTML='';app.append(head());const c=h('div',{class:'center'});app.append(c);
 if(mode==='cmp'){c.append(h('div',{class:'msg'},'Hangi canavarın daha çok yemeği var?'),h('div',{class:'row'},[['a',cmp.a],['b',cmp.b]].map(([k,v])=>h('div',{class:'mon',style:'width:230px;cursor:pointer',onclick:()=>cmpPick(v>(k==='a'?cmp.b:cmp.a))},h('div',{class:'face'},k==='a'?'👾':'👹'),dots(v)))),h('div',{class:'msg',id:'ms'},''));return}
 const fr=h('div',{class:'frame'});for(let i=0;i<Math.max(10,Math.ceil(tgt/5)*5);i++)fr.append(h('span',{class:i<got?'f':'',style:i>=tgt?'opacity:.25':''}));
 c.append(h('div',{class:'mon'},h('div',{class:'face'},got===tgt?'😋':'👾'),h('div',{class:'big'},got+' / '+tgt),fr),
  h('div',{class:'msg'},'Canavar tam '+tgt+' yemek istiyor! Çubuğa dokun; fazlaysa çubuk otomatik bölünür.'),
  h('div',{class:'tray'},tray.map(r=>rodEl(r,()=>feed(r)))),h('div',{class:'msg '+msgT,id:'ms'},''),h('div',{class:'row'},h('button',{class:'btn alt',onclick:()=>{newRound()}},'🔄 Yeni')))}
function feed(r){if(done)return;const need=tgt-got;sfx.tap();moves++;
 if(r.v<=need){got+=r.v;tray=tray.filter(x=>x!==r)}
 else{got+=need;const rest=r.v-need;tray=tray.filter(x=>x!==r);tray.push(rod(rest));msgT='ok';setTimeout(()=>{const m=$('#ms');if(m)m.textContent='✂️ '+r.v+' = '+need+' + '+rest},0)}
 if(got===tgt){done=true;sfx.ok();score+=moves<=3?3:moves<=5?2:1;lvl++;view();$('#ms').className='msg ok pop';$('#ms').textContent='Tıka basa doydu! 🎉';setTimeout(()=>{if(lvl>=12)end();else newRound()},1100)}else view()}
function cmpPick(ok){if(done)return;if(ok){done=true;sfx.ok();score+=2;lvl++;$('#ms').className='msg ok pop';$('#ms').textContent='Doğru! '+cmp.a+' ve '+cmp.b;setTimeout(()=>{if(lvl>=12)end();else newRound()},1000)}else{sfx.bad();$('#ms').className='msg bad shake';$('#ms').textContent='Dikkatle say!'}}
function end(){app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🎉 Canavarlar doydu!'),h('div',{class:'msg'},'Puan: '+score),h('button',{class:'btn',onclick:menu},'Tekrar')));window.__won=true}
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'👾 Sayı Canavarları'),h('div',{class:'msg'},'Sayı çubuklarıyla canavarları doyur. Sayıları parçala, birleştir ve karşılaştır!'),h('button',{class:'btn',onclick:()=>{lvl=0;score=0;newRound()}},'Başla')))}
menu();
</script></body></html>
'''

ARCADE_HTML['buyuk'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.cols{display:grid;gap:8px;justify-content:center;margin:6px 0}
.pl{background:rgba(255,255,255,.07);border:2px solid var(--line);border-radius:14px;padding:6px 4px;text-align:center;min-width:92px}
.pl h4{margin:0 0 4px;font-size:13px;color:var(--mut)}
.blk{display:flex;flex-wrap:wrap;gap:3px;justify-content:center;min-height:56px;align-content:flex-start}
.blk i{width:16px;height:16px;border-radius:4px;display:block}
.pl .n{font-size:26px;font-weight:900}
.pl.warn{border-color:var(--gold);background:rgba(251,191,36,.12)}
.mini{padding:5px 8px;font-size:12px;border-radius:10px;box-shadow:0 2px 0 #0f766e}
.words{font-size:clamp(18px,3.5vw,28px);font-weight:800;color:var(--gold)}
.eqn{font-size:clamp(24px,5vw,40px);font-weight:900}
</style></head><body><div id="app"></div><script>
const app=$('#app');const PN=['Birler','Onlar','Yüzler','Binler','On Binler','Yüz Binler'],PC=['#94a3b8','#38bdf8','#4ade80','#fbbf24','#fb7185','#c084fc'];
const O=['','bir','iki','üç','dört','beş','altı','yedi','sekiz','dokuz'],T=['','on','yirmi','otuz','kırk','elli','altmış','yetmiş','seksen','doksan'];
function words(n){if(n===0)return'sıfır';const g=x=>{let s='';const y=Math.floor(x/100),r=x%100;if(y)s+=(y>1?O[y]+' ':'')+'yüz ';if(r)s+=T[Math.floor(r/10)]+(r%10?' '+O[r%10]:'');return s.trim()};
 const b=Math.floor(n/1000),r=n%1000;let s='';if(b)s+=(b===1?'':g(b)+' ')+'bin ';if(r)s+=g(r);return s.replace(/\s+/g,' ').trim()}
let mode,A,B,cnt,sub,target,lvl=0,score=0,done,moves,P=4;
function digs(n,k){const d=[];for(let i=0;i<k;i++){d.push(n%10);n=Math.floor(n/10)}return d}
const val=d=>d.reduce((s,x,i)=>s+x*10**i,0);
function newRound(){done=false;moves=0;P=Math.min(6,3+Math.floor(lvl/3));const k=lvl%3;mode=['add','sub','build'][k];
 if(mode==='add'){do{A=rnd(10**(P-2),10**P-1-10**(P-2));B=rnd(10**(P-2),10**P-1-10**(P-2))}while(A+B>=10**P||!carries(A,B));cnt=digs(A,P).map((x,i)=>x+digs(B,P)[i]);target=A+B;sub=null}
 else if(mode==='sub'){do{A=rnd(10**(P-1),10**P-1);B=rnd(10**(P-2),A-1)}while(!borrows(A,B));cnt=digs(A,P);sub=digs(B,P);target=A-B}
 else{target=rnd(10**(P-1),10**P-1);cnt=new Array(P).fill(0);sub=null}
 view()}
function carries(a,b){const x=digs(a,7),y=digs(b,7);return x.some((v,i)=>v+y[i]>=10)}
function borrows(a,b){const x=digs(a,7),y=digs(b,7);return x.some((v,i)=>v<y[i])}
function hiNZ(i){for(let j=i+1;j<P;j++)if(cnt[j]>0)return j;return 0}
function borrow(i){const j=hiNZ(i);if(!j)return false;cnt[j]--;for(let k=j-1;k>i;k--)cnt[k]+=9;cnt[i]+=10;return true}
function pl(i){const c=cnt[i],e=h('div',{class:'pl'+(mode==='add'&&c>=10?' warn':'')+(mode==='sub'&&sub[i]>c?' warn':'')});e.append(h('h4',{},PN[i]),h('div',{class:'blk'},Array.from({length:Math.min(c,60)},()=>h('i',{style:'background:'+PC[i]}))),h('div',{class:'n'},c+(mode==='sub'?' − '+sub[i]:'')));
 const bt=h('div',{class:'row'});
 if(mode==='add'&&c>=10&&i<P-1)bt.append(h('button',{class:'btn mini',onclick:()=>{cnt[i]-=10;cnt[i+1]++;moves++;sfx.ok();view()}},'10 → 1 '+['onluk','yüzlük','binlik','on binlik','yüz binlik'][i]));
 if(mode==='sub'&&sub[i]>c&&hiNZ(i)>0)bt.append(h('button',{class:'btn mini',onclick:()=>{borrow(i);moves++;sfx.ok();view()}},'1 aç → 10'));
 if(mode==='build'){bt.append(h('button',{class:'btn mini alt',onclick:()=>{if(cnt[i]>0){cnt[i]--;sfx.tap();view()}}},'−'),h('button',{class:'btn mini',onclick:()=>{if(cnt[i]<9){cnt[i]++;sfx.tap();view()}}},'+'))}
 e.append(bt);return e}
function view(){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},'🔟 Büyük Sayılar'),h('span',{class:'sp'}),h('span',{class:'chip'},'Tur '+(lvl+1)+'/9'),h('span',{class:'chip'},'⭐ '+score),h('button',{class:'btn alt',onclick:menu},'☰')));
 const c=h('div',{class:'center'});app.append(c);
 if(mode==='add')c.append(h('div',{class:'eqn'},A.toLocaleString('tr-TR')+' + '+B.toLocaleString('tr-TR')+' = ?'),h('div',{class:'msg'},'Basamakları topladık. 10 veya daha fazla olan basamakta 10 tanesini bir üst basamağa çevir.'));
 else if(mode==='sub')c.append(h('div',{class:'eqn'},A.toLocaleString('tr-TR')+' − '+B.toLocaleString('tr-TR')+' = ?'),h('div',{class:'msg'},'Çıkarılacak sayı büyükse bir üst basamaktan 1 aç. Sonra "Çıkar" a bas.'));
 else c.append(h('div',{class:'words'},words(target)),h('div',{class:'msg'},'Okunuşu verilen sayıyı basamak bloklarıyla oluştur.'));
 const g=h('div',{class:'cols',style:`grid-template-columns:repeat(${P},minmax(86px,1fr));width:min(100%,${P*110}px)`});for(let i=P-1;i>=0;i--)g.append(pl(i));c.append(g);
 const cur=mode==='sub'?val(cnt):val(cnt);
 if(mode==='add')c.append(h('div',{class:'eqn'},'= '+(cnt.every(x=>x<10)?val(cnt).toLocaleString('tr-TR'):'…')),h('button',{class:'btn',disabled:!cnt.every(x=>x<10),onclick:()=>fin(val(cnt)===target)},'Tamam ✓'));
 else if(mode==='sub')c.append(h('button',{class:'btn',disabled:!cnt.every((x,i)=>x>=sub[i]),onclick:()=>fin(val(cnt.map((x,i)=>x-sub[i]))===target)},'Çıkar ✓'));
 else c.append(h('div',{class:'eqn'},val(cnt).toLocaleString('tr-TR')),h('button',{class:'btn',onclick:()=>fin(val(cnt)===target)},'Kontrol ✓'));
 c.append(h('div',{class:'msg',id:'ms'},''))}
function fin(ok){if(done)return;const m=$('#ms');if(ok){done=true;sfx.win();score+=moves<=P+2?3:2;lvl++;m.className='msg ok pop';m.textContent='Süper! Sonuç: '+target.toLocaleString('tr-TR')+' — '+words(target);setTimeout(()=>{if(lvl>=9)end();else newRound()},1700)}else{sfx.bad();m.className='msg bad shake';m.textContent='Tam tutmadı, bir daha bak.'}}
function end(){app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🎉 Büyük sayılar fethedildi!'),h('div',{class:'msg'},'Puan: '+score),h('button',{class:'btn',onclick:menu},'Tekrar')));window.__won=true}
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'🔟 Büyük Sayılar'),h('div',{class:'msg'},'Basamak bloklarıyla toplama, çıkarma ve sayı okuma. Eldeli toplama ve onluk bozmayı görerek öğren!'),h('button',{class:'btn',onclick:()=>{lvl=0;score=0;newRound()}},'Başla')))}
menu();
</script></body></html>
'''

ARCADE_HTML['zihin'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.cell{width:84px;height:84px;border-radius:18px;background:rgba(255,255,255,.1);border:2px solid var(--line);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:900;transition:.12s}
.cell.lit{background:var(--ac);transform:scale(1.08);box-shadow:0 0 22px var(--ac)}
.gridm{display:grid;gap:10px;justify-content:center}
.cat{width:200px;padding:14px;border-radius:20px;background:rgba(255,255,255,.07);border:2px solid var(--line);cursor:pointer;text-align:center}
.cat:hover{border-color:var(--ac)}.cat b{display:block;font-size:20px}.cat span{font-size:13px;color:var(--mut)}
.tbar{height:8px;border-radius:99px;background:rgba(255,255,255,.12);overflow:hidden;width:min(90%,520px)}
.tbar i{display:block;height:100%;background:linear-gradient(90deg,#2dd4bf,#22d3ee);transition:width .2s linear}
.word{font-size:clamp(40px,10vw,84px);font-weight:900}
</style></head><body><div id="app"></div><script>
const app=$('#app');
const CATS=[['mem','🧠','Hafıza','Işık dizisini hatırla'],['att','🎯','Dikkat','Renk–kelime çatışması'],['spd','⚡','Hız','Hızlı doğru/yanlış işlem'],['log','🧩','Mantık','Sayı örüntüsü'],['lan','🔤','Dil','Karışık harfleri düzelt'],['vis','👁️','Görsel','Farklı olanı bul']];
let sc=store('scores')||{},cur,round,pts,tEnd,tmr;
function menu(){clearInterval(tmr);app.innerHTML='';
 const tot=CATS.reduce((a,c)=>a+(sc[c[0]]||0),0);
 app.append(h('div',{class:'top'},h('h2',{},'🧠 Zihin Antrenmanı'),h('span',{class:'sp'}),h('span',{class:'chip'},'Zihin puanı: '+tot)),h('div',{class:'msg'},'Her oyun 45 saniye. En iyi skorların beyin haritanı doldurur!'));
 const g=h('div',{class:'row'},CATS.map(c=>h('div',{class:'cat',onclick:()=>begin(c[0])},h('div',{style:'font-size:38px'},c[1]),h('b',{},c[2]),h('span',{},c[3]),h('div',{class:'chip',style:'margin-top:8px;display:inline-block'},'En iyi: '+(sc[c[0]]||0)))));
 app.append(g,radar())}
function radar(){const n=CATS.length,R=110,cx=140,cy=130;const mx=Math.max(100,...CATS.map(c=>sc[c[0]]||0));
 const pt=(i,v)=>{const a=-Math.PI/2+i*2*Math.PI/n;return[cx+Math.cos(a)*R*v,cy+Math.sin(a)*R*v]};
 let s=`<svg viewBox="0 0 280 260" width="280" height="260" style="margin:auto;display:block">`;
 for(const k of[.33,.66,1])s+=`<polygon points="${CATS.map((c,i)=>pt(i,k).join(',')).join(' ')}" fill="none" stroke="rgba(94,234,212,.3)"/>`;
 s+=`<polygon points="${CATS.map((c,i)=>pt(i,(sc[c[0]]||0)/mx).join(',')).join(' ')}" fill="rgba(45,212,191,.45)" stroke="#2dd4bf" stroke-width="2"/>`;
 CATS.forEach((c,i)=>{const[x,y]=pt(i,1.18);s+=`<text x="${x}" y="${y}" fill="#e6fffb" font-size="12" text-anchor="middle" dominant-baseline="middle">${c[1]} ${c[2]}</text>`});
 return h('div',{html:s+'</svg>'})}
function begin(k){cur=k;pts=0;round=0;tEnd=Date.now()+45000;clearInterval(tmr);tmr=setInterval(()=>{const r=Math.max(0,tEnd-Date.now());const b=$('#tb');if(b)b.style.width=(r/450)+'%';if(r<=0&&!(cur==='mem'&&memBusy))finish()},150);
 app.innerHTML='';GAME[k]()}
function frame(title,body){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},title),h('span',{class:'sp'}),h('span',{class:'chip',id:'pt'},'Puan '+pts),h('button',{class:'btn alt',onclick:menu},'☰')),h('div',{class:'center',style:'gap:14px'},h('div',{class:'tbar'},h('i',{id:'tb',style:'width:'+Math.max(0,(tEnd-Date.now())/450)+'%'})),body,h('div',{class:'msg',id:'ms'},'')))}
function add(n,ok){pts=Math.max(0,pts+n);const p=$('#pt');if(p)p.textContent='Puan '+pts;ok?sfx.ok():sfx.bad();const m=$('#ms');if(m){m.className='msg '+(ok?'ok':'bad');m.textContent=ok?'✓':'✗'}}
function finish(){clearInterval(tmr);const best=Math.max(sc[cur]||0,pts);const isNew=best>(sc[cur]||0);sc[cur]=best;store('scores',sc);sfx.win();
 app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'⏱ Süre doldu!'),h('div',{class:'msg'},'Puan: '+pts+(isNew?'  🏅 Yeni rekor!':'')),h('div',{class:'row'},h('button',{class:'btn',onclick:()=>begin(cur)},'Tekrar'),h('button',{class:'btn alt',onclick:menu},'Menü'))));window.__fin=pts}
let memBusy=false;
const GAME={
 async mem(){let seq=[],len=2;const size=3;const lit=i=>{const e=$('#c'+i);if(e){e.classList.add('lit');setTimeout(()=>e.classList.remove('lit'),380)}};
  const cells=[];const g=h('div',{class:'gridm',style:`grid-template-columns:repeat(${size},84px)`});for(let i=0;i<9;i++)g.append(h('div',{class:'cell',id:'c'+i,onclick:()=>tap(i)},''));frame('🧠 Hafıza',g);
  let inp=[],accept=false;
  async function show(){memBusy=true;accept=false;inp=[];seq=Array.from({length:len},()=>rnd(0,8));$('#ms').textContent='İzle…';await sleep(500);for(const i of seq){lit(i);sfx.tap();await sleep(650)}memBusy=false;accept=true;if($('#ms'))$('#ms').textContent='Sıra sende';if(Date.now()>tEnd)finish()}
  function tap(i){if(!accept)return;lit(i);inp.push(i);const k=inp.length-1;if(seq[k]!==i){accept=false;add(0,false);len=Math.max(2,len-1);setTimeout(()=>{if(Date.now()<tEnd)show();else finish()},700);return}
   if(inp.length===seq.length){accept=false;add(seq.length*5,true);len++;setTimeout(()=>{if(Date.now()<tEnd)show();else finish()},700)}}
  window.__memSeq=()=>seq;window.__memTap=tap;show()},
 att(){const W=[['KIRMIZI','#ef4444'],['MAVİ','#3b82f6'],['YEŞİL','#22c55e'],['SARI','#eab308']];let ans;
  function nx(){const w=pick(W),c=Math.random()<.5?w:pick(W);ans=c[0];const body=h('div',{class:'center'},h('div',{class:'msg'},'Kelimenin ANLAMINA değil RENGİNE bak!'),h('div',{class:'word',style:'color:'+c[1]},w[0]),h('div',{class:'row'},W.map(x=>h('button',{class:'btn',style:'background:'+x[1]+';color:#fff',onclick:()=>{const ok=x[0]===ans;add(ok?10:-5,ok);nx()}},x[0]))));frame('🎯 Dikkat',body);window.__ans=()=>ans}nx()},
 spd(){function nx(){const a=rnd(3,19),b=rnd(2,12),op=pick(['+','−','×']);const r=op==='+'?a+b:op==='−'?a-b:a*b;const shown=Math.random()<.5?r:r+pick([-2,-1,1,2,10]);const ok=shown===r;
  frame('⚡ Hız',h('div',{class:'center'},h('div',{class:'big'},`${a} ${op} ${b} = ${shown}`),h('div',{class:'row'},h('button',{class:'btn',onclick:()=>{add(ok?8:-5,ok);nx()}},'✓ Doğru'),h('button',{class:'btn bad',onclick:()=>{add(!ok?8:-5,!ok);nx()}},'✗ Yanlış'))));window.__ok=ok}nx()},
 log(){function nx(){const t=rnd(0,3);let s=[],a=rnd(1,9),d=rnd(2,6),r=rnd(2,3),ans;
  if(t===0){s=[0,1,2,3].map(i=>a+d*i);ans=a+d*4}else if(t===1){s=[0,1,2,3].map(i=>a*r**i);ans=a*r**4}else if(t===2){s=[0,1,2,3].map(i=>(i+1)**2+a);ans=25+a}else{s=[a,d];for(let i=2;i<5;i++)s.push(s[i-1]+s[i-2]);ans=s[3]+s[4-0-1+0]-0;ans=s[4-1]+s[4-2];s=s.slice(0,4);ans=s[3]+s[2]}
  const o=shuf([...new Set([ans,ans+rnd(1,4),ans-rnd(1,4),ans+rnd(5,9)])].filter(x=>x>0));
  frame('🧩 Mantık',h('div',{class:'center'},h('div',{class:'big'},s.join(' , ')+' , ?'),h('div',{class:'row'},o.map(v=>h('button',{class:'btn',onclick:()=>{const ok=v===ans;add(ok?12:-4,ok);nx()}},v)))));window.__ans=ans}nx()},
 lan(){const WL=['OKUL','KİTAP','KALEM','DEFTER','ÖĞRETMEN','SINIF','BİLGİ','MATEMATİK','TÜRKİYE','ÇİÇEK','GÜNEŞ','DENİZ','ORMAN','HARİTA','ATLAS','MİKROSKOP','HÜCRE','KESİR','ÜÇGEN','ENERJİ','MADDE','İKLİM','CUMHURİYET','ÖZGÜRLÜK','KÜTÜPHANE'];let w;
  function nx(){w=pick(WL);let sh;do{sh=shuf([...w]).join('')}while(sh===w);let g=[];
   const t=h('div',{class:'center'},h('div',{class:'big'},sh),h('div',{class:'chip',id:'gs',style:'min-height:30px;font-size:22px'},''),h('div',{class:'row'},[...sh].map((ch,i)=>h('button',{class:'btn',id:'L'+i,onclick:e=>{g.push(ch);e.target.disabled=true;sfx.tap();$('#gs').textContent=g.join('');if(g.length===w.length){const ok=g.join('')===w;add(ok?w.length*2:-5,ok);setTimeout(nx,300)}}},ch))),h('button',{class:'btn alt',onclick:nx},'Geç'));
   frame('🔤 Dil',t);window.__word=w}nx()},
 vis(){let n=3;function nx(){n=Math.min(6,3+Math.floor(pts/60));const A=pick(['●','■','▲','◆','★','♥']);let B;do{B=pick(['●','■','▲','◆','★','♥'])}while(B===A);const idx=rnd(0,n*n-1);const hue=rnd(0,360);
   const g=h('div',{class:'gridm',style:`grid-template-columns:repeat(${n},64px)`});for(let i=0;i<n*n;i++)g.append(h('div',{class:'cell',style:`width:64px;height:64px;color:hsl(${hue},80%,65%)`,onclick:()=>{const ok=i===idx;add(ok?9:-5,ok);nx()}},i===idx?B:A));
   frame('👁️ Görsel',h('div',{class:'center'},h('div',{class:'msg'},'Farklı olan şekli bul!'),g));window.__odd=idx}nx()}};
menu();
</script></body></html>
'''

ARCADES = [('uno', '🃏', 'UNO', 'linear-gradient(135deg, #ef4444, #f59e0b)', 'Robot rakiplere karşı kart savaşı'), ('sudoku', '🔢', 'Sudoku', 'linear-gradient(135deg, #0ea5e9, #6366f1)', '4×4, 6×6, 9×9 mantık bulmacası'), ('satranc', '♞', 'Satranç', 'linear-gradient(135deg, #334155, #0f766e)', 'Yapay zekâya karşı tam kurallı'), ('kelimeler', '🔤', 'Kelime Bulmacaları', 'linear-gradient(135deg, #f97316, #db2777)', 'Kelime avı, çapraz bulmaca, eksik harf'), ('macera', '🧭', 'İnteraktif Macera', 'linear-gradient(135deg, #0d9488, #4f46e5)', 'Seçimlerinle hikâyeyi yönlendir'), ('kultur', '🗺️', 'Kültür & Coğrafya Puzzle', 'linear-gradient(135deg, #ca8a04, #dc2626)', 'Gerçek fotoğraflarla dünya harikaları'), ('cark', '🎡', 'Bilgi Çarkı', 'linear-gradient(135deg, #8b5cf6, #ec4899)', 'Çarkı çevir, soruyu bil'), ('sirala', '⏳', 'Zaman Şeridi & Sırala', 'linear-gradient(135deg, #0891b2, #2563eb)', 'Olayları ve sayıları doğru sıraya diz'), ('sinema', '🤫', 'Sessiz Sinema', 'linear-gradient(135deg, #f43f5e, #9333ea)', 'Mimikle anlat, takımın bilsin'), ('kesir', '🍫', 'Kesir Dilimleme', 'linear-gradient(135deg, #f59e0b, #b45309)', 'Kes, böl, karşılaştır, topla'), ('cebir', '🐉', 'Ejderha Cebir', 'linear-gradient(135deg, #a855f7, #6366f1)', 'Denklemi oyunla çöz'), ('canavar', '👾', 'Sayı Canavarları', 'linear-gradient(135deg, #22c55e, #0d9488)', 'Sayı çubuklarıyla doyur'), ('buyuk', '🔟', 'Büyük Sayılar', 'linear-gradient(135deg, #ec4899, #8b5cf6)', 'Basamak blokları, eldeli işlem'), ('zihin', '🧠', 'Zihin Antrenmanı', 'linear-gradient(135deg, #14b8a6, #06b6d4)', 'Hafıza, dikkat, hız, mantık')]
