import React, { useState } from "react";
import { FilePdf, UploadSimple, Crosshair, DownloadSimple, MapTrifold, ArrowsOut, X, Target, MagnifyingGlassPlus, MagnifyingGlassMinus, Broadcast, CaretLeft, CaretRight, Download } from "@phosphor-icons/react/dist/ssr";
import dynamic from 'next/dynamic';
import { motion } from 'motion/react';
import 'leaflet/dist/leaflet.css';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';

const GeoMap = dynamic(() => import('./GeoMap'), { ssr: false });


const CLASS_COLORS: Record<string, string> = {
  "shipwreck": "#ef4444",
  "aircraft": "#3b82f6",
  "pipe": "#eab308",
  "cylinder": "#f97316",
  "ghost net": "#22c55e",
};

function InteractiveOverlay({ reportData, width, height }: { reportData: any[], width: number, height: number }) {
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  if (!width || !height) return null;

  return (
    <svg 
      viewBox={`0 0 ${width} ${height}`} 
      className="absolute inset-0 w-full h-full pointer-events-none"
      preserveAspectRatio="xMidYMid meet"
    >
      {reportData?.map((d: any, idx: number) => {
        if (!d.box) return null;
        const [x1, y1, x2, y2] = d.box;
        const w = x2 - x1;
        const h = y2 - y1;
        const isHovered = hoveredId === idx;
        const classNameStr = (d.class || "").toLowerCase();
        const baseColor = CLASS_COLORS[classNameStr] || "#3b82f6";
        const strokeColor = isHovered ? "#ffffff" : baseColor;
        
        // Convert hex to rgb for rgba fill
        let r=59, g=130, b=246;
        if (baseColor.startsWith('#')) {
            const hex = baseColor.replace('#', '');
            r = parseInt(hex.substring(0, 2), 16);
            g = parseInt(hex.substring(2, 4), 16);
            b = parseInt(hex.substring(4, 6), 16);
        }
        
        return (
          <g 
            key={idx} 
            className="pointer-events-auto cursor-pointer transition-all duration-200"
            onMouseEnter={() => setHoveredId(idx)}
            onMouseLeave={() => setHoveredId(null)}
          >
            {/* Box Background (Subtle) */}
            <rect 
              x={x1} y={y1} width={w} height={h} 
              fill={isHovered ? `rgba(${r}, ${g}, ${b}, 0.25)` : `rgba(${r}, ${g}, ${b}, 0.05)`}
              stroke={strokeColor} 
              strokeWidth={isHovered ? 4 : 2}
              className="transition-all duration-300"
            />
            
            {/* Corner Brackets */}
            <path d={`M ${x1} ${y1+15} L ${x1} ${y1} L ${x1+15} ${y1}`} fill="none" stroke="white" strokeWidth="3" />
            <path d={`M ${x2} ${y1+15} L ${x2} ${y1} L ${x2-15} ${y1}`} fill="none" stroke="white" strokeWidth="3" />
            <path d={`M ${x1} ${y2-15} L ${x1} ${y2} L ${x1+15} ${y2}`} fill="none" stroke="white" strokeWidth="3" />
            <path d={`M ${x2} ${y2-15} L ${x2} ${y2} L ${x2-15} ${y2}`} fill="none" stroke="white" strokeWidth="3" />
            
            {/* Tooltip logic */}
            {(isHovered || true) && (
              <g transform={`translate(${x1}, ${y1 > 40 ? y1 - 30 : y2 + 10})`} className="opacity-100 transition-opacity">
                <rect x="0" y="0" width="160" height="28" fill="rgba(2, 6, 23, 0.85)" rx="4" />
                <rect x="0" y="0" width="4" height="28" fill={baseColor} rx="2" />
                <text x="12" y="18" fill="white" fontSize="14" fontFamily="monospace" fontWeight="bold">
                  {d.class.toUpperCase()} 
                </text>
                <text x="100" y="18" fill={baseColor} fontSize="12" fontFamily="monospace">
                  {d.confidence_pct}%
                </text>
              </g>
            )}
            
            {isHovered && d.width_m && (
              <g transform={`translate(${x2 + 10}, ${y1})`}>
                <rect x="0" y="0" width="100" height="40" fill="rgba(2, 6, 23, 0.9)" stroke="rgba(255,255,255,0.1)" rx="4" />
                <text x="8" y="16" fill="#94a3b8" fontSize="10" fontFamily="sans-serif">SIZE</text>
                <text x="8" y="32" fill="white" fontSize="12" fontFamily="monospace">{d.width_m}×{d.height_m}m</text>
              </g>
            )}
          </g>
        );
      })}
    </svg>
  );
}



const TacticalVideoPlayer = ({ src }: { src: string }) => {
  return (
    <div className="relative w-full h-full group bg-black overflow-hidden flex justify-center items-center rounded-none border border-slate-700/50">
      <video src={src} autoPlay loop muted playsInline className="w-full h-full object-cover opacity-90 mix-blend-screen" />
      
      {/* Tactical HUD Overlay */}
      <div className="absolute inset-0 pointer-events-none border-[4px] border-black/20">
        <div className="absolute top-4 left-4 flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.8)]"></div>
          <span className="text-red-500 font-mono text-xs font-bold tracking-widest uppercase">LIVE UPLINK</span>
        </div>
        
        <div className="absolute top-4 right-4 flex flex-col items-end">
          <span className="text-emerald-400 font-mono text-[10px] tracking-widest">{new Date().toISOString().replace('T', ' ').substring(0, 19)} Z</span>
          <span className="text-emerald-400/70 font-mono text-[10px] tracking-widest">LAT: 13.1023° N | LON: 80.3012° E</span>
        </div>

        <div className="absolute bottom-4 left-4 text-blue-400/80 font-mono text-[10px] tracking-widest flex flex-col">
          <span>SYS: SAMUDRA-PRAHARI-X</span>
          <span>SENS: HIGH-FREQ-SONAR</span>
          <span>MODE: ACTIVE SEARCH</span>
        </div>
        
        {/* Crosshair */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-30">
           <div className="w-32 h-[1px] bg-emerald-400 absolute top-1/2 -translate-y-1/2 -left-16"></div>
           <div className="h-32 w-[1px] bg-emerald-400 absolute left-1/2 -translate-x-1/2 -top-16"></div>
           <div className="w-8 h-8 border border-emerald-400 rounded-full absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"></div>
        </div>
      </div>
    </div>
  );
};


export default function Viewer({ files, setFiles, results, setResults, analyzing, enableGeo, startLat, startLon }: any) {
  const [activeTab, setActiveTab] = useState("map"); 
  const [modalState, setModalState] = useState<{index: number, view: string} | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [stripViews, setStripViews] = useState<Record<number, string>>({});

  const updateImageStatus = async (filename: string, status: 'Approved' | 'Rejected') => {
    try {
      const formData = new FormData();
      formData.append("filename", filename);
      formData.append("status", status);
      const token = localStorage.getItem("auth_token");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/update_status`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      if (res.status === 401) {
        window.dispatchEvent(new Event('auth_error'));
        return;
      }
      
      if (!res.ok) {
         throw new Error(`Failed to update status, server responded with ${res.status}`);
      }

      const responseData = await res.json();
      if (responseData.status !== "success") {
          throw new Error("Update failed on backend");
      }
      
      if (setResults) {
        const newResults = [...results];
        const resIdx = newResults.findIndex((r: any) => r.name === filename);
        if (resIdx >= 0) {
          newResults[resIdx].image_status = status;
          newResults[resIdx].status = status;
          if (newResults[resIdx].report_data) {
            newResults[resIdx].report_data.forEach((d: any) => {
              d.image_status = status;
              d.status = status;
            });
          }
          setResults(newResults);
        }
      }
    } catch (e) {
      console.error("Failed to update status", e);
      alert("Failed to sync status with database. Please try again.");
    }
  };

  const masterResult = results.find((r: any) => r.is_master);
  const globalReportData = masterResult ? masterResult.report_data : results.filter((r: any) => !r.is_master).flatMap((r: any) => r.report_data || []);

  const sparklineData = React.useMemo(() => {
    if (!globalReportData || globalReportData.length === 0) return [{value: 0}];
    return globalReportData.map((d: any) => ({ value: d.confidence_pct || 0 }));
  }, [globalReportData]);

  const handleFileChange = (e: any) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleDownload = (data: any, format: 'json'|'csv'|'geojson'|'pdf', contextResults?: any[], title?: string) => {
    if (format === "pdf" && contextResults) {
       import("../../utils/pdfGenerator").then(m => m.generateTacticalPDF(contextResults, title === "AGGREGATED" ? "AGGREGATED" : "SINGLE_COMPONENT", title !== "AGGREGATED" ? title : undefined));
       return;
    }
    let content = "";
    let mime = "";
    if (format === 'json') {
       content = JSON.stringify(data, null, 2);
       mime = "application/json";
    } else if (format === 'csv') {
       if (data.length === 0) return;
       const headers = Object.keys(data[0]).join(",");
       const rows = data.map((row: any) => Object.values(row).join(",")).join("\n");
       content = headers + "\n" + rows;
       mime = "text/csv";
    } else if (format === 'geojson') {
       const features = data.filter((d:any) => d.lat && d.lon).map((d:any) => ({
         type: "Feature",
         geometry: { type: "Point", coordinates: [Number(d.lon), Number(d.lat)] },
         properties: d
       }));
       content = JSON.stringify({ type: "FeatureCollection", features }, null, 2);
       mime = "application/geo+json";
    }
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sonar_export.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const effectiveTab = (!masterResult && ['map', 'anomaly', 'segmentation'].includes(activeTab)) ? 'data' : activeTab;

  return (
    <div className="w-full h-full flex flex-col font-sans relative">
      {modalState && <ModalView state={modalState} results={results} onClose={() => setModalState(null)} onNavigate={(idx) => setModalState({...modalState, index: idx})} onUpdateView={(v) => setModalState({...modalState, view: v})} />}



      {analyzing ? (
        <div className="flex-1 flex flex-col items-center justify-center bg-slate-900 rounded-none border border-slate-800 shadow-inner relative overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
          <div className="relative flex flex-col items-center p-8 bg-slate-950  rounded-none border border-slate-800 shadow-2xl">
            <div className="w-64 h-1 bg-slate-800 mb-6 relative overflow-hidden"><div className="absolute top-0 left-0 h-full bg-blue-500 w-1/3 animate-[pulse_1.5s_ease-in-out_infinite]"></div></div>
            <h3 className="text-lg font-semibold text-white tracking-wider uppercase mb-2 flex items-center gap-2">
               Processing Telemetry
            </h3>
            <span className="text-slate-400 text-xs font-mono">Running detection & mapping engine</span>
          </div>
        </div>
      ) : results.length > 0 ? (
        <div className="flex-1 flex flex-col gap-8 overflow-y-auto no-scrollbar pb-10">
          
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2 }}
            className="flex flex-col gap-6"
          >

            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-2">
              <div className="col-span-1 md:col-span-2 md:row-span-2 bg-slate-900 border border-slate-800 shadow-md p-6 flex flex-col relative group rounded-none hover:bg-slate-800/50 transition-colors">
                <div className="flex justify-between items-start mb-6 z-10">
                  <div>
                    <h4 className="text-slate-400 text-xs font-medium uppercase tracking-wider">Total Anomalies</h4>
                    <div className="flex items-baseline gap-2 mt-2">
                      <span className="text-5xl font-semibold text-white tracking-tight">{globalReportData?.length || 0}</span>
                    </div>
                  </div>
                  <div className="p-3 bg-white/5 rounded-none border border-slate-800">
                    <Target size={20} className="text-blue-400" />
                  </div>
                </div>
                <div className="flex-1 min-h-[100px] w-full mt-auto opacity-70 group-hover:opacity-100 transition-all">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={sparklineData}>
                       <defs>
                         <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                           <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                           <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                         </linearGradient>
                       </defs>
                      <Area type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} fill="url(#colorValue)" isAnimationActive={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="col-span-1 md:col-span-2 bg-slate-900 border border-slate-800 shadow-md p-6 flex flex-col justify-between rounded-none">
                <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Spatial Frame</span>
                <div className="mt-4 flex items-end">
                  {masterResult ? (
                    <span className="text-3xl font-medium text-white tracking-tight">{masterResult.is_video ? "Video Stream" : masterResult.width + " × " + masterResult.height} <span className="text-sm text-slate-500 font-normal ml-1">px</span></span>
                  ) : (
                    <span className="text-3xl font-medium text-white tracking-tight">{results.filter((r: any) => !r.is_master).length} <span className="text-slate-500 font-normal text-xl mx-1">Components</span></span>
                  )}
                </div>
              </div>

              <div className="col-span-1 md:col-span-1 bg-slate-900 border border-slate-800 shadow-md p-6 flex flex-col justify-between rounded-none">
                <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Mean Confidence</span>
                <div className="mt-4">
                  <span className="text-3xl font-medium text-blue-400 tracking-tight">
                    {globalReportData?.length > 0 
                      ? (globalReportData.reduce((acc:any, curr:any) => acc + curr.confidence_pct, 0) / globalReportData.length).toFixed(1) + '%'
                      : '0.0%'}
                  </span>
                </div>
              </div>
              
              <div className="col-span-1 md:col-span-1 bg-slate-900 border border-slate-800 shadow-md p-6 flex flex-col justify-between rounded-none">
                 <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Mean Shadow</span>
                 <div className="mt-4">
                   <span className="text-3xl font-medium text-white tracking-tight">
                     {globalReportData?.length > 0 
                       ? (globalReportData.reduce((acc:any, curr:any) => acc + (curr.shadow_score || 0), 0) / globalReportData.length).toFixed(3)
                       : '0.000'}
                   </span>
                 </div>
              </div>
            </div>

            <div className="flex gap-2">
              {masterResult && (
                <>
                  <button onClick={() => setActiveTab('map')} className={`px-5 py-2.5 text-sm font-medium rounded-none transition-all ${effectiveTab === 'map' ? 'bg-blue-500/10 text-blue-400 shadow-inner' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
                    AI Overlay
                  </button>
                  {masterResult.anomaly_url && (
                    <button onClick={() => setActiveTab('anomaly')} className={`px-5 py-2.5 text-sm font-medium rounded-none transition-all ${effectiveTab === 'anomaly' ? 'bg-orange-500/10 text-orange-400 shadow-inner' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
                      Autoencoder
                    </button>
                  )}
                  {masterResult.segmentation_url && (
                    <button onClick={() => setActiveTab('segmentation')} className={`px-5 py-2.5 text-sm font-medium rounded-none transition-all ${effectiveTab === 'segmentation' ? 'bg-green-500/10 text-green-400 shadow-inner' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
                      UNet Mask
                    </button>
                  )}
                </>
              )}
              <button onClick={() => setActiveTab('data')} className={`px-5 py-2.5 text-sm font-medium rounded-none transition-all ${effectiveTab === 'data' ? 'bg-white/10 text-white shadow-inner' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
                Raw Telemetry
              </button>
              {enableGeo && (
                <button onClick={() => setActiveTab('geo')} className={`px-5 py-2.5 text-sm font-medium rounded-none transition-all ${effectiveTab === 'geo' ? 'bg-white/10 text-white shadow-inner' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
                  GeoSpatial Map
                </button>
              )}
            </div>

            <div className="bg-slate-900 border border-slate-800 shadow-md relative flex items-center justify-center min-h-[800px] h-[80vh] rounded-none overflow-hidden group">
               {effectiveTab === 'geo' && enableGeo ? (
                  <div className="w-full h-full min-h-[800px] h-[80vh]">
                    <GeoMap startLat={startLat} startLon={startLon} reportData={globalReportData} />
                  </div>
               ) : effectiveTab === 'data' ? (
                  <div className="flex-1 w-full overflow-auto h-[80vh]">
                    <table className="w-full text-left">
                      <thead className="text-xs uppercase tracking-wider text-slate-400 bg-white/[0.03] sticky top-0 ">
                        <tr>
                          <th className="px-6 py-4 font-medium">ID</th>
                          <th className="px-6 py-4 font-medium">Class</th>
                          <th className="px-6 py-4 font-medium">Conf</th>
                          <th className="px-6 py-4 font-medium">Shadow</th>
                          <th className="px-6 py-4 font-medium text-emerald-400">Height (m)</th>
                          <th className="px-6 py-4 font-medium">Lat</th>
                          <th className="px-6 py-4 font-medium">Lon</th>
                          <th className="px-6 py-4 font-medium">Size (m)</th>
                          <th className="px-6 py-4 font-medium text-emerald-400">Vol (m³)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 text-slate-300 font-mono text-sm">
                        {globalReportData?.map((d: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                            <td className="px-6 py-4">{d.id || idx+1}</td>
                            <td className="px-6 py-4 text-white font-sans font-medium">{d.class}</td>
                            <td className="px-6 py-4 text-blue-400">{d.confidence_pct}%</td>
                            <td className="px-6 py-4">{d.shadow_score !== undefined && d.shadow_score !== null ? d.shadow_score : "-"}</td>
                            <td className="px-6 py-4 font-bold text-white">{d.height_3d_m !== undefined && d.height_3d_m !== null ? d.height_3d_m : "-"}</td>
                            <td className="px-6 py-4">{d.lat ? Number(d.lat).toFixed(6) : "-"}</td>
                            <td className="px-6 py-4">{d.lon ? Number(d.lon).toFixed(6) : "-"}</td>
                            <td className="px-6 py-4">{d.width_m !== undefined ? `${d.width_m} × ${d.height_m}` : "-"}</td>
                            <td className="px-6 py-4 font-bold text-emerald-400">
                              {d.width_m && d.height_m && d.height_3d_m ? (d.width_m * d.height_m * d.height_3d_m).toFixed(1) : "-"}
                            </td>
                          </tr>
                        ))}
                        {!globalReportData?.length && <tr><td colSpan={9} className="text-center py-12 text-slate-500 font-medium font-sans">No anomalies detected in scan</td></tr>}
                      </tbody>
                    </table>
                  </div>
               ) : masterResult ? (
                  <div className="relative w-full h-full min-h-[800px] h-[80vh] bg-black/40 border-t border-slate-800">
                    {/* Floating Controls for Master Mosaic (Fixed to Screen) */}
                    <div className="absolute top-4 right-6 z-50 flex items-center gap-4">
                       <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700 p-1.5 flex gap-2 shadow-2xl rounded-none">
                          {(masterResult.status || masterResult.image_status) === 'Approved' ? (
                            <span className="text-xs font-bold text-green-400 bg-green-500/10 px-4 py-2 rounded-none border border-green-500/20">APPROVED</span>
                          ) : (masterResult.status || masterResult.image_status) === 'Rejected' ? (
                            <span className="text-xs font-bold text-red-400 bg-red-500/10 px-4 py-2 rounded-none border border-red-500/20">REJECTED</span>
                          ) : (
                            <>
                              <button onClick={() => updateImageStatus(masterResult.name, 'Approved')} className="text-xs font-bold text-green-400 hover:bg-green-500/20 px-4 py-2 rounded-none transition-colors border border-transparent hover:border-green-500/30">APPROVE</button>
                              <button onClick={() => updateImageStatus(masterResult.name, 'Rejected')} className="text-xs font-bold text-red-400 hover:bg-red-500/20 px-4 py-2 rounded-none transition-colors border border-transparent hover:border-red-500/30">REJECT</button>
                            </>
                          )}
                       </div>
                       
                       <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700 p-2 flex gap-2 shadow-2xl rounded-none">
                          <button onClick={() => setZoomLevel(prev => Math.max(0.5, prev - 0.25))} className="p-2 hover:bg-blue-500/20 text-slate-300 hover:text-blue-400 transition-colors rounded-none" title="Zoom Out"><MagnifyingGlassMinus size={18} /></button>
                          <div className="px-2 flex items-center justify-center font-mono text-xs text-blue-400 font-bold min-w-[60px]">{Math.round(zoomLevel * 100)}%</div>
                          <button onClick={() => setZoomLevel(prev => Math.min(3.0, prev + 0.25))} className="p-2 hover:bg-blue-500/20 text-slate-300 hover:text-blue-400 transition-colors rounded-none" title="Zoom In"><MagnifyingGlassPlus size={18} /></button>
                       </div>
                    </div>
                    
                    {/* Scrollable Container */}
                    <div className="w-full h-full overflow-auto custom-scrollbar flex flex-col items-center">
                        <div className="relative flex justify-center p-4 transition-all duration-300 origin-top" style={{ width: `${zoomLevel * 100}%` }}>
                      {effectiveTab === 'anomaly' && masterResult.anomaly_url ? (
                        <img src={(masterResult.anomaly_url?.startsWith("http") ? masterResult.anomaly_url : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${masterResult.anomaly_url}?t=${Date.now()}`)} alt="Anomaly Map" className="w-full h-auto object-contain shadow-2xl border border-slate-800" />
                      ) : effectiveTab === 'segmentation' && masterResult.segmentation_url ? (
                        <img src={(masterResult.segmentation_url?.startsWith("http") ? masterResult.segmentation_url : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${masterResult.segmentation_url}?t=${Date.now()}`)} alt="Segmentation Map" className="w-full h-auto object-contain shadow-2xl border border-slate-800" />
                      ) : masterResult.is_video ? (
                        <TacticalVideoPlayer src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${masterResult.processed_url || masterResult.raw_url}?t=${Date.now()}`} />
                      ) : (
                        <div className="relative w-full shadow-2xl border border-slate-800">
                          <img src={(masterResult.processed_url?.startsWith("http") ? masterResult.processed_url : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${masterResult.processed_url}?t=${Date.now()}`)} alt="Master Processed Map" className="w-full h-auto object-contain block" />
                          <InteractiveOverlay reportData={masterResult.report_data} width={masterResult.width} height={masterResult.height} />
                        </div>
                      )}
                    </div>
                    </div>
                    <button 
                      onClick={() => {
                         const idx = results.findIndex((r: any) => r.is_master);
                         setModalState({ index: idx, view: 'annotated' });
                      }}
                      className="absolute bottom-6 right-6 bg-white/10 hover:bg-blue-500  text-white border border-slate-800 p-3 rounded-none transition-all flex items-center gap-2 shadow-lg group-hover:scale-105"
                    >
                      <ArrowsOut size={16} /> <span className="text-sm font-medium">Enlarge</span>
                    </button>
                  </div>
               ) : (
                  <div className="relative w-full h-full flex justify-center items-center bg-black/40 min-h-[800px] h-[80vh]">
                    <p className="text-slate-500">Please select Raw Telemetry or GeoSpatial Map</p>
                  </div>
               )}
            </div>
            
            <div className="flex gap-3">
              <button onClick={() => handleDownload(globalReportData, "pdf", results, "AGGREGATED")} className="bg-white/5 hover:bg-white/10 text-white border border-slate-800 text-sm font-medium py-2.5 px-6 rounded-none transition-colors flex items-center gap-2">
                <FilePdf size={18} />
                Export PDF
              </button>
              <button onClick={() => handleDownload(globalReportData, 'csv')} className="bg-white/5 hover:bg-white/10 text-white border border-slate-800 text-sm font-medium py-2.5 px-6 rounded-none transition-colors flex items-center gap-2">
                <DownloadSimple size={16} /> Export CSV
              </button>
              <button onClick={() => handleDownload(globalReportData, 'json')} className="bg-white/5 hover:bg-white/10 text-white border border-slate-800 text-sm font-medium py-2.5 px-6 rounded-none transition-colors flex items-center gap-2">
                <DownloadSimple size={16} /> Export JSON
              </button>
              {enableGeo && (
                <button onClick={() => handleDownload(globalReportData, 'geojson')} className="bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 text-sm font-medium py-2.5 px-6 rounded-none transition-colors flex items-center gap-2">
                  <MapTrifold size={16} /> Export GeoJSON
                </button>
              )}
            </div>
          </motion.div>

          <div className="mt-12">
            <div className="flex items-center gap-3 mb-6">
              <h3 className="text-xl font-semibold text-white tracking-tight">Component Strips</h3>
            </div>
            
            <div className="flex flex-row overflow-x-auto snap-x snap-mandatory scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-900 gap-8 pb-8 px-1">
              {results.filter((r:any) => !r.is_master).map((res: any, idx: number) => {
                 const view = stripViews[idx] || 'annotated';
                 
                 let currentImgUrl = res.processed_url; // Base image is processed
                 if (view === 'raw') currentImgUrl = res.raw_url;
                 if (view === 'annotated') currentImgUrl = res.processed_url; // Overlays handled by React
                 if (view === 'anomaly' && res.anomaly_url) currentImgUrl = res.anomaly_url;
                 if (view === 'segmentation' && res.segmentation_url) currentImgUrl = res.segmentation_url;
                 
                 return (
                 <motion.div 
                   key={idx} 
                   initial={{ opacity: 0 }}
                   animate={{ opacity: 1 }}
                   transition={{ duration: 0.2 }}
                   className="snap-start shrink-0 min-w-[300px] w-[90%] sm:w-[85%] md:w-[75%] lg:w-[800px] xl:max-w-[800px] flex flex-col xl:flex-row gap-0 bg-slate-900 border border-slate-800 shadow-md rounded-lg overflow-hidden"
                 >
                   <div className="flex-[2] flex flex-col border-r border-slate-800">
                      
                      <div className="flex border-b border-slate-800 bg-slate-800/30">
                        <button onClick={() => setStripViews(p => ({...p, [idx]: 'raw'}))} className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider transition-colors ${view === 'raw' ? 'bg-white/10 text-white' : 'text-slate-500 hover:text-slate-300'}`}>Raw Feed</button>
                        <button onClick={() => setStripViews(p => ({...p, [idx]: 'processed'}))} className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider transition-colors ${view === 'processed' ? 'bg-white/10 text-white' : 'text-slate-500 hover:text-slate-300'}`}>DSP Filtered</button>
                        <button onClick={() => setStripViews(p => ({...p, [idx]: 'annotated'}))} className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider transition-colors ${view === 'annotated' ? 'bg-blue-500/10 text-blue-400' : 'text-slate-500 hover:text-slate-300'}`}>AI Overlay</button>
                        {res.anomaly_url && (
                           <button onClick={() => setStripViews(p => ({...p, [idx]: 'anomaly'}))} className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider transition-colors ${view === 'anomaly' ? 'bg-orange-500/10 text-orange-400' : 'text-slate-500 hover:text-slate-300'}`}>Anomaly</button>
                        )}
                        {res.segmentation_url && (
                           <button onClick={() => setStripViews(p => ({...p, [idx]: 'segmentation'}))} className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider transition-colors ${view === 'segmentation' ? 'bg-green-500/10 text-green-400' : 'text-slate-500 hover:text-slate-300'}`}>UNet Mask</button>
                        )}
                      </div>

                      <div className="flex-1 flex items-center justify-center p-6 relative min-h-[400px] bg-black/40 w-full h-full">
                        <div className="relative flex justify-center w-full h-full max-h-[400px]">
                          {res.is_video ? (
                             <TacticalVideoPlayer src={(currentImgUrl?.startsWith("http") ? currentImgUrl : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${currentImgUrl}`)} />
                          ) : (
                             <img src={(currentImgUrl?.startsWith("http") ? currentImgUrl : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${currentImgUrl}`)} alt={res.name} className="w-full h-full object-contain " />
                          )}
                          {view === 'annotated' && !res.is_video && (
                             <InteractiveOverlay reportData={res.report_data} width={res.width} height={res.height} />
                          )}
                        </div>
                        <button 
                          onClick={() => {
                             const idx = results.findIndex((r: any) => r.name === res.name);
                             setModalState({ index: idx, view: view });
                          }}
                          className="absolute bottom-4 right-4 bg-white/10 border border-slate-800 text-white hover:bg-blue-500 p-2.5 rounded-none transition-all flex items-center shadow-lg"
                        >
                          <ArrowsOut size={16} />
                        </button>
                      </div>
                      

                   </div>

                   <div className="flex-1 flex flex-col h-full xl:max-h-[480px]">
                      <div className="flex justify-between items-center px-6 py-5 border-b border-slate-800 bg-slate-800/30">
                         <h4 className="font-semibold text-sm text-white break-all max-w-xs xl:max-w-md">{res.name}</h4>
                         <div className="flex items-center gap-3">
                           {(res.status || res.image_status) === 'Approved' ? (
                              <span className="text-xs font-bold text-green-400 bg-green-500/10 px-3 py-1 rounded-none border border-green-500/20">APPROVED</span>
                           ) : (res.status || res.image_status) === 'Rejected' ? (
                              <span className="text-xs font-bold text-red-400 bg-red-500/10 px-3 py-1 rounded-none border border-red-500/20">REJECTED</span>
                           ) : (
                              <div className="flex gap-2">
                                <button onClick={() => updateImageStatus(res.name, 'Approved')} className="flex items-center justify-center gap-2 text-xs font-bold text-green-400 bg-green-500/10 hover:bg-green-500/20 px-4 py-1.5 rounded-none transition-transform active:translate-y-[1px] border border-green-500/20">APPROVE</button>
                                <button onClick={() => updateImageStatus(res.name, 'Rejected')} className="flex items-center justify-center gap-2 text-xs font-bold text-red-400 bg-red-500/10 hover:bg-red-500/20 px-4 py-1.5 rounded-none transition-transform active:translate-y-[1px] border border-red-500/20">REJECT</button>
                              </div>
                           )}
                           <span className="text-xs font-bold text-blue-400 bg-blue-500/10 px-3 py-1 rounded-none">{res.report_data?.length || 0} HITS</span>
                         </div>
                      </div>
                      
                      <div className="flex-1 overflow-auto">
                        <table className="w-full text-left">
                          <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-white/[0.01] sticky top-0 border-b border-slate-800">
                            <tr>
                              <th className="px-6 py-4 font-medium">Class</th>
                              <th className="px-6 py-4 font-medium text-blue-400">Conf</th>
                              <th className="px-6 py-4 font-medium">Size (m)</th>
                              <th className="px-6 py-4 font-medium text-emerald-400">Vol (m³)</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/5 text-slate-300 font-mono text-sm">
                            {res.report_data?.map((d: any, d_idx: number) => (
                              <tr key={d_idx} className="hover:bg-slate-800/30 transition-colors">
                                <td className="px-6 py-4 text-white font-sans font-medium">{d.class}</td>
                                <td className="px-6 py-4 text-blue-400">{d.confidence_pct}%</td>
                                <td className="px-6 py-4 whitespace-nowrap">{d.bounding_dimensions_m || "-"}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-emerald-400 font-bold">
                                  {d.width_m && d.height_m && d.height_3d_m ? (d.width_m * d.height_m * d.height_3d_m).toFixed(1) : "-"}
                                </td>
                              </tr>
                            ))}
                            {!res.report_data?.length && <tr><td colSpan={3} className="text-center py-10 text-slate-500 font-sans text-sm">No signature detected</td></tr>}
                          </tbody>
                        </table>
                      </div>
                      
                      <div className="p-4 border-t border-slate-800 bg-white/[0.01] flex justify-end gap-2 shrink-0">
                          <button onClick={() => handleDownload(res.report_data, "pdf", [res], res.name)} className="bg-white/5 hover:bg-white/10 text-white border border-slate-800 text-xs font-medium py-2 px-4 rounded-none transition-colors flex items-center gap-1.5">
                            <FilePdf size={14} />
                            PDF
                          </button>
                        <button onClick={() => handleDownload(res.report_data, 'csv')} className="bg-white/5 hover:bg-white/10 text-white border border-slate-800 text-xs font-medium py-2 px-4 rounded-none transition-colors flex items-center gap-1.5">
                          <DownloadSimple size={14} /> CSV
                        </button>
                        <button onClick={() => handleDownload(res.report_data, 'json')} className="bg-white/5 hover:bg-white/10 text-white border border-slate-800 text-xs font-medium py-2 px-4 rounded-none transition-colors flex items-center gap-1.5">
                          <DownloadSimple size={14} /> JSON
                        </button>
                        {enableGeo && (
                          <button onClick={() => handleDownload(res.report_data, 'geojson')} className="bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 text-xs font-medium py-2 px-4 rounded-none transition-colors flex items-center gap-1.5">
                            <MapTrifold size={14} /> GeoJSON
                          </button>
                        )}
                      </div>
                   </div>
                 </motion.div>
              )})}
            </div>
          </div>
          
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center">
           <div className="p-8 bg-white/5 rounded-none border border-slate-800 mb-6 shadow-xl">
             <Broadcast size={48} className="text-slate-500" weight="light" />
           </div>
           <p className="text-lg font-medium text-slate-300">Awaiting Telemetry</p>
           <p className="text-sm text-slate-500 mt-2">Upload sonar scans to begin processing</p>
        </div>
      )}
    </div>
  );
}

function ModalView({ state, results, onClose, onNavigate, onUpdateView }: { state: any, results: any[], onClose: () => void, onNavigate: (idx: number) => void, onUpdateView: (view: string) => void }) {
  const [isNativeSize, setIsNativeSize] = useState(false);

  const currentRes = results[state.index];

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') onNavigate((state.index + 1) % results.length);
      if (e.key === 'ArrowLeft') onNavigate((state.index - 1 + results.length) % results.length);
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.index, results.length, onClose, onNavigate]);

  if (!currentRes) return null;

  let currentImgUrl = currentRes.processed_url;
  if (state.view === 'raw') currentImgUrl = currentRes.raw_url;
  if (state.view === 'anomaly' && currentRes.anomaly_url) currentImgUrl = currentRes.anomaly_url;
  if (state.view === 'segmentation' && currentRes.segmentation_url) currentImgUrl = currentRes.segmentation_url;
  
  const fullUrl = (currentImgUrl?.startsWith("http") ? currentImgUrl : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${currentImgUrl}`);
  const showOverlay = (state.view === 'annotated' || state.view === 'map');

  const handleDownloadImage = () => {
    const a = document.createElement('a');
    a.href = fullUrl;
    a.download = `${currentRes.name.replace('.jpg', '')}_${state.view}.jpg`;
    a.click();
  };

  return (
    <div className="fixed inset-0 z-[100] bg-slate-950  flex flex-col">
      <div className="flex justify-between items-center p-4 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex bg-white/5 rounded-none p-1 border border-slate-800">
            <button onClick={() => onUpdateView('raw')} className={`px-3 py-1.5 text-xs font-semibold rounded-none ${state.view === 'raw' ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white'}`}>Raw</button>
            <button onClick={() => onUpdateView('processed')} className={`px-3 py-1.5 text-xs font-semibold rounded-none ${state.view === 'processed' ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white'}`}>DSP Filtered</button>
            <button onClick={() => onUpdateView('annotated')} className={`px-3 py-1.5 text-xs font-semibold rounded-none ${state.view === 'annotated' || state.view === 'map' ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400 hover:text-white'}`}>AI Overlay</button>
            {currentRes.anomaly_url && (
              <button onClick={() => onUpdateView('anomaly')} className={`px-3 py-1.5 text-xs font-semibold rounded-none ${state.view === 'anomaly' ? 'bg-orange-500/20 text-orange-400' : 'text-slate-400 hover:text-white'}`}>Anomaly</button>
            )}
            {currentRes.segmentation_url && (
              <button onClick={() => onUpdateView('segmentation')} className={`px-3 py-1.5 text-xs font-semibold rounded-none ${state.view === 'segmentation' ? 'bg-green-500/20 text-green-400' : 'text-slate-400 hover:text-white'}`}>UNet Mask</button>
            )}
          </div>
          <button className="flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white transition-colors bg-white/5 border border-slate-800 rounded-none px-4 py-2"
            onClick={() => setIsNativeSize(!isNativeSize)}
          >
            {isNativeSize ? <MagnifyingGlassMinus size={16} /> : <MagnifyingGlassPlus size={16} />}
            {isNativeSize ? 'Fit to Viewport' : 'Native Resolution'}
          </button>
          
          <button 
            className="flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white transition-colors bg-white/5 border border-slate-800 rounded-none px-4 py-2"
            onClick={handleDownloadImage}
          >
            <Download size={16} /> Save Image
          </button>
          
          <div className="text-slate-400 text-sm font-medium ml-4 border-l border-slate-800 pl-4 truncate max-w-[150px] sm:max-w-xs md:max-w-md">
             {currentRes.name} <span className="uppercase text-blue-400 ml-2">[{state.view}]</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => onNavigate((state.index - 1 + results.length) % results.length)} className="text-slate-400 hover:text-white p-2 bg-white/5 hover:bg-white/10 rounded-none transition-all">
             <CaretLeft size={20} />
          </button>
          <span className="text-sm font-medium text-slate-300 px-2">{state.index + 1} / {results.length}</span>
          <button onClick={() => onNavigate((state.index + 1) % results.length)} className="text-slate-400 hover:text-white p-2 bg-white/5 hover:bg-white/10 rounded-none transition-all">
             <CaretRight size={20} />
          </button>
          <div className="w-px h-6 bg-white/10 mx-2"></div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-2 bg-white/5 hover:bg-white/10 rounded-none transition-all">
            <X size={20} />
          </button>
        </div>
      </div>
      
      <div 
        className={`flex-1 w-full overflow-auto flex items-center justify-center p-8 ${!currentRes.is_video && isNativeSize ? 'cursor-zoom-out items-start' : !currentRes.is_video ? 'cursor-zoom-in' : ''}`}
        onClick={() => !currentRes.is_video && setIsNativeSize(!isNativeSize)}
      >
        <div className={`relative flex justify-center ${isNativeSize ? '' : 'w-full h-full'}`}>
            {currentRes.is_video ? (
              <TacticalVideoPlayer src={fullUrl} />
            ) : (
              <img 
                src={fullUrl} 
                alt="Enlarged" 
                className={isNativeSize ? "max-w-none shadow-2xl" : "w-full h-full max-h-full object-contain shadow-2xl "} 
              />
            )}
            {showOverlay && currentRes.report_data && !currentRes.is_video && (
                <div className="absolute inset-0 pointer-events-none">
                   <InteractiveOverlay reportData={currentRes.report_data} width={currentRes.width} height={currentRes.height} />
                </div>
            )}
        </div>
      </div>
    </div>
  );
}
