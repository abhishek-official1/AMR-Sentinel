// Optional real-browser QA. Use a dedicated headless browser with a CDP endpoint;
// this creates/closes only its own tab and never controls an existing user tab.
import {mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const cdp=process.env.CDP_URL||'http://127.0.0.1:9222';
const base=process.env.AMR_BASE_URL||'http://127.0.0.1:8000';
await mkdir('.browser-artifacts',{recursive:true});
let target;
try{const response=await fetch(`${cdp}/json/new?${encodeURIComponent(base)}`,{method:'PUT'});if(!response.ok)throw Error('No CDP tab could be created');target=await response.json();}
catch(error){throw Error(`Browser QA unavailable. Start a dedicated headless Chrome/Edge with remote debugging, then set CDP_URL. ${error.message}`);}
const socket=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
let id=0;const pending=new Map(),errors=[];
socket.onmessage=event=>{const data=JSON.parse(event.data);if(data.id){const task=pending.get(data.id);if(task){pending.delete(data.id);data.error?task.reject(Error(data.error.message)):task.resolve(data.result);}}if(data.method==='Runtime.exceptionThrown')errors.push(data.params.exceptionDetails.text);};
function send(method,params={}){return new Promise((resolve,reject)=>{const next=++id;pending.set(next,{resolve,reject});socket.send(JSON.stringify({id:next,method,params}));});}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value;}
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function waitFor(expression){for(let i=0;i<50;i++){if(await evaluate(expression))return;await delay(100);}throw Error('Timed out waiting for '+expression);}
async function shot(name){const result=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await writeFile(`.browser-artifacts/${name}.png`,Buffer.from(result.data,'base64'));}
try{
  await send('Page.enable');await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:base});
  await waitFor("document.querySelector('.stats-grid') && document.body.textContent.includes('95')");
  // Parameter help must work with the keyboard, pointer, and Escape.
  await evaluate("document.querySelector('.stat-value').focus()");
  await waitFor("document.querySelector('.help-bubble') !== null");
  assert(await evaluate("document.querySelector('.help-bubble').textContent.includes('Distinct reporting countries')"));
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
  await waitFor("document.querySelector('.help-bubble') === null");
  const helpPoint=await evaluate("(()=>{const r=document.querySelector('.stat-value').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()");
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',...helpPoint});
  await waitFor("document.querySelector('.help-bubble') !== null");
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:1400,y:100});
  await waitFor("document.querySelector('.help-bubble') === null");
  assert.equal(await evaluate("document.documentElement.scrollWidth <= innerWidth"),true,'Desktop page must not overflow');
  await shot('overview-desktop');
  for(const page of ['trends','forecasts','evaluation']){
    await evaluate(`document.querySelector('nav a[href="#${page}"]').click()`);
    await waitFor(`document.querySelector('nav a[href="#${page}"]').getAttribute('aria-current') === 'page'`);
    await delay(150);
    await shot(page+'-desktop');
  }
  assert(await evaluate("document.body.textContent.includes('9.61') && document.body.textContent.includes('12.25')"));
  await evaluate("document.querySelector('nav a[href=\"#forecasts\"]').click()");
  await waitFor("document.querySelector('[aria-label=\"Forecast region\"]') !== null");
  await evaluate("(()=>{const s=document.querySelector('[aria-label=\"Forecast region\"]');s.value='AMR';s.dispatchEvent(new Event('change',{bubbles:true}));})()");
  await waitFor("document.body.textContent.includes('Insufficient data to forecast')");
  await evaluate("document.querySelector('nav a[href=\"#overview\"]').click()");
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await delay(200);
  const touchPoint=await evaluate("(()=>{const r=document.querySelector('.stat-value').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()");
  await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[touchPoint]});
  await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await waitFor("document.querySelector('.help-bubble') !== null");
  await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:380,y:110}]});
  await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await waitFor("document.querySelector('.help-bubble') === null");
  assert.equal(await evaluate("document.documentElement.scrollWidth <= innerWidth"),true,'Mobile page must not overflow');
  await shot('overview-mobile');
  await evaluate("document.querySelector('[aria-label=\"Open navigation\"]').click()");
  await waitFor("document.querySelector('.sidebar.open') !== null");
  await evaluate("document.querySelector('nav a[href=\"#evaluation\"]').click()");
  await waitFor("document.querySelector('.evaluation-headline') !== null");
  await shot('evaluation-mobile');
  await evaluate("Array.from(document.querySelectorAll('button')).find(x=>x.textContent.includes('Import study')).click()");
  await waitFor("document.querySelector('dialog[open]') !== null");
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
  await waitFor("document.querySelector('dialog[open]') === null");
  assert.deepEqual(errors,[],'No browser runtime exceptions');
  const response=await fetch(base+'/api/export/forecasts');assert(response.ok);assert((await response.text()).includes('experimental_forecast'));
  console.log('Desktop/mobile browser smoke checks and screenshots passed.');
}finally{socket.close();await fetch(`${cdp}/json/close/${target.id}`).catch(()=>{});}
