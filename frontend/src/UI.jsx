import {useEffect,useRef,useId,useState} from 'react';
import {createPortal} from 'react-dom';
import Icon from './Icons.jsx';
import {fmt,REGION_NAMES,REGION_COLORS} from './data.mjs';

export function Button({children,icon,variant='',className='',...props}){return <button className={`button ${variant} ${className}`} {...props}>{icon&&<Icon name={icon} size={16}/>} {children}</button>}
export function Help({children,text,className=''}){
  const id=useId(),anchor=useRef(null),timer=useRef(null),[position,setPosition]=useState(null);
  const close=()=>{clearTimeout(timer.current);setPosition(null);};
  const scheduleClose=()=>{timer.current=setTimeout(close,150);};
  function show(){clearTimeout(timer.current);const rect=anchor.current.getBoundingClientRect(),width=Math.min(280,innerWidth-24),below=rect.top<120;setPosition({left:Math.max(12,Math.min(rect.left+rect.width/2-width/2,innerWidth-width-12)),top:below?rect.bottom+10:rect.top-10,width,transform:below?'none':'translateY(-100%)'});}
  useEffect(()=>{if(!position)return;const dismiss=e=>{if(e.key==='Escape'||e.type==='resize'||e.type==='scroll'||(e.type==='pointerdown'&&!anchor.current?.contains(e.target)&&!e.target.closest?.('.help-bubble')))close();};document.addEventListener('keydown',dismiss);document.addEventListener('pointerdown',dismiss);window.addEventListener('resize',dismiss);window.addEventListener('scroll',dismiss,true);return()=>{document.removeEventListener('keydown',dismiss);document.removeEventListener('pointerdown',dismiss);window.removeEventListener('resize',dismiss);window.removeEventListener('scroll',dismiss,true);};},[position]);
  useEffect(()=>()=>clearTimeout(timer.current),[]);
  return <><button ref={anchor} type="button" className={`help-trigger ${className}`} aria-describedby={id} onMouseEnter={show} onMouseLeave={scheduleClose} onFocus={show} onBlur={scheduleClose} onClick={show}>{children}<Icon name="info" size={12}/></button><span id={id} role="tooltip" className="sr-only">{text}</span>{position&&createPortal(<span className="help-bubble" aria-hidden="true" style={position} onMouseEnter={()=>clearTimeout(timer.current)} onMouseLeave={scheduleClose}>{text}</span>,document.body)}</>;
}
export function Panel({title,eyebrow,action,children,className='',description}){return <section className={`panel ${className}`}><header className="panel-header"><div>{eyebrow&&<span className="eyebrow">{eyebrow}</span>}<h2>{description?<Help text={description}>{title}</Help>:title}</h2></div>{action}</header>{children}</section>}
export function Badge({children,tone=''}){return <span className={`badge ${tone}`}>{children}</span>}
export function RegionPicker({regions,setRegions}){return <div className="region-picker" aria-label="Filter WHO regions"><button className={`region-chip ${regions.length===6?'selected':''}`} onClick={()=>setRegions(regions.length===6?[]:Object.keys(REGION_NAMES))}>All regions <span>{regions.length}/6</span></button>{Object.entries(REGION_NAMES).map(([code,label])=><button key={code} className={`region-chip ${regions.includes(code)?'selected':''}`} aria-pressed={regions.includes(code)} title={label} onClick={()=>setRegions(regions.includes(code)?regions.filter(r=>r!==code):[...regions,code])}><i style={{background:REGION_COLORS[code]}}/>{code}</button>)}</div>}
export function Notice({children,compact=false}){return <div className={`notice ${compact?'compact':''}`}><Icon name="info" size={17}/><p>{children}</p></div>}
export function Empty({title='Data unavailable',children}){return <div className="empty"><div className="empty-icon"><Icon name="layers" size={28}/></div><h3>{title}</h3><p>{children||'There are no verified observations for this selection.'}</p></div>}
export function Stat({label,value,note,icon}){return <div className="stat"><div className="stat-top"><span>{label}</span><Icon name={icon} size={18}/></div><Help className="stat-value" text={note}><strong>{value}</strong></Help></div>}
export function Legend({regions=Object.keys(REGION_NAMES),forecast=false}){return <div className="legend">{regions.map(r=><span key={r}><i style={{background:REGION_COLORS[r]}}/>{REGION_NAMES[r]}</span>)}{forecast&&<span><b className="legend-diamond"/>Experimental forecast</span>}</div>}
export function Table({columns,rows,empty='No rows available.',caption}){return <div className="table-wrap"><table>{caption&&<caption className="sr-only">{caption}</caption>}<thead><tr>{columns.map(c=><th key={c.key} scope="col">{c.help?<Help text={c.help}>{c.label}</Help>:c.label}</th>)}</tr></thead><tbody>{rows.length?rows.map((row,i)=><tr key={i}>{columns.map(c=><td key={c.key}>{c.help?<Help text={c.help}>{c.render?c.render(row):row[c.key]??'—'}</Help>:c.render?c.render(row):row[c.key]??'—'}</td>)}</tr>):<tr><td colSpan={columns.length}>{empty}</td></tr>}</tbody></table></div>}
export function RegionName({code,full=true}){return <span className="region-name"><i style={{background:REGION_COLORS[code]}}/><span>{full?REGION_NAMES[code]:code}</span>{full&&<small>{code}</small>}</span>}
export function Direction({summary}){return <span className={`direction ${summary.slope>=1?'up':summary.slope<=-1?'down':''}`}><Icon name={summary.slope>=1?'northeast':summary.slope<=-1?'arrow':'minus'} size={13}/>{summary.direction}</span>}
export function Modal({title,onClose,children,wide=false}){
  const dialog=useRef(null);
  useEffect(()=>{const el=dialog.current;el.showModal();const old=document.body.style.overflow;document.body.style.overflow='hidden';return()=>{document.body.style.overflow=old;};},[]);
  return <dialog ref={dialog} className={`modal ${wide?'wide':''}`} onCancel={e=>{e.preventDefault();onClose();}} onClick={e=>{if(e.target===dialog.current)onClose();}} aria-label={title}><div className="modal-inner"><header className="modal-header"><h2>{title}</h2><button className="icon-button" aria-label="Close dialog" onClick={onClose}><Icon name="close"/></button></header>{children}</div></dialog>;
}
