import React, { useState, useEffect } from "react";
import { Terminal, Key, Sliders, HardDrives, ClockCounterClockwise, Aperture, Spinner } from "@phosphor-icons/react";

export default function Profile() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  
  const [prefs, setPrefs] = useState({
    operator_id: "OPR-7729-DELTA",
    email: "operator.delta@samudra.sys",
    mfa_enabled: true,
    engine: "YOLO11n + UNet (Standard)",
    alert_threshold: "Medium (Confidence > 50%)",
    theme: "Deep Space Dark (Default)",
    auto_stitch: true,
    api_key: "sk_live_...",
    role: "LEVEL 4 - ADMIN"
  });
  const [storage, setStorage] = useState({ used: 0, total: 10 * 1024 * 1024 * 1024, files: 0, sessions: 0, detections: 0 });
  const [revealKey, setRevealKey] = useState(false);

  const fetchPrefs = async () => {
    try {
      const token = localStorage.getItem("auth_token");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/preferences`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.status === "success") {
        setPrefs({
          operator_id: data.preferences.operator_id,
          email: data.preferences.email,
          mfa_enabled: data.preferences.mfa_enabled,
          engine: data.preferences.engine,
          alert_threshold: data.preferences.alert_threshold,
          theme: data.preferences.theme,
          auto_stitch: data.preferences.auto_stitch,
          api_key: data.preferences.api_key || "sk_live_mock",
          role: data.preferences.role || "LEVEL 4 - USER"
        });
        setStorage({
           used: data.preferences.storage_used_bytes || 0,
           total: data.preferences.storage_total_bytes || (10 * 1024 * 1024 * 1024),
           files: data.preferences.file_count || 0,
           sessions: data.preferences.db_sessions || 0,
           detections: data.preferences.db_detections || 0
        });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPrefs();
  }, []);

  const savePrefs = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem("auth_token");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/preferences`, {
        method: "POST",
        headers: { 
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(prefs)
      });
      const data = await res.json();
      if (data.status === "success") {
        setToast("Settings successfully saved and synced to database.");
        setTimeout(() => setToast(null), 3000);
        
        document.documentElement.setAttribute('data-theme', prefs.theme);
      }
    } catch (e) {
      console.error(e);
      setToast("Failed to save settings.");
      setTimeout(() => setToast(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-950 text-white min-h-[80vh]">
        <div className="flex gap-2 items-center"><div className="w-2 h-4 bg-blue-500 animate-pulse"></div>Loading Profile...</div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col p-4 md:p-8 overflow-y-auto no-scrollbar bg-slate-950 text-slate-100 min-h-full pb-20 relative">
      
      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-emerald-500/90 backdrop-blur border border-emerald-400 text-white px-6 py-3 shadow-lg z-[100] flex items-center gap-3">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
          <span className="text-sm font-medium tracking-wide">{toast}</span>
        </div>
      )}

      <div className="max-w-4xl mx-auto w-full">
        
        <div className="flex justify-between items-end mb-8">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-white mb-2">System Profile & Config</h2>
            <p className="text-sm text-slate-400 max-w-[65ch]">Manage operator credentials, API authentication keys, and underlying pipeline processing engine preferences.</p>
          </div>
          <button 
            onClick={savePrefs} 
            disabled={saving}
            className="hidden md:flex px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs uppercase tracking-widest transition-colors flex items-center gap-2 shadow-[0_0_15px_rgba(37,99,235,0.2)] hover:shadow-[0_0_20px_rgba(37,99,235,0.4)] disabled:opacity-50"
          >
            {saving ? <><div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> Syncing</> : 'Save Changes'}
          </button>
        </div>

        <div className="max-w-4xl w-full flex flex-col gap-12 bg-slate-900/50 border border-slate-800 p-8 md:p-12 shadow-xl">
          
          

          <section className="flex flex-col gap-8">
            <div className="flex flex-col gap-6">
              <h3 className="text-base font-semibold text-white flex items-center gap-2"><Sliders size={18} className="text-slate-400" /> Pipeline Preferences</h3>
              
              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Default Processing Engine</label>
                  <select value={prefs.engine} onChange={e => setPrefs({...prefs, engine: e.target.value})} className="w-full bg-slate-950 border border-slate-800 text-slate-300 px-3 py-2 rounded-none focus:outline-none focus:border-blue-500 text-sm appearance-none cursor-pointer">
                    <option>YOLO11n + UNet (Standard)</option>
                    <option>YOLO11x + DeepLab (High Fidelity)</option>
                    <option>Fast Heuristics (Low Power)</option>
                  </select>
                </div>
                
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Telemetry Alert Threshold</label>
                  <select value={prefs.alert_threshold} onChange={e => setPrefs({...prefs, alert_threshold: e.target.value})} className="w-full bg-slate-950 border border-slate-800 text-slate-300 px-3 py-2 rounded-none focus:outline-none focus:border-blue-500 text-sm appearance-none cursor-pointer">
                    <option>Medium (Confidence &gt; 50%)</option>
                    <option>High (Confidence &gt; 80%)</option>
                    <option>All Detections</option>
                  </select>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">System Theme</label>
                  <select value={prefs.theme} onChange={e => {
                      const newTheme = e.target.value;
                      setPrefs({...prefs, theme: newTheme});
                      document.documentElement.setAttribute('data-theme', newTheme);
                    }} className="w-full bg-slate-950 border border-slate-800 text-slate-300 px-3 py-2 rounded-none focus:outline-none focus:border-blue-500 text-sm appearance-none cursor-pointer">
                    <option>Deep Space Dark (Default)</option>
                    <option>Operator Light</option>
                    
                  </select>
                </div>

                <div className="flex items-start gap-3 mt-2">
                  <button 
                    onClick={() => setPrefs({...prefs, auto_stitch: !prefs.auto_stitch})}
                    className={`mt-1 shrink-0 w-10 h-5 p-0.5 transition-colors relative border rounded-full ${prefs.auto_stitch ? 'bg-blue-600 border-blue-500' : 'bg-slate-900 border-slate-700'}`}
                  >
                    <div className={`w-3.5 h-3.5 bg-white rounded-full transition-transform ${prefs.auto_stitch ? 'translate-x-5' : 'translate-x-0'}`} />
                  </button>
                  <div>
                    <div onClick={() => setPrefs({...prefs, auto_stitch: !prefs.auto_stitch})} className="text-sm font-medium text-slate-200 cursor-pointer">Auto-run Stitching on Session End</div>
                    <p className="text-xs text-slate-500 mt-1">Automatically compile a master mosaic when all files in a session are processed.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-6">
              <h3 className="text-base font-semibold text-white flex items-center gap-2"><HardDrives size={18} className="text-slate-400" /> Storage Quota</h3>
              <div className="flex flex-col gap-6">
                
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-slate-950 border border-slate-800 p-4 flex flex-col gap-1 items-center justify-center">
                     <span className="text-2xl font-mono text-blue-400 font-semibold">{storage.sessions}</span>
                     <span className="text-[10px] uppercase tracking-widest text-slate-500 font-medium">Active Sessions</span>
                  </div>
                  <div className="bg-slate-950 border border-slate-800 p-4 flex flex-col gap-1 items-center justify-center">
                     <span className="text-2xl font-mono text-emerald-400 font-semibold">{storage.detections}</span>
                     <span className="text-[10px] uppercase tracking-widest text-slate-500 font-medium">DB Detections</span>
                  </div>
                  <div className="bg-slate-950 border border-slate-800 p-4 flex flex-col gap-1 items-center justify-center">
                     <span className="text-2xl font-mono text-amber-400 font-semibold">{storage.files}</span>
                     <span className="text-[10px] uppercase tracking-widest text-slate-500 font-medium">Files on Disk</span>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <div className="flex justify-between text-xs text-slate-400 font-medium">
                    <span>{(storage.used / (1024 * 1024)).toFixed(2)} MB Physical Storage Used</span>
                    <span>{(storage.total / (1024 * 1024 * 1024)).toFixed(1)} GB System Limit</span>
                  </div>
                  <div className="h-2 w-full bg-slate-950 border border-slate-800 overflow-hidden relative">
                    <div className="absolute top-0 left-0 h-full bg-blue-500 transition-all duration-1000" style={{ width: `${Math.min(100, Math.max(1, (storage.used / storage.total) * 100))}%` }}></div>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">Real-time telemetry measuring physical disk allocation and dynamic SQLite table depth.</p>
                </div>
              </div>
            </div>

          </section>

        </div>
        
        <div className="md:hidden mt-8">
           <button onClick={savePrefs} disabled={saving} className="w-full py-4 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs uppercase tracking-widest shadow-lg flex items-center justify-center gap-2">
             {saving ? <><div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> Syncing</> : 'Save Changes'}
           </button>
        </div>

      </div>
    </div>
  );
}
