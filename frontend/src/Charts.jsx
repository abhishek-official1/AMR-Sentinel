import {useState,useEffect} from 'react';
import {REGION_NAMES,REGION_COLORS,fmt,segments} from './data.mjs';

function useCompactChart(){
  const [compact,setCompact]=useState(typeof window!=='undefined'&&window.innerWidth<=740);
  useEffect(()=>{const media=window.matchMedia('(max-width:740px)');const update=()=>setCompact(media.matches);update();media.addEventListener('change',update);return()=>media.removeEventListener('change',update);},[]);
  return compact;
}

export function LineChart({rows,regions=Object.keys(REGION_NAMES),projection=null,height=310,title='Observed resistance over time'}){
  const [hover,setHover]=useState(null);
  const compact=useCompactChart();
  const all=rows.filter(r=>r.resistance_pct!=null);
  if(!all.length)return <div className="chart-empty">No observations for this selection.</div>;
  const w=compact?460:950,h=compact?290:height,p={l:40,r:24,t:25,b:45};
  const years=all.map(r=>r.year);if(projection)years.push(projection.target_year);
  const lo=Math.min(...years),hi=Math.max(...years),span=Math.max(1,hi-lo);
  const x=year=>p.l+(year-lo)/span*(w-p.l-p.r),y=value=>h-p.b-value/100*(h-p.b-p.t);
  const ticks=Array.from({length:hi-lo+1},(_,i)=>lo+i);
  const point=(r,forecast=false)=>{const px=x(forecast?r.target_year:r.year),py=y(forecast?r.prediction:r.resistance_pct);return {x:px,y:py,row:r,forecast};};
  return <div className="line-chart"><svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={title} onMouseLeave={()=>setHover(null)}>
    <title>{`${title}. Values are percentages; line breaks show missing observations.`}</title>
    {[0,25,50,75,100].map(v=><g key={v}><line x1={p.l} x2={w-p.r} y1={y(v)} y2={y(v)} className="grid-line"/><text x={p.l-14} y={y(v)+4} textAnchor="end" className="axis-label">{v}{v===100?'%':''}</text></g>)}
    {ticks.map(year=><text key={year} x={x(year)} y={h-13} textAnchor="middle" className="axis-label">{year}</text>)}
    {regions.map(region=>{
      const data=rows.filter(r=>r.who_region===region);
      return <g key={region}>{segments(data).map((part,index)=><polyline key={index} points={part.map(r=>`${x(r.year)},${y(r.resistance_pct)}`).join(' ')} fill="none" stroke={REGION_COLORS[region]} strokeWidth="2.8" strokeLinejoin="round"/>)}
        {data.filter(r=>r.resistance_pct!=null).map(r=><g key={r.year} tabIndex="0" role="img" aria-label={`${REGION_NAMES[region]}, ${r.year}: ${fmt(r.resistance_pct,2)} percent; ${r.country_count??'unknown'} reporting countries`} onFocus={()=>setHover(point(r))} onBlur={()=>setHover(null)} onMouseEnter={()=>setHover(point(r))}><circle cx={x(r.year)} cy={y(r.resistance_pct)} r="10" fill="transparent"/><circle cx={x(r.year)} cy={y(r.resistance_pct)} r="3.6" stroke="#fcfcf8" strokeWidth="1.5" fill={REGION_COLORS[region]}/></g>)}
      </g>;
    })}
    {projection&&<g tabIndex="0" role="img" aria-label={`Experimental ${projection.target_year} forecast: ${fmt(projection.prediction,2)} percent; not observed`} onFocus={()=>setHover(point(projection,true))} onBlur={()=>setHover(null)} onMouseEnter={()=>setHover(point(projection,true))}>
      <line x1={x(projection.last_observed_year)} x2={x(projection.target_year)} y1={y(rows.filter(r=>r.year===projection.last_observed_year)[0]?.resistance_pct??projection.prediction)} y2={y(projection.prediction)} stroke="#c4663d" strokeWidth="2" strokeDasharray="6 5"/>
      <path d={`M${x(projection.target_year)},${y(projection.prediction)-8}l8,8-8,8-8-8Z`} fill="#c4663d" stroke="#fcfcf8" strokeWidth="2"/>
    </g>}
    {hover&&<g className="chart-tooltip" pointerEvents="none" transform={`translate(${Math.min(w-220,Math.max(p.l,hover.x-100))},${Math.max(2,hover.y-85)})`}><rect width="210" height="70" rx="8" fill="#263128"/><text x="13" y="22" fill="#ecede7" fontSize="12">{hover.forecast?'Experimental forecast':REGION_NAMES[hover.row.who_region]} · {hover.forecast?hover.row.target_year:hover.row.year}</text><text x="13" y="45" fill="#fcfcf8" fontSize="19" fontWeight="600">{fmt(hover.forecast?hover.row.prediction:hover.row.resistance_pct,2)}%</text><text x="13" y="61" fill="#c0c9bc" fontSize="10">{hover.forecast?'Not observed / not independently verified':`${hover.row.country_count??'Unknown'} reporting countries`}</text></g>}
  </svg></div>;
}

export function RegionBars({rows,onRegion}){
  const [focus,setFocus]=useState(null);
  const compact=useCompactChart();
  const w=compact?460:850,h=270,p={l:38,r:18,t:15,b:35};
  const scale=(h-p.b-p.t)/100,bw=(w-p.l-p.r)/6;
  return <svg className="bar-chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Regional comparison of observed resistance percentages">
    {[0,25,50,75,100].map(v=><g key={v}><line x1={p.l} x2={w-p.r} y1={h-p.b-v*scale} y2={h-p.b-v*scale} className="grid-line"/><text x={p.l-10} y={h-p.b-v*scale+4} textAnchor="end" className="axis-label">{v}</text></g>)}
    {Object.keys(REGION_NAMES).map((region,i)=>{
      const row=rows.find(r=>r.who_region===region),v=row?.resistance_pct??null,x=p.l+i*bw+bw*.2,y=h-p.b-(v??0)*scale;
      return <g key={region} className="region-bar" role="button" tabIndex="0" aria-label={`${REGION_NAMES[region]}: ${v==null?'data unavailable':fmt(v,2)+' percent'}. Inspect historical trends.`} onClick={()=>onRegion?.(region)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onRegion?.(region);}}} onMouseEnter={()=>setFocus(region)} onMouseLeave={()=>setFocus(null)} onFocus={()=>setFocus(region)} onBlur={()=>setFocus(null)}>
        {v!=null?<><rect x={x} y={y} width={bw*.6} height={v*scale} rx="4" fill={REGION_COLORS[region]} opacity={focus&&focus!==region ? .6 : 1}/><text x={x+bw*.3} y={y-9} textAnchor="middle" className="bar-value">{fmt(v,1)}%</text></>:<text x={x+bw*.3} y={h-p.b-15} textAnchor="middle" className="axis-label">Unavailable</text>}
        <text x={x+bw*.3} y={h-10} textAnchor="middle" className="bar-region">{region}</text>
        <title>{`${REGION_NAMES[region]}: ${v==null?'Data unavailable':`${fmt(v,2)}% · ${row.country_count??'Unknown'} countries`}`}</title>
      </g>;
    })}
  </svg>;
}

export function CoverageGrid({coverage,observations,from,to}){
  const years=Array.from({length:to-from+1},(_,i)=>from+i);
  return <div className="coverage-grid" style={{'--year-count':years.length}}>
    <span/><div className="coverage-years">{years.map(year=><span key={year}>{String(year).slice(2)}</span>)}</div>
    {Object.keys(REGION_NAMES).map(region=><div className="coverage-row" key={region}><span className="coverage-label">{region}</span><div className="coverage-cells">{years.map(year=>{
      const row=coverage.find(r=>r.who_region===region&&r.year===year)||observations.find(r=>r.who_region===region&&r.year===year);
      const count=row?.country_count??null;
      return <span key={year} className={`coverage-cell ${count==null?'missing':count<5?'suppressed':''}`} style={{backgroundColor:count==null?undefined:`rgba(98,126,100,${.18+Math.min(count,30)/30*.82})`}} tabIndex="0" aria-label={`${REGION_NAMES[region]}, ${year}: ${count??'unknown'} reporting countries${count!=null&&count<5?'; median suppressed':''}`} title={`${region} · ${year}: ${count??'Unknown'} countries${count!=null&&count<5?' (suppressed)':''}`}>{count??'–'}</span>;
    })}</div></div>)}
  </div>;
}
