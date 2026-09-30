"use client";
import React, { useState, useEffect } from "react";
import { House, User } from "@phosphor-icons/react";
import Login from "@/components/auth/Login";
import Sidebar from "@/components/layout/Sidebar";
import Viewer from "@/components/dashboard/Viewer";
import ControlPanel from "@/components/dashboard/ControlPanel";
import MasterLedger from "@/components/dashboard/MasterLedger";
import Profile from "@/components/dashboard/Profile";
import LandingPage from "@/components/layout/LandingPage";

function AuthenticatedDashboard({ token, handleLogout }: { token: string; handleLogout: () => void }) {
  const [activeTab, setActiveTab] = useState("analysis");

  // Global state for pipeline
  const [enableStitching, setEnableStitching] = useState(true);
  const [compileVideo, setCompileVideo] = useState(false);
  const [stitchDirection, setStitchDirection] = useState("Vertical");
  const [denoise, setDenoise] = useState(true);
  const [nadir, setNadir] = useState(false);
  const [slant, setSlant] = useState(false);
  const [nadirSide, setNadirSide] = useState("left");
  const [confThresh, setConfThresh] = useState(0.15);
  const [keepThresh, setKeepThresh] = useState(0.25);
  const [unetThresh, setUnetThresh] = useState(0.3);
  const [weightsPath, setWeightsPath] = useState("models/v3/yolo11n.onnx");
  const [enableGeo, setEnableGeo] = useState(false);
  
  // Geo anchoring parameters
  const [startLat, setStartLat] = useState(13.1);
  const [startLon, setStartLon] = useState(80.3);
  const [heading, setHeading] = useState(0.0);
  const [towfishSpeed, setTowfishSpeed] = useState(3.0);
  const [resolution, setResolution] = useState(0.1);
  
  const [analyzing, setAnalyzing] = useState(false);
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [files, setFiles] = useState<File[]>([]);

  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const activeSessionRef = React.useRef(activeSessionId);
  React.useEffect(() => { activeSessionRef.current = activeSessionId; }, [activeSessionId]);

  const createNewSession = async (name?: string) => {
      const sessionName = name || `Sonar Session ${sessions.length + 1}`;
      const formData = new FormData();
      formData.append("name", sessionName);
      try {
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/sessions`, {
              method: "POST",
              headers: { Authorization: `Bearer ${token}` },
              body: formData
          });
          const data = await res.json();
          if (data.status === "success") {
              setSessions(prev => [data.session, ...prev]);
              setActiveSessionId(data.session.id);
              setResults([]);
              setFiles([]);
          }
      } catch (e) { console.error("Network Error:", (e as Error)?.message || String(e)); }
  };

  const deleteSession = async (sessionId: string) => {
    if (!sessionId) {
       console.error("No sessionId provided to deleteSession");
       return;
    }
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/sessions/${sessionId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!res.ok) {
         const errText = await res.text();
         console.error(`Backend returned ${res.status}: ${errText}`);
         return;
      }
      
      const data = await res.json();
      if (data.status === "success") {
        const newSessions = sessions.filter(s => s.id !== sessionId);
        setSessions(newSessions);
        if (activeSessionId === sessionId) {
          if (newSessions.length > 0) {
            setActiveSessionId(newSessions[0].id);
          } else {
            setActiveSessionId(null);
            setResults([]);
            setFiles([]);
          }
        }
      }
    } catch (e) {
      console.error("Fetch failed entirely:", e);
      alert("Could not connect to the backend server. Is it running?");
    }
  };

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/preferences`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => res.json())
      .then(data => {
         if (data.status === "success") {
            document.documentElement.setAttribute('data-theme', data.preferences.theme);
            // Store auto-stitch preference globally or in localStorage for easy access
            localStorage.setItem("auto_stitch", data.preferences.auto_stitch ? "true" : "false");
         }
      }).catch(e => console.error(e));

    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/sessions`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => res.json())
      .then(data => {
         if (data.status === "success") {
            setSessions(data.sessions);
            const saved = localStorage.getItem("active_session_id");
            if (saved && data.sessions.find((s:any) => s.id === saved)) {
                setActiveSessionId(saved);
            } else if (data.sessions.length > 0) {
                setActiveSessionId(data.sessions[0].id);
            } else {
                if (!(window as any).isCreatingInitialSession) {
                    (window as any).isCreatingInitialSession = true;
                    createNewSession("Sonar Session 1").finally(() => {
                        setTimeout(() => (window as any).isCreatingInitialSession = false, 1000);
                    });
                }
            }
         }
      }).catch(e => console.error("Network Error:", (e as Error)?.message || String(e)));
  }, [token]);

  useEffect(() => {
     if (activeSessionId) {
         localStorage.setItem("active_session_id", activeSessionId);
         if (activeTab === "analysis") {
             fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/processing_history?session_id=${activeSessionId}`, { headers: { Authorization: `Bearer ${token}` } })
             .then(res => res.json())
             .then(data => {
                if (data.status === "success" && data.history.length > 0) {
                   const loadedResults = data.history.map((h: any) => ({
                       name: h.filename,
                       vis_url: h.map_stitching_output || h.processed_image_url,
                       processed_url: h.processed_image_url,
                       raw_url: h.uploaded_image_url || h.processed_image_url,
                       report_data: typeof h.report_data === 'string' ? JSON.parse(h.report_data || "[]") : h.report_data,
                       width: h.width,
                       height: h.height,
                       anomaly_url: h.anomaly_url,
                       segmentation_url: h.segmentation_url,
                       is_master: h.filename === "master_mosaic" || h.is_video === true,
                       is_video: h.is_video === true
                   }));
                   loadedResults.sort((a: any, b: any) => (b.is_master ? 1 : 0) - (a.is_master ? 1 : 0));
                   setResults(loadedResults);
                } else {
                   setResults([]);
                }
             }).catch(e => console.error("Network Error:", (e as Error)?.message || String(e)));
         }
     }
  }, [activeSessionId, activeTab, token]);

  React.useEffect(() => {
    if (activeTab === "history") {
      setLoadingHistory(true);
      const url = activeSessionId ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/history?session_id=${activeSessionId}` : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/history`;
      fetch(url, { headers: { Authorization: `Bearer ${token}` } })
        .then(res => {
          if (res.status === 401) {
            window.dispatchEvent(new Event('auth_error'));
            throw new Error('Unauthorized');
          }
          return res.json();
        })
        .then(data => {
          if (data.status === "success") {
            setHistoryData(data.history);
          }
        })
        .catch(e => console.error("Network error:", e)).finally(() => setLoadingHistory(false));
    }
  }, [activeTab, activeSessionId, token]);


  const exportDatabase = () => {
    if (historyData.length === 0) return;
    const headers = Object.keys(historyData[0]).join(",");
    const rows = historyData.map((row: any) => Object.values(row).map(val => `"${val}"`).join(",")).join("\n");
    const blob = new Blob([headers + "\n" + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'samudra_sonar_sessions_database_full.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const clearDatabase = async () => {
    try {
      const formData = new FormData();
      if (activeSessionId) {
          formData.append("session_id", activeSessionId);
      }
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/clear_history`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: formData });
      if (res.status === 401) {
        window.dispatchEvent(new Event('auth_error'));
        return;
      }
      setHistoryData([]);
    } catch (e) {
      console.error("Network Error:", (e as Error)?.message || String(e));
    }
  };

  const runAnalysis = async () => {
    if (files.length === 0) return;
    setAnalyzing(true);
    
    const formData = new FormData();
    files.forEach(file => formData.append("files", file));
    
    if (activeSessionId) {
        formData.append("session_id", activeSessionId);
    }
    
    formData.append("enable_denoise", denoise ? "true" : "false");
    formData.append("enable_nadir", nadir ? "true" : "false");
    formData.append("enable_slant", slant ? "true" : "false");
    formData.append("nadir_side", nadirSide);
    formData.append("conf_thresh", confThresh.toString());
    formData.append("keep_thresh", keepThresh.toString());
    formData.append("unet_thresh", unetThresh.toString());
    formData.append("weights_path", weightsPath);
    
    formData.append("enable_geo", enableGeo ? "true" : "false");
    formData.append("start_lat", startLat.toString());
    formData.append("start_lon", startLon.toString());
    formData.append("heading", heading.toString());
    formData.append("towfish_speed", towfishSpeed.toString());
    formData.append("resolution", resolution.toString());
    
    const autoStitchPref = localStorage.getItem("auto_stitch") === "true";
    const doStitch = (enableStitching || autoStitchPref) && files.length > 1;
    const isDirectVideo = files.length === 1 && files[0].name.toLowerCase().endsWith('.mp4');
    let endpoint = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/analyze`;
    if (compileVideo || isDirectVideo) {
      endpoint = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/analyze_video`;
    } else if (doStitch) {
      endpoint = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/stitch`;
    }
    
    if (doStitch && !compileVideo) {
       formData.append("stitch_direction", stitchDirection);
    }
    
    const submittedSessionId = activeSessionId;
    
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      if (res.status === 401) {
         handleLogout();
         return;
      }
      const data = await res.json();
      
      if (activeSessionRef.current !== submittedSessionId) return;
      
      if (data.status === "success") {
        if (compileVideo || isDirectVideo) {
           const videoResult = {
              name: "video_feed",
              vis_url: data.annotated_video,
              processed_url: data.annotated_video,
              raw_url: data.raw_video,
              is_master: true,
              is_video: true,
              report_data: data.report_data || []
           };
           const frameResults = (data.results || []).map((r:any) => ({
                name: r.name,
                vis_url: r.vis_url,
                processed_url: r.processed_url,
                raw_url: r.raw_url,
                anomaly_url: r.anomaly_url,
                segmentation_url: r.segmentation_url,
                report_data: r.report_data,
                width: r.width,
                height: r.height,
                is_master: false
           }));
           setResults([videoResult, ...frameResults]);
        } else if (doStitch) {
           setResults([
              {
                name: "master_mosaic",
                vis_url: data.master_map_url,
                processed_url: data.master_clean_url || data.master_map_url,
                raw_url: data.master_clean_url || data.master_map_url,
                anomaly_url: data.master_anomaly_url,
                segmentation_url: data.master_segmentation_url,
                report_data: data.report_data,
                width: data.width,
                height: data.height,
                is_master: true
              },
              ...(data.individual_results || [])
           ]);
        } else {
           setResults(data.results);
        }
      }
    } catch (e: any) {
      if (e.name === 'TypeError' && e.message.includes('NetworkError')) {
          console.warn("Analysis request was aborted or the server is restarting.");
      } else {
          console.error("Analysis Error:", e?.message || String(e));
      }
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="flex w-full h-full bg-transparent text-slate-100 relative selection:bg-zinc-800 selection:text-white font-sans tracking-tight">

      <div className="z-10 relative flex w-full h-full">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} sessions={sessions} activeSessionId={activeSessionId} setActiveSessionId={setActiveSessionId} createNewSession={() => createNewSession()} deleteSession={deleteSession} />
        <main className="flex-1 flex flex-col h-full overflow-hidden relative bg-slate-950">
          <header className="h-16 border-b border-slate-800 flex items-center px-8 shrink-0 bg-slate-900  z-20">
            <h1 className="text-sm font-semibold text-slate-300 flex items-center gap-3">
              <span className="text-blue-400 uppercase tracking-widest">{activeTab === "analysis" ? "Sonar Pipeline Environment" : activeTab === "ledger" ? "Master Ledger" : activeTab === "profile" ? "System Profile" : "Sonar Sessions Database"}</span>
            </h1>
            <div className="ml-auto flex items-center gap-4">
              <div className="hidden md:flex items-center gap-2">
                <button onClick={() => setActiveTab('analysis')} className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-white transition-colors bg-slate-800 hover:bg-slate-700 rounded-none">
                  <House size={14} weight="bold" /> Home
                </button>
                <button onClick={() => setActiveTab('profile')} className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-white transition-colors bg-slate-800 hover:bg-slate-700 rounded-none">
                  <User size={14} weight="bold" /> Profile
                </button>
              </div>
              <button onClick={handleLogout} className="text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-white transition-colors bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-none">
                Logout
              </button>
            </div>
          </header>
          {activeTab === "ledger" ? (
            <MasterLedger />
          ) : activeTab === "profile" ? (
            <Profile />
          ) : activeTab === "history" ? (
             <div className="flex-1 flex flex-col p-8 overflow-hidden bg-slate-950 text-slate-100">
                <div className="flex justify-between items-end mb-8">
                  <div>
                    <h2 className="text-2xl font-semibold tracking-tight text-white mb-2">Persistent Sonar Session Database</h2>
                    <p className="text-sm text-slate-400 max-w-[65ch]">Historical archive of all globally detected targets.</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <button onClick={exportDatabase} className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-none transition-colors shadow-sm">
                      Export CSV
                    </button>
                    <button onClick={clearDatabase} className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-none transition-colors shadow-sm">
                      Clear Database
                    </button>
                  </div>
                </div>
                
                <div className="flex-1 overflow-auto rounded-none border border-slate-800 bg-slate-900 shadow-inner">
                  {loadingHistory ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="flex flex-col items-center gap-4">
                        <div className="flex gap-1"><div className="w-2 h-4 bg-blue-500 animate-pulse"></div><div className="w-2 h-4 bg-blue-500/50 animate-pulse" style={{animationDelay: '150ms'}}></div><div className="w-2 h-4 bg-blue-500/20 animate-pulse" style={{animationDelay: '300ms'}}></div></div>
                        <span className="text-sm text-slate-400 font-medium tracking-wide uppercase">Loading historical database...</span>
                      </div>
                    </div>
                  ) : historyData.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center p-8">
                      <h3 className="text-lg font-semibold text-slate-300 mb-2">Sonar Sessions Database Empty</h3>
                      <p className="text-sm text-slate-500 max-w-sm">Run a sonar pipeline analysis to automatically log detections.</p>
                    </div>
                  ) : (
                    <table className="w-full text-left text-sm whitespace-nowrap">
                      <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-slate-900 sticky top-0 z-10 border-b border-slate-800">
                        <tr>
                          <th className="px-6 py-4 font-semibold">ID</th>
                          <th className="px-6 py-4 font-semibold">File</th>
                          <th className="px-6 py-4 font-semibold">Class</th>
                          <th className="px-6 py-4 font-semibold">Conf</th>
                          <th className="px-6 py-4 font-semibold">Lat</th>
                          <th className="px-6 py-4 font-semibold">Lon</th>
                          <th className="px-6 py-4 font-semibold text-blue-400">3D Est (m)</th>
                          <th className="px-6 py-4 font-semibold text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 text-slate-300 font-mono text-[13px]">
                        {historyData.map((d: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-800/50 transition-colors group">
                            <td className="px-6 py-4 text-slate-500">{d.id}</td>
                            <td className="px-6 py-4 text-slate-300 break-all max-w-[200px] truncate" title={d.filename}>{d.filename}</td>
                            <td className="px-6 py-4 font-sans font-medium text-slate-200">{d.class}</td>
                            <td className="px-6 py-4 text-blue-400 font-semibold">{d.confidence}%</td>
                            <td className="px-6 py-4">{d.lat ? d.lat.toFixed(6) : "-"}</td>
                            <td className="px-6 py-4">{d.lon ? d.lon.toFixed(6) : "-"}</td>
                            <td className="px-6 py-4 font-semibold text-blue-400">{d.height_3d_m || "-"}</td>
                            <td className="px-6 py-4 text-right font-sans">
                              {(d.status || d.image_status) === 'Approved' ? <span className="text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-none border border-emerald-500/20 tracking-wider uppercase">Approved</span> : 
                               (d.status || d.image_status) === 'Rejected' ? <span className="text-[11px] font-bold text-rose-400 bg-rose-500/10 px-3 py-1.5 rounded-none border border-rose-500/20 tracking-wider uppercase">Rejected</span> : 
                               <span className="text-[11px] font-bold text-amber-400 bg-amber-500/10 px-3 py-1.5 rounded-none border border-amber-500/20 tracking-wider uppercase">Pending</span>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
             </div>
          ) : (
             <div className="flex-1 flex overflow-hidden bg-slate-950">
            <div className="flex-1 overflow-y-auto p-4 lg:p-6 no-scrollbar relative">
              <Viewer 
                files={files} 
                setFiles={setFiles} 
                results={results} 
                analyzing={analyzing}
                enableGeo={enableGeo}
                startLat={startLat}
                startLon={startLon}
                setResults={setResults}
              />
            </div>
            <div className="shrink-0 bg-slate-900 hidden xl:block z-20 shadow-2xl h-full">
              <ControlPanel 
                 files={files} setFiles={setFiles}
                 enableStitching={enableStitching} setEnableStitching={setEnableStitching}
                 compileVideo={compileVideo} setCompileVideo={setCompileVideo}
                 stitchDirection={stitchDirection} setStitchDirection={setStitchDirection}
                 denoise={denoise} setDenoise={setDenoise}
                 nadir={nadir} setNadir={setNadir}
                 slant={slant} setSlant={setSlant}
                 nadirSide={nadirSide} setNadirSide={setNadirSide}
                 confThresh={confThresh} setConfThresh={setConfThresh}
                 keepThresh={keepThresh} setKeepThresh={setKeepThresh}
                 unetThresh={unetThresh} setUnetThresh={setUnetThresh}
                 weightsPath={weightsPath} setWeightsPath={setWeightsPath}
                 enableGeo={enableGeo} setEnableGeo={setEnableGeo}
                 startLat={startLat} setStartLat={setStartLat}
                 startLon={startLon} setStartLon={setStartLon}
                 heading={heading} setHeading={setHeading}
                 towfishSpeed={towfishSpeed} setTowfishSpeed={setTowfishSpeed}
                 resolution={resolution} setResolution={setResolution}
                 onRun={runAnalysis}
                 analyzing={analyzing}
              />
            </div>
          </div>
          )}
      </main>
      </div>
    </div>
  );
}

export default function Dashboard() {

  const [token, setToken] = useState<string | null>(null);
  const [showLanding, setShowLanding] = useState<boolean>(true);

  useEffect(() => {
    const savedToken = localStorage.getItem("auth_token");
    if (savedToken) {
      setToken(savedToken);
      setShowLanding(false); // Skip landing if already logged in
    }
  }, []);

  const handleLogin = (newToken: string) => {
    localStorage.setItem("auth_token", newToken);
    setToken(newToken);
  };

  const handleLogout = async () => {
    const tk = localStorage.getItem("auth_token");
    if (tk) {
      try {
        await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${tk}` }
        });
      } catch (e) {
        console.error("Logout error", e);
      }
    }
    localStorage.removeItem("auth_token");
    setToken(null);
    setShowLanding(true); // Return to landing on logout
  };

  useEffect(() => {
    const onAuthError = () => handleLogout();
    window.addEventListener('auth_error', onAuthError);
    return () => window.removeEventListener('auth_error', onAuthError);
  }, []);

  if (showLanding) {
    return <LandingPage onEnter={() => setShowLanding(false)} />;
  }

  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

  return <AuthenticatedDashboard token={token} handleLogout={handleLogout} />;
}
