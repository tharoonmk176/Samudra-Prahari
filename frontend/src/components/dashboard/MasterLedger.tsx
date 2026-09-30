import React, { useState, useEffect, useCallback } from "react";
import { DownloadSimple, ArrowClockwise } from "@phosphor-icons/react";

interface LedgerRecord {
  id: number;
  filename: string;
  uploaded_image_url?: string;
  processed_image_url?: string;
  map_stitching_output?: string;
  confidence?: number | null;
  status?: string;
}

export default function MasterLedger() {
  const [data, setData] = useState<LedgerRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const getFullUrl = (url: string) => {
    if (url.startsWith('http')) return url;
    return url.startsWith('/') ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${url}` : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/${url}`;
  };

  const fetchLedger = useCallback(() => {
    setLoading(true);
    const token = localStorage.getItem("auth_token");
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/processing_history`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => {
        if (res.status === 401) {
          window.dispatchEvent(new Event('auth_error'));
          throw new Error('Unauthorized');
        }
        return res.json();
      })
      .then(resData => {
        if (resData.status === "success") {
          setData(resData.history);
        }
      })
      .catch(err => console.error("Network Error:", (err as any)?.message || String(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchLedger();
  }, [fetchLedger]);

  return (
    <div className="flex-1 flex flex-col p-8 overflow-hidden bg-slate-950 text-slate-100">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-white mb-2">Master Ledger Dashboard</h2>
          <p className="text-sm text-slate-400 max-w-[65ch]">Comprehensive overview of all processed outputs and analysis history.</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchLedger} className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 rounded-none transition-colors border border-white/10" title="Refresh Data">
            <ArrowClockwise size={16} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto rounded-none border border-slate-800 bg-slate-900 shadow-inner">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-4">
              <div className="flex gap-1"><div className="w-2 h-4 bg-blue-500 animate-pulse"></div><div className="w-2 h-4 bg-blue-500/50 animate-pulse" style={{animationDelay: '150ms'}}></div><div className="w-2 h-4 bg-blue-500/20 animate-pulse" style={{animationDelay: '300ms'}}></div></div>
              <span className="text-sm text-slate-400 font-medium tracking-wide uppercase">Syncing Ledger...</span>
            </div>
          </div>
        ) : data.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <h3 className="text-lg font-semibold text-slate-300 mb-2">Ledger Empty</h3>
            <p className="text-sm text-slate-500 max-w-sm">Run a sonar pipeline analysis to populate records.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-slate-900 sticky top-0 z-10 border-b border-slate-800">
              <tr>
                <th className="px-6 py-4 font-semibold">ID</th>
                <th className="px-6 py-4 font-semibold">Filename</th>
                <th className="px-6 py-4 font-semibold text-center">Uploaded</th>
                <th className="px-6 py-4 font-semibold text-center">Processed</th>
                <th className="px-6 py-4 font-semibold text-center">Stitching</th>
                <th className="px-6 py-4 font-semibold">Confidence</th>
                <th className="px-6 py-4 font-semibold text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300 font-mono text-[13px]">
              {data.map((d: LedgerRecord, idx: number) => (
                <tr key={d.id || idx} className="hover:bg-slate-800/50 transition-colors group">
                  <td className="px-6 py-4 text-slate-500">{d.id}</td>
                  <td className="px-6 py-4 text-slate-300 max-w-[200px] truncate" title={d.filename}>{d.filename}</td>
                  
                  <td className="px-6 py-3 text-center">
                    {d.uploaded_image_url ? (
                      <a href={getFullUrl(d.uploaded_image_url)} target="_blank" rel="noreferrer" className="inline-block hover:scale-110 transition-transform shadow-sm">
                        <img src={getFullUrl(d.uploaded_image_url)} alt="Uploaded" className="w-12 h-12 object-cover rounded-none border border-slate-700 group-hover:border-slate-500 transition-colors" />
                      </a>
                    ) : <span className="text-slate-600">-</span>}
                  </td>
                  
                  <td className="px-6 py-3 text-center">
                    {d.processed_image_url ? (
                      <a href={getFullUrl(d.processed_image_url)} target="_blank" rel="noreferrer" className="inline-block hover:scale-110 transition-transform shadow-sm">
                        <img src={getFullUrl(d.processed_image_url)} alt="Processed" className="w-12 h-12 object-cover rounded-none border border-slate-700 group-hover:border-slate-500 transition-colors" />
                      </a>
                    ) : <span className="text-slate-600">-</span>}
                  </td>
                  
                  <td className="px-6 py-3 text-center">
                    {d.map_stitching_output ? (
                      <a href={getFullUrl(d.map_stitching_output)} target="_blank" rel="noreferrer" className="inline-block hover:scale-110 transition-transform shadow-sm">
                        <img src={getFullUrl(d.map_stitching_output)} alt="Map Stitching" className="w-12 h-12 object-cover rounded-none border border-slate-700 group-hover:border-slate-500 transition-colors" />
                      </a>
                    ) : <span className="text-slate-600">-</span>}
                  </td>

                  <td className="px-6 py-4">
                    {d.confidence !== null && d.confidence !== undefined ? (
                      <span className="text-blue-400 font-semibold">{typeof d.confidence === 'number' ? d.confidence.toFixed(1) : d.confidence}%</span>
                    ) : <span className="text-slate-600">-</span>}
                  </td>
                  
                  <td className="px-6 py-4 text-right font-sans">
                    {d.status === 'Approved' ? <span className="text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-none border border-emerald-500/20 tracking-wider uppercase">Approved</span> : 
                     d.status === 'Rejected' ? <span className="text-[11px] font-bold text-rose-400 bg-rose-500/10 px-3 py-1.5 rounded-none border border-rose-500/20 tracking-wider uppercase">Rejected</span> : 
                     <span className="text-[11px] font-bold text-amber-400 bg-amber-500/10 px-3 py-1.5 rounded-none border border-amber-500/20 tracking-wider uppercase">Pending</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
