export const REGION_NAMES = {AFR:'Africa',AMR:'Americas',EMR:'Eastern Mediterranean',EUR:'Europe',SEAR:'South-East Asia',WPR:'Western Pacific'};
export const REGION_COLORS = {AFR:'#d66a41',AMR:'#b69a52',EMR:'#9c7fa4',EUR:'#6e8ca8',SEAR:'#728d72',WPR:'#53a39f'};
export const MODEL_NAMES = {naive:'Naïve carry-forward',linear:'Linear trend',ridge:'Ridge regression'};
export const numericObservations=rows=>rows.filter(r=>r.resistance_pct!=null&&Number.isFinite(r.resistance_pct));
export const targetMatches=(row,metadata)=>!!row&&row.indicator_code===metadata?.indicator_code&&row.statistic_type===metadata?.statistic_type;
export const statisticLabel=statistic=>statistic==='derived_country_median'?'Derived reporting-country median':'WHO unadjusted regional median';
export const fmt=(n,d=1)=>n==null||!Number.isFinite(Number(n))?'—':Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
export const yearRange=rows=>[Math.min(...rows.map(r=>r.year)),Math.max(...rows.map(r=>r.year))];
export function filterObservations(rows,{indicator,statistic,regions,from=-Infinity,to=Infinity}){
  return rows.filter(r=>r.indicator_code===indicator&&r.statistic_type===statistic&&regions.includes(r.who_region)&&r.year>=from&&r.year<=to);
}
export function segments(rows){
  const out=[];let current=[];
  for(const row of [...rows].sort((a,b)=>a.year-b.year)){
    if(row.resistance_pct==null){if(current.length)out.push(current);current=[];continue;}
    if(current.length&&row.year!==current.at(-1).year+1){out.push(current);current=[];}
    current.push(row);
  }
  if(current.length)out.push(current);
  return out;
}
export function trendSummary(rows){
  const tail=segments(rows).at(-1)||[];
  if(tail.length<3)return {direction:'Insufficient data',slope:null,n:tail.length};
  const mx=tail.reduce((s,r)=>s+r.year,0)/tail.length,my=tail.reduce((s,r)=>s+r.resistance_pct,0)/tail.length;
  const slope=tail.reduce((s,r)=>s+(r.year-mx)*(r.resistance_pct-my),0)/tail.reduce((s,r)=>s+(r.year-mx)**2,0);
  return {direction:slope>=1?'Increasing':slope<=-1?'Decreasing':'Inconclusive / near-flat',slope,n:tail.length};
}
export function metricsFor(rows){
  const models=rows.some(r=>r.ridge_pred!=null)?['naive','linear','ridge']:['naive','linear'];
  const shared=rows.filter(r=>r.actual!=null&&models.every(m=>r[m+'_pred']!=null));
  return shared.length?models.map(model=>({model,n:shared.length,mae_pp:shared.reduce((s,r)=>s+Math.abs(r[model+'_pred']-r.actual),0)/shared.length,rmse_pp:Math.sqrt(shared.reduce((s,r)=>s+(r[model+'_pred']-r.actual)**2,0)/shared.length)})):[];
}
export function toCsv(rows){
  if(!rows.length)return '';
  const keys=[...new Set(rows.flatMap(Object.keys))];
  const escape=v=>{const s=v==null?'':typeof v==='object'?JSON.stringify(v):String(v);return /[",\r\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s;};
  return [keys.join(','),...rows.map(r=>keys.map(k=>escape(r[k])).join(','))].join('\r\n');
}
export function download(data,name,type='text/csv;charset=utf-8'){
  const url=URL.createObjectURL(new Blob([data],{type}));const anchor=document.createElement('a');anchor.href=url;anchor.download=name;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
