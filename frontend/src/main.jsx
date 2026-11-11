import {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import Icon,{BrandMark} from './Icons.jsx';
import {Overview,Trends,Forecasts,Evaluation} from './Pages.jsx';
import {ImportDialog,SourceDialog} from './Dialogs.jsx';
import {Button,Badge,RegionPicker,Notice,Empty,Help} from './UI.jsx';
import {REGION_NAMES,filterObservations,toCsv,download,numericObservations,statisticLabel} from './data.mjs';
import './styles.css';
import './readability.css';
import './tooltips.css';

const navigation=[{id:'overview',label:'Regional overview',icon:'overview'},{id:'trends',label:'Historical trends',icon:'trends'},{id:'forecasts',label:'Forecast lab',icon:'forecast'},{id:'evaluation',label:'Model evaluation',icon:'evaluation'}];
const copy={overview:{eyebrow:'GLOBAL AMR SURVEILLANCE',title:<>Regional <em>overview.</em></>,description:'A clearer view of reported antibiotic resistance across the six WHO regions.'},trends:{eyebrow:'THE HISTORICAL RECORD',title:<>Historical <em>trends.</em></>,description:'Explore annual observations, visible gaps, and the context behind changing trends.'},forecasts:{eyebrow:'EXPERIMENTAL FORECASTING',title:<>Forecast <em>lab.</em></>,description:'Review Colab projections alongside observed history. Every forecast keeps its limitations.'},evaluation:{eyebrow:'EVIDENCE BEFORE EXPECTATIONS',title:<>Model <em>evaluation.</em></>,description:'Compare Ridge with transparent baselines on the same chronological test cases.'}};

function App(){
  const [study,setStudy]=useState(null),[loadError,setLoadError]=useState(''),[loading,setLoading]=useState(true);
  const [page,setPage]=useState(navigation.some(n=>n.id===location.hash.slice(1))?location.hash.slice(1):'overview');
  const [definition,setDefinition]=useState(''),[regions,setRegions]=useState(Object.keys(REGION_NAMES));
  const [year,setYear]=useState(null),[from,setFrom]=useState(null),[to,setTo]=useState(null),[region,setRegion]=useState('AFR'),[model,setModel]=useState('naive');
  const [modal,setModal]=useState(null),[mobileOpen,setMobileOpen]=useState(false),[toast,setToast]=useState('');
  const [phase,setPhase]=useState('holdout');
  function acceptStudy(data){
    setStudy(data);setLoadError('');
    if(data.status==='ready'){
      const preferred=numericObservations(data.observations).find(r=>r.indicator_code==='ECOLI_3GC_BSI')||data.observations[0];
      const key=preferred.indicator_code+'|'+preferred.statistic_type;
      const selected=numericObservations(data.observations).filter(r=>r.indicator_code===preferred.indicator_code&&r.statistic_type===preferred.statistic_type);
      setDefinition(key);setYear(selected.length?Math.max(...selected.map(r=>r.year)):null);setFrom(selected.length?Math.min(...selected.map(r=>r.year)):null);setTo(selected.length?Math.max(...selected.map(r=>r.year)):null);
      setRegions(Object.keys(REGION_NAMES));setModel(data.metadata?.preferred_model||'naive');
    }
  }
  async function reload(){setLoading(true);try{const response=await fetch('/api/study');if(!response.ok)throw Error('The local study API did not respond successfully.');acceptStudy(await response.json());}catch(error){setLoadError(error.message);}finally{setLoading(false);}}
  useEffect(()=>{reload();const onHash=()=>{const id=location.hash.slice(1);if(navigation.some(n=>n.id===id))setPage(id);};addEventListener('hashchange',onHash);return()=>removeEventListener('hashchange',onHash);},[]);
  useEffect(()=>{if(toast){const id=setTimeout(()=>setToast(''),4500);return()=>clearTimeout(id);}},[toast]);
  function navigate(id){setPage(id);location.hash=id;setMobileOpen(false);window.scrollTo({top:0,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
  const ready=study?.status==='ready';
  const [indicator,statistic]=definition.split('|');
  const observations=ready?study.observations.filter(r=>r.indicator_code===indicator&&r.statistic_type===statistic):[];
  const definitions=ready?[...new Set(study.observations.map(r=>r.indicator_code+'|'+r.statistic_type))]:[];
  function changeDefinition(key){setDefinition(key);const [i,s]=key.split('|');const rows=numericObservations(study.observations).filter(r=>r.indicator_code===i&&r.statistic_type===s);const lo=rows.length?Math.min(...rows.map(r=>r.year)):null,hi=rows.length?Math.max(...rows.map(r=>r.year)):null;setFrom(lo);setTo(hi);setYear(hi);}
  function exportSelection(){
    let rows;
    if(page==='forecasts')rows=study.forecasts.filter(r=>r.who_region===region&&r.indicator_code===indicator&&r.statistic_type===statistic);
    else if(page==='evaluation')rows=study.backtests.filter(r=>r.phase===phase&&regions.includes(r.who_region)&&r.indicator_code===indicator&&r.statistic_type===statistic);
    else rows=filterObservations(observations,{indicator,statistic,regions,from:page==='trends'?from:year,to:page==='trends'?to:year});
    if(!rows.length){setToast('No rows available for this selection.');return;}
    download(toCsv(rows),`amr_${page}_selection.csv`);setToast('Your selected data have been exported.');
  }
  const studyYears=ready&&study.summary.first_year!=null?`${study.summary.first_year}—${study.summary.last_year}`:ready?'No numeric observations':'Awaiting data';
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
    {mobileOpen&&<button className="nav-backdrop" aria-label="Close navigation" onClick={()=>setMobileOpen(false)}/>}
    <aside className={`sidebar ${mobileOpen?'open':''}`} aria-label="Main navigation">
      <a href="#overview" className="brand" onClick={e=>{e.preventDefault();navigate('overview');}}><BrandMark/><div><span>AMR</span><strong>SENTINEL<span className="brand-period">.</span></strong></div></a>
      <div className="sidebar-label">RESEARCH WORKSPACE</div>
      <nav>{navigation.map(item=><a key={item.id} href={'#'+item.id} className={`nav-item ${page===item.id?'active':''}`} aria-current={page===item.id?'page':undefined} onClick={e=>{e.preventDefault();navigate(item.id);}}><Icon name={item.icon} size={19}/><span>{item.label}</span>{page===item.id&&<i/>}</a>)}</nav>
      <div className="sidebar-divider"/>
      <div className="sidebar-label">EXPLORE THE EVIDENCE</div>
      <button className="nav-item secondary" onClick={()=>setModal('sources')} disabled={!ready}><Icon name="shield" size={19}/><span>Sources & data quality</span></button>
      <a className="nav-item secondary" href="/api/notebook" download><Icon name="document" size={19}/><span>Colab notebook</span><Icon name="northeast" size={14}/></a>
      <div className="sidebar-bottom"><div className="study-tag"><span className="tag-label"><i/>CURRENT STUDY</span><strong>{studyYears}</strong><p>WHO source observations<br/>{ready?statisticLabel(statistic):'Awaiting a verified study'}</p><div className="study-tag-foot"><span>SDG 3.d.2</span><Icon name="globe" size={16}/></div></div><p className="sidebar-disclaimer">An academic lens on surveillance.<br/>Not clinical guidance.</p><span className="sidebar-version">AMR SENTINEL <span>v2.0</span></span></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-toggle" aria-label="Open navigation" onClick={()=>setMobileOpen(true)}><Icon name="menu"/></button><span>Surveillance</span><Icon name="chevron" size={12}/><strong>{navigation.find(n=>n.id===page)?.label}</strong></div><div className="topbar-right"><span className="academic-tag">ACADEMIC RESEARCH</span><span className="workspace-avatar" aria-label="Research workspace">AS</span></div></header>
      <main id="main-content" tabIndex="-1">
        <div className="page-heading"><div><span className="eyebrow"><i className="heading-line"/>{copy[page].eyebrow}</span><h1>{copy[page].title}</h1></div><div className="page-actions"><Button icon="upload" onClick={()=>setModal('import')}>Import study</Button><Button icon="download" variant="primary" disabled={!ready} onClick={exportSelection}>Export data</Button></div></div>
        {loadError?<div className="error-state" role="alert"><Empty title="The study could not be loaded">{loadError}</Empty><Button icon="refresh" onClick={reload}>Try again</Button></div>:loading?<div className="loading-state" role="status"><span className="loading-ring"/>Reading and checking your Colab study…</div>:!ready?<><Empty title="Real dataset required — analysis unavailable">{study?.error||'Open a verified Colab study bundle or import authentic WHO observations to begin. No example observations or predictions are substituted.'}</Empty><div className="empty-actions"><Button variant="primary" icon="upload" onClick={()=>setModal('import')}>Import Colab study</Button><a className="button" href="/api/notebook" download><Icon name="download" size={16}/>Download notebook</a></div></>:<>
          <div className="context-strip"><label className="indicator-select"><Icon name="layers" size={16}/><select aria-label="Indicator and statistical definition" value={definition} onChange={e=>changeDefinition(e.target.value)}>{definitions.map(key=><option key={key} value={key}>{key.startsWith('ECOLI')?'E. coli · 3GC resistance':'MRSA · Bloodstream infection'} / {key.split('|')[1]==='derived_country_median'?'Derived country median':'WHO unadjusted median'}</option>)}</select><Icon name="chevrondown" size={13}/></label><span className="context-badge"><i/>Observed {from==null?'unavailable':`${Math.min(...numericObservations(observations).map(r=>r.year))}–${Math.max(...numericObservations(observations).map(r=>r.year))}`}</span><button className="text-button source-button" onClick={()=>setModal('sources')}>Source notes <Icon name="info" size={14}/></button></div>
          {page!=='forecasts'&&<RegionPicker regions={regions} setRegions={setRegions}/>}
          <div className="page-content" key={page}>
            {!numericObservations(observations).length?<Empty title="No numeric observations">The selected target has no observed percentages. Missing values have not been filled.</Empty>:<>
            {page==='overview'&&<Overview study={study} observations={observations} regions={regions} year={year} setYear={setYear} onInspect={r=>{setRegions([r]);navigate('trends');}} onNavigate={navigate} onSources={()=>setModal('sources')}/>}
            {page==='trends'&&<Trends observations={observations} regions={regions} from={from} to={to} setFrom={setFrom} setTo={setTo}/>}
            {page==='forecasts'&&<Forecasts study={study} observations={observations} region={region} setRegion={setRegion} model={model} setModel={setModel}/>}
            {page==='evaluation'&&<Evaluation study={study} observations={observations} regions={regions} phase={phase} setPhase={setPhase} onSources={()=>setModal('sources')}/>}
          </>}
          </div>
          <div className="interpretation-note"><Help text="Reporting-country medians reflect participating surveillance systems, not population prevalence. Country coverage and testing practices can change over time.">Surveillance estimates · not population prevalence</Help></div>
        </>}
        <footer className="footer"><div><span className="footer-brand">AMR SENTINEL<span>·</span></span><span>Source: WHO GLASS & SDG indicator 3.d.2</span></div><a href={indicator==='MRSA_BSI'?'https://data.who.int/indicators/i/918081E/5DD9606':'https://data.who.int/indicators/i/918081E/745F475'} target="_blank" rel="noreferrer">Explore the WHO source <Icon name="northeast" size={12}/></a></footer>
      </main>
    </div>
    {modal==='import'&&<ImportDialog onClose={()=>setModal(null)} onImported={data=>{acceptStudy(data);setToast('Study validated and opened.');}}/>}
    {modal==='sources'&&ready&&<SourceDialog study={study} definition={definition} onClose={()=>setModal(null)}/>}
    {toast&&<div className="toast" role="status"><Icon name="check" size={16}/>{toast}</div>}
  </div>;
}

createRoot(document.getElementById('root')).render(<App/>);
