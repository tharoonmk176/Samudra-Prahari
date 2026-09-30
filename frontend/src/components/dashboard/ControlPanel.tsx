import React from 'react';
import { MapPinLine, Scan, Faders, Play, Cpu, UploadSimple, CaretUp, CaretDown } from "@phosphor-icons/react/dist/ssr";

export default function ControlPanel(props: any) {
  const [searchQuery, setSearchQuery] = React.useState('');
  const [isConfigOpen, setIsConfigOpen] = React.useState(true);
  const SliderRow = ({ label, value, onChange, min, max, step }: any) => (
    <div className="flex flex-col gap-1.5 py-2">
      <div className="flex justify-between items-center">
        <span className="text-[13px] text-slate-400 font-medium tracking-tight">{label}</span>
        <span className="text-[12px] text-blue-400 font-mono bg-blue-500/10 px-2 py-0.5 rounded-none border border-blue-500/20">{Number(value).toFixed(2)}</span>
      </div>
      <input 
        type="range" 
        min={min} 
        max={max} 
        step={step}
        value={value} 
        onChange={(e) => onChange(parseFloat(e.target.value))} 
        className="w-full h-1.5 bg-white/10 rounded-none appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400 transition-all"
      />
    </div>
  );

  const InputRow = ({ label, value, onChange, type="text" }: any) => (
    <div className="flex justify-between items-center py-1.5">
      <span className="text-[13px] text-slate-400 font-medium tracking-tight">{label}</span>
      <input 
        type={type} 
        value={value} 
        onChange={(e) => onChange(e.target.value)} 
        className="w-24 bg-slate-800/50 border border-slate-800 text-white text-sm px-3 py-1 rounded-none outline-none focus:border-blue-500/50 focus:bg-white/10 transition-all font-mono text-right shadow-inner"
      />
    </div>
  );

  const ToggleRow = ({ label, checked, onChange }: any) => (
    <div className="flex justify-between items-center py-2">
      <span className="text-[13px] text-slate-400 font-medium tracking-tight">{label}</span>
      <button 
        onClick={() => onChange(!checked)}
        className={`w-10 h-5 p-0.5 transition-colors relative border rounded-full ${checked ? 'bg-blue-600 border-blue-500' : 'bg-slate-900 border-slate-700'}`}
      >
        <div className={`w-3.5 h-3.5 bg-white rounded-full transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
      </button>
    </div>
  );

  return (
    <div className={`flex flex-col h-full bg-slate-950 text-slate-100 border-l border-slate-800 shadow-2xl relative overflow-x-hidden transition-all duration-300 ease-in-out ${isConfigOpen ? "w-80" : "w-[60px]"}`}>
      
      {/* Header */}
      <div 
        className={`py-5 flex items-center shrink-0 border-b border-slate-800 cursor-pointer hover:bg-slate-800/30 transition-all ${isConfigOpen ? "px-6 justify-between" : "px-0 justify-center"}`}
        onClick={() => setIsConfigOpen(!isConfigOpen)}
      >
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-blue-500/10 rounded-none border border-blue-500/20 shrink-0">
            <Faders size={16} className="text-blue-400" />
          </div>
          {isConfigOpen && <h2 className="text-sm font-semibold text-white tracking-wide uppercase whitespace-nowrap">Pipeline Config</h2>}
        </div>
        {isConfigOpen && (
          <button className="text-slate-400 hover:text-white transition-colors">
            <CaretDown size={16} className="-rotate-90" />
          </button>
        )}
      </div>

      {isConfigOpen && (
      <div className="flex-1 overflow-y-auto px-5 py-6 space-y-5 no-scrollbar">
        
        {/* Upload Section */}
        <label className="w-full relative group cursor-pointer block">
          <div className="absolute inset-0 bg-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-none" />
          <div className="border-2 border-dashed border-slate-700 group-hover:border-blue-500/50 bg-slate-900/50 transition-all p-6 flex flex-col items-center justify-center gap-4 rounded-none text-center shadow-sm">
             <div className="p-3 bg-slate-800 rounded-full group-hover:bg-blue-500/20 group-hover:text-blue-400 transition-all shadow-lg">
                <UploadSimple size={24} className="text-slate-400 group-hover:text-blue-400" />
             </div>
             <div className="flex flex-col gap-1 w-full">
               <span className="text-sm font-bold text-white tracking-wide">
                 {props.files?.length > 0 ? `${props.files.length} File(s) Ready for Processing` : 'Ingest Sonar Data'}
               </span>
               <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider mb-2">
                 Drag & Drop or Click to Browse
               </span>
               <div className="flex items-center justify-center gap-2 mt-1">
                 <span className="text-[10px] px-2 py-1 bg-slate-800 text-slate-300 border border-slate-700">.XTF</span>
                 <span className="text-[10px] px-2 py-1 bg-slate-800 text-slate-300 border border-slate-700">.JPG / .PNG</span>
                 <span className="text-[10px] px-2 py-1 bg-slate-800 text-slate-300 border border-slate-700">.MP4 (Video)</span>
               </div>
             </div>
          </div>
          <input type="file" multiple accept="image/*,video/mp4,.xtf" className="hidden" onChange={(e) => {
              if (e.target.files) props.setFiles(Array.from(e.target.files));
          }} />
        </label>

        {/* Pipeline Card */}
        <div className="bg-slate-800/30 border border-slate-800 rounded-none p-4 shadow-sm">
          <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
            <Scan size={14} /> Processing Stages
          </h3>
          <div className="flex flex-col gap-0.5">
             <ToggleRow label="Mosaic Stitching" checked={props.enableStitching} onChange={props.setEnableStitching} />
             <ToggleRow label="Compile to Video Feed" checked={props.compileVideo} onChange={props.setCompileVideo} />
             {props.enableStitching && (
               <div className="flex justify-between items-center py-1.5 mb-1 bg-slate-800/30 px-3 rounded-none border border-slate-800">
                 <span className="text-xs text-slate-400 font-medium">Stitch Direction</span>
                 <select value={props.stitchDirection} onChange={e => props.setStitchDirection(e.target.value)} className="bg-transparent text-xs outline-none text-white cursor-pointer font-medium text-right">
                   <option value="vertical">Vertical (Along Track)</option>
                   <option value="horizontal">Horizontal (Cross Track)</option>
                 </select>
               </div>
             )}
             <ToggleRow label="Denoise Filter" checked={props.denoise} onChange={props.setDenoise} />
             <ToggleRow label="Nadir Removal" checked={props.nadir} onChange={props.setNadir} />
             <ToggleRow label="Slant Range Correct" checked={props.slant} onChange={props.setSlant} />
          </div>
        </div>

        {/* AI Thresholds Card */}
        <div className="bg-slate-800/30 border border-slate-800 rounded-none p-4 shadow-sm">
          <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
            <Cpu size={14} /> Inference Engine
          </h3>
          <div className="flex flex-col gap-1">
             <SliderRow label="Min Confidence" value={props.confThresh} onChange={props.setConfThresh} min="0.01" max="0.99" step="0.01" />
             <SliderRow label="NMS Strictness" value={props.keepThresh} onChange={props.setKeepThresh} min="0.01" max="0.99" step="0.01" />
             <SliderRow label="UNet Strictness" value={props.unetThresh} onChange={props.setUnetThresh} min="0.01" max="0.99" step="0.01" />
          </div>
        </div>

        {/* Geospatial Card */}
        <div className="bg-slate-800/30 border border-slate-800 rounded-none p-4 shadow-sm">
          <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
            <MapPinLine size={14} /> Telemetry
          </h3>
          <div className="flex flex-col gap-1">
             <ToggleRow label="Enable GeoReferencing" checked={props.enableGeo} onChange={props.setEnableGeo} />
             {props.enableGeo && (
               <div className="mt-2 pt-3 border-t border-slate-800 flex flex-col gap-1">
                 <div className="flex gap-2 mb-2">
                   <input 
                     type="text" 
                     placeholder="Search location (e.g. Erode)" 
                     value={searchQuery}
                     onChange={(e) => setSearchQuery(e.target.value)}
                     className="flex-1 bg-slate-800/50 border border-slate-800 text-white text-xs px-3 py-1.5 rounded-none outline-none focus:border-blue-500/50"
                     onKeyDown={(e) => {
                       if (e.key === 'Enter') {
                         fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(searchQuery)}&format=json&limit=1`)
                           .then(res => res.json())
                           .then(data => {
                             if (data && data.length > 0) {
                               props.setStartLat(parseFloat(data[0].lat));
                               props.setStartLon(parseFloat(data[0].lon));
                             } else {
                               alert("Location not found!");
                             }
                           });
                       }
                     }}
                   />
                   <button 
                     onClick={() => {
                       if (!searchQuery) return;
                       fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(searchQuery)}&format=json&limit=1`)
                         .then(res => res.json())
                         .then(data => {
                           if (data && data.length > 0) {
                             props.setStartLat(parseFloat(data[0].lat));
                             props.setStartLon(parseFloat(data[0].lon));
                           } else {
                             alert("Location not found!");
                           }
                         });
                     }}
                     className="px-3 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 rounded-none border border-blue-500/20 transition-all flex items-center justify-center"
                   >
                     <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                   </button>
                 </div>
                 <InputRow label="Origin Lat" value={props.startLat} onChange={props.setStartLat} />
                 <InputRow label="Origin Lon" value={props.startLon} onChange={props.setStartLon} />
                 <InputRow label="Heading (°)" value={props.heading} onChange={props.setHeading} type="number" />
                 <InputRow label="Speed (kts)" value={props.towfishSpeed} onChange={props.setTowfishSpeed} type="number" />
                 <InputRow label="Res (m/px)" value={props.resolution} onChange={props.setResolution} type="number" />
               </div>
             )}
          </div>
        </div>

      </div>
      )}

      {/* Execute Button */}
      <div className={`border-t border-slate-800 bg-slate-950 shrink-0 z-20 mt-auto transition-all ${isConfigOpen ? "p-5" : "p-3"}`}>
        <button 
          onClick={props.onRun}
          disabled={props.analyzing}
          title="Execute Analysis"
          className={`w-full py-3.5 font-bold text-[13px] rounded-none transition-all flex items-center justify-center gap-2 tracking-wide uppercase ${
            props.analyzing 
            ? 'bg-white/5 text-slate-500 cursor-not-allowed border border-slate-800' 
            : 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(37,99,235,0.3)] hover:shadow-[0_0_30px_rgba(37,99,235,0.5)] hover:-translate-y-0.5'
          } ${isConfigOpen ? "px-4" : "px-0"}`}
        >
          {props.analyzing ? (
            isConfigOpen ? (
              <><div className="flex gap-0.5"><div className="w-1 h-3 bg-slate-400 animate-pulse"></div><div className="w-1 h-3 bg-slate-500 animate-pulse" style={{animationDelay: '150ms'}}></div><div className="w-1 h-3 bg-slate-600 animate-pulse" style={{animationDelay: '300ms'}}></div></div> Processing</>
            ) : (
              <div className="flex gap-0.5"><div className="w-1 h-3 bg-slate-400 animate-pulse"></div><div className="w-1 h-3 bg-slate-500 animate-pulse" style={{animationDelay: '150ms'}}></div><div className="w-1 h-3 bg-slate-600 animate-pulse" style={{animationDelay: '300ms'}}></div></div>
            )
          ) : (
            isConfigOpen ? (
              <><Play size={16} weight="fill" /> Execute Analysis</>
            ) : (
              <Play size={16} weight="fill" />
            )
          )}
        </button>
      </div>
    </div>
  );
}
