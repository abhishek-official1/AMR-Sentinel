import {useState} from 'react';
import {Button,Modal,Badge,Notice,Table} from './UI.jsx';
import Icon from './Icons.jsx';
import {download,REGION_NAMES,statisticLabel,targetMatches,numericObservations} from './data.mjs';

export function ImportDialog({onClose,onImported}){
  const [mode,setMode]=useState('study'),[file,setFile]=useState(null),[mapping,setMapping]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function submit(e){
    e.preventDefault();if(!file)return;setBusy(true);setError('');
    try{
      let response;
      if(mode==='study')response=await fetch('/api/import/study',{method:'POST',body:file,headers:{'Content-Type':'application/zip'}});
      else{
        if(!mapping)throw Error('Choose the column-mapping and provenance JSON file.');
        const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=16384)binary+=String.fromCharCode(...bytes.subarray(i,i+16384));
        response=await fetch('/api/import/observations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:file.name,content_base64:btoa(binary),mapping:JSON.parse(await mapping.text())})});
      }
      const body=await response.json();if(!response.ok)throw Error(body.detail||'Import could not be validated.');onImported(body);onClose();
    }catch(err){setError(err.message);}finally{setBusy(false);}
  }
  return <Modal title="Bring your study into focus" onClose={onClose}><p className="modal-lead">Load observations and results from your Colab analysis. The data identity and model scores are checked before anything changes.</p><div className="segmented"><button className={mode==='study'?'active':''} onClick={()=>{setMode('study');setFile(null);setError('');}}>Colab study ZIP</button><button className={mode==='observations'?'active':''} onClick={()=>{setMode('observations');setFile(null);setError('');}}>WHO CSV / XLSX</button></div><form onSubmit={submit}>
    <label className="upload-zone"><Icon name="upload" size={30}/><strong>{file?file.name:mode==='study'?'Choose your Colab study bundle':'Choose an untouched WHO export'}</strong><span>{mode==='study'?'amr_project_bundle.zip · up to 50 MB':'CSV or XLSX · original source bytes preserved'}</span><input key={mode} aria-label="Select study or WHO data file" type="file" accept={mode==='study'?'.zip':'.csv,.xlsx'} required onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
    {mode==='observations'&&<label className="field">Column mapping and provenance JSON<input aria-label="Mapping JSON" type="file" accept=".json" required onChange={e=>setMapping(e.target.files?.[0]||null)}/><small>Use the format in config/mapping.example.json. Explicit percentage scale and WHO source metadata are required.</small></label>}
    {error&&<div className="form-error" role="alert"><Icon name="info"/>{error}</div>}
    <Notice compact>Models are trained only in Colab. This dashboard imports CSV/JSON results and never loads fitted model files. Imports last for this server session; the original study bundle remains your reproducible archive.</Notice>
    <div className="modal-actions"><Button type="button" onClick={onClose}>Cancel</Button><Button variant="primary" icon={busy?'refresh':'shield'} type="submit" disabled={busy||!file}>{busy?'Validating…':'Validate & open study'}</Button></div>
  </form></Modal>;
}

export function SourceDialog({study,onClose,definition}){
  const [indicator,statistic]=definition.split('|');
  const files=(study.manifest?.files||[]).filter(f=>f.adapter?.indicator_code===indicator&&f.adapter?.statistic_type===statistic),upstream=study.manifest?.upstream_sources||[];
  const meta=study.metadata||{},matched=targetMatches({indicator_code:indicator,statistic_type:statistic},meta),unknown=matched?(study.validation?.unmapped_country_codes||[]):[];
  const quality=study.quality.filter(r=>r.indicator_code===indicator&&r.statistic_type===statistic);
  const indicatorUrl=indicator==='MRSA_BSI'?'https://data.who.int/indicators/i/918081E/5DD9606':'https://data.who.int/indicators/i/918081E/745F475';
  const derived=statistic==='derived_country_median';
  const values=numericObservations(study.observations.filter(r=>r.indicator_code===indicator&&r.statistic_type===statistic));
  const first=values.length?Math.min(...values.map(r=>r.year)):null,last=values.length?Math.max(...values.map(r=>r.year)):null;
  return <Modal title="The evidence behind the dashboard" onClose={onClose} wide>
    <div className="source-summary"><Badge tone="neutral">Source transparency · {indicator}</Badge><h3>Reported observations. Visible limitations.</h3><p>{derived?'This target uses derived, unweighted medians of available national resistance percentages.':'This target uses WHO-provided unadjusted regional medians, kept separate from derived country medians.'} These describe reporting surveillance systems and are not population prevalence or WHO-adjusted regional estimates.</p></div>
    <div className="source-facts"><div><span>Source</span><strong>WHO · SDG 3.d.2</strong></div><div><span>Observation period</span><strong>{first??'Unknown'}–{last??'Unknown'}</strong></div><div><span>Input provenance</span><strong>User-supplied WHO export</strong></div><div><span>Colab analysis</span><strong>{matched&&meta.created_at?new Date(meta.created_at).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}):'Pending'}</strong></div></div>
    <Notice>Checksums verify file consistency; they do not independently authenticate the publisher. Source revision: {files[0]?.adapter?.source_revision||'Not available'}.</Notice>
    <h3 className="section-title">Coverage & eligibility</h3><ul className="plain-list"><li>Regional medians require at least five reporting countries in a year.</li><li>Unknown infection/testing counts cannot establish WHO chart eligibility.</li><li>{files[0]?.adapter?.coverage_note||'Region membership follows the supplied source mapping; historical memberships may differ.'}</li>{unknown.length>0&&<li><strong>{unknown.length} unmapped identifier{unknown.length>1?'s':''} excluded:</strong> {unknown.join(', ')}. Review input_validation.json and the original source file.</li>}<li>Forecasts require four consecutive observed years. {last==null?'No valid endpoint is available for forecasting.':`An endpoint of ${last} produces an experimental ${last+1} projection.`}</li></ul>
    <Table caption="Regional data quality" columns={[{key:'who_region',label:'Region'},{key:'n_observations',label:'Observed years'},{key:'consecutive_years',label:'Consecutive years'},{key:'forecast_eligible',label:'Forecast history',render:r=>r.forecast_eligible?'Eligible':'Insufficient'}]} rows={quality}/>
    <h3 className="section-title">Traceable source files</h3>{[...files,...upstream].map((file,i)=><div className="source-file" key={i}><Icon name="document"/><div><strong>{file.original_filename||file.filename}</strong><code>{file.sha256}</code><small>{file.adapter?.source_downloaded_at||file.downloaded_at||'Retrieval date unknown'}</small></div></div>)}
    <div className="source-links"><a href={indicatorUrl} target="_blank" rel="noreferrer">WHO indicator definition <Icon name="northeast" size={14}/></a><a href="https://worldhealthorg.shinyapps.io/glass-dashboard/" target="_blank" rel="noreferrer">WHO GLASS dashboard <Icon name="northeast" size={14}/></a></div>
    <div className="modal-actions">{study.report_available&&<a className="button" href="/api/report" download><Icon name="document" size={16}/>Analysis report</a>}<a className="button" href="/api/export/quality"><Icon name="download" size={16}/>Data quality CSV</a><Button icon="download" onClick={()=>download(JSON.stringify({manifest:study.manifest,metadata:study.metadata,validation:study.validation},null,2),'amr_provenance.json','application/json')}>Source metadata</Button></div>
  </Modal>;
}
