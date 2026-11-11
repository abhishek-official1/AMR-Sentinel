export default function Icon({name,size=18,...props}){
  const paths={
    overview:<><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    trends:<><path d="M4 4v16h16M6 15l5-5 4 3 5-8"/></>,
    forecast:<><path d="M9 3h6M10 3v7l-5 8a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-8V3M8 15h8"/></>,
    evaluation:<><path d="M5 20V10m7 10V4m7 16v-7M3 21h19"/></>,
    download:<><path d="M12 3v12m-4-4 4 4 4-4M4 17v4h16v-4"/></>,
    upload:<><path d="M12 16V4m-4 4 4-4 4 4M4 16v5h16v-5"/></>,
    arrow:<><path d="M5 12h14m-5-5 5 5-5 5"/></>,
    northeast:<><path d="M5 19 19 5M6 5h13v13"/></>,
    chevron:<path d="m8 5 7 7-7 7"/>,
    chevrondown:<path d="m6 9 6 6 6-6"/>,
    close:<path d="m6 6 12 12M6 18 18 6"/>,
    info:<><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/></>,
    globe:<><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/></>,
    shield:<><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/></>,
    calendar:<><rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 3v5m8-5v5M4 11h16"/></>,
    people:<><circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-16a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 5"/></>,
    layers:<><path d="m12 3 10 5-10 5L2 8zm-10 10 10 5 10-5M2 18l10 5 10-5"/></>,
    check:<path d="m5 12 4 4L19 6"/>,
    document:<><path d="M14 3H5v18h14V8zm0 0v5h5M8 12h8m-8 4h6"/></>,
    menu:<path d="M4 6h16M4 12h16M4 18h16"/>,
    refresh:<><path d="M20 8V3l-4 4a8 8 0 1 0 4 9M20 3h-5"/></>,
    minus:<path d="M5 12h14"/>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]||paths.info}</svg>;
}
export function BrandMark(){return <svg className="brand-mark" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M20 5v30M5 20h30M9.4 9.4l21.2 21.2M9.4 30.6 30.6 9.4" stroke="currentColor" strokeWidth="2.4"/><circle cx="20" cy="20" r="7" fill="currentColor"/><circle cx="20" cy="20" r="3" fill="#222722"/></svg>}
