import assert from 'node:assert/strict';
import worker, {validEvent} from '../worker/events.mjs';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const body={event:'task_open',page:'home',language:'en',section:'contribution-start',source:'facebook',medium:'paid',campaign:'week1'};
const writes=[];
const env={ACTION_ANALYTICS_ENABLED:'true',EVENTS:{writeDataPoint:point=>writes.push(point)},ASSETS:{fetch:()=>new Response('asset')}};
const make=(value=body,headers={},method='POST')=>new Request('https://djazair.dev/api/events',{method,
 headers:{Origin:'https://djazair.dev','Content-Type':'application/json',...headers},body:method==='POST' ? JSON.stringify(value) : undefined});
assert.equal((await worker.fetch(make(),env)).status,204);
assert.deepEqual(writes[0],{indexes:['week1'],doubles:[1],blobs:['task_open','home','en','contribution-start','facebook','paid','week1']});
for (const bad of [{...body,ip:'1.2.3.4'},{...body,event:'contribution_completed'},{...body,source:'person@example.com'},{...body,campaign:'x'.repeat(65)},[],null]) {
 assert.equal(validEvent(bad),false); assert.equal((await worker.fetch(make(bad),env)).status,400);
}
assert.equal((await worker.fetch(make(body,{Origin:'https://evil.example'}),env)).status,403);
assert.equal((await worker.fetch(make(body,{'Content-Type':'text/plain'}),env)).status,415);
assert.equal((await worker.fetch(make({...body,extra:'x'.repeat(1500)}),env)).status,413);
assert.equal((await worker.fetch(make(body,{},'GET'),env)).status,405);
assert.equal((await worker.fetch(make(),{...env,ACTION_ANALYTICS_ENABLED:'false'})).status,503);
assert.equal((await worker.fetch(make(),{...env,EVENTS:{writeDataPoint:()=>{throw Error('unavailable');}}})).status,503);
assert.equal(await (await worker.fetch(new Request('https://djazair.dev/en/'),env)).text(),'asset');
for (const header of ['DNT','Sec-GPC']) assert.equal((await worker.fetch(make(body,{[header]:'1'}),env)).status,204);
assert.equal(writes.length,1,'private requests and invalid events never reach the dataset');

// Exercise the client using a small DOM fixture, without a browser or third-party modules.
const source=readFileSync(new URL('../site/static/js/actions.js',import.meta.url),'utf8');
function fixture(privateMode=false,search='?utm_source=facebook&utm_medium=paid&utm_campaign=week1&fbclid=private') {
 const sent=[], handlers={};
 const links=[
  ['https://djazair.dev/en/hub/?kind=gfi#issues','/en/hub/?kind=gfi#issues'],
  ['https://founders.coffee/en/algeria/host/create','https://founders.coffee/en/algeria/host/create'],
  ['https://djazair.dev/en/index/','/en/index/'],
  ['https://djazair.dev/en/#main','#main'],
  ['https://github.com/o/r/issues/42','https://github.com/o/r/issues/42']
 ].map(([href,original])=>({href,getAttribute:()=>original,closest:s=>s==='section' ? {id:'local-team',classList:{contains:()=>false}} : null}));
 const share={dataset:{copied:'Copied',failed:'Failed'},parentElement:{hidden:true,querySelector:()=>({})},addEventListener:(e,fn)=>handlers.share=fn};
 const ctx={location:{pathname:'/en/',search,origin:'https://djazair.dev',hostname:'djazair.dev'},navigator:{doNotTrack:privateMode===true ? '1' : '0',globalPrivacyControl:privateMode==='gpc',clipboard:{writeText:async()=>{}}},window:{isSecureContext:true},
 URL,URLSearchParams,Date,console,document:{referrer:'',querySelectorAll:()=>links,querySelector:()=>share,addEventListener:(e,fn)=>handlers[e]=fn},
 fetch:(url,args)=>{assert.equal(url,'/api/events');sent.push(JSON.parse(args.body));return Promise.resolve();}};
 vm.runInNewContext(source,ctx);
 return {sent,links,handlers,share,ctx,click:link=>handlers.click({target:{closest:()=>link}})};
}
const test=fixture();
assert.equal(test.sent[0].event,'landing_view');
assert.equal(new URL(test.links[0].href).hash,'#issues');
assert.equal(new URL(test.links[0].href).searchParams.get('kind'),'gfi');
assert.equal(new URL(test.links[2].href).searchParams.get('utm_campaign'),'week1');
assert.equal(new URL(test.links[3].href).search,'','skip link stays an in-page anchor');
assert.equal(new URL(test.links[4].href).search,'','GitHub never receives attribution parameters');
assert.ok(test.links.every(link=>!link.href.includes('fbclid')));
test.click(test.links[1]); assert.equal(test.sent.at(-1).event,'meetup_host');
await test.handlers.share(); assert.equal(test.sent.at(-1).event,'share_copy');
const cancelled=fixture(); cancelled.ctx.navigator.share=async()=>{throw Object.assign(Error(),{name:'AbortError'});};
await cancelled.handlers.share(); assert.equal(cancelled.sent.at(-1).event,'share_open');
assert.ok(!cancelled.sent.some(row=>row.event==='share_complete'));
const direct=fixture(false,''); assert.equal(new URL(direct.links[0].href).search,'?kind=gfi');
const privateTest=fixture(true); privateTest.click(privateTest.links[1]); await privateTest.handlers.share();
assert.deepEqual(privateTest.sent,[]); assert.equal(new URL(privateTest.links[0].href).search,'?kind=gfi');
console.log('Worker and browser-client behavior passed.');

const hubSource=readFileSync(new URL('../site/static/js/hub.js',import.meta.url),'utf8');
const remember=hubSource.slice(hubSource.indexOf('  function remember(f)'),hubSource.indexOf('  function restore()'));
let remembered='';
const hubLocation={pathname:'/en/hub/',hash:'#issues',search:'?utm_source=facebook&utm_medium=paid&utm_campaign=week1&fbclid=discard'};
const hubHistory={replaceState:(state,title,url)=>{remembered=url;hubLocation.search=new URL(url,'https://djazair.dev').search;}};
const hubContext={URLSearchParams,location:hubLocation,window:{history:hubHistory},history:hubHistory,search:{value:'docs'},names:['lang','repo','age','kind']};
vm.createContext(hubContext);
vm.runInContext(remember+'remember({kind:"gfi"});',hubContext);
assert.equal(new URL(remembered,'https://djazair.dev').searchParams.get('utm_campaign'),'week1');
assert.equal(new URL(remembered,'https://djazair.dev').searchParams.get('q'),'docs');
assert.ok(!remembered.includes('fbclid'));
hubContext.search.value='';
vm.runInContext('remember({});',hubContext);
assert.equal(new URL(remembered,'https://djazair.dev').searchParams.get('utm_campaign'),'week1','clearing filters preserves campaign');
assert.equal(new URL(remembered,'https://djazair.dev').hash,'#issues');
assert.ok(!new URL(remembered,'https://djazair.dev').searchParams.has('kind'));

assert.deepEqual(fixture('gpc').sent,[], 'Global Privacy Control prevents every count');
