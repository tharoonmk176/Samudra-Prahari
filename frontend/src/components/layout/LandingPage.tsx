import React, { useState, useEffect } from "react";
import { ShieldCheck, Waves, MapTrifold, ArrowRight, Lightning, Target, Crosshair, Broadcast, Database, Cpu } from "@phosphor-icons/react";

export default function LandingPage({ onEnter }: { onEnter: () => void }) {
  const [mounted, setMounted] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    setMounted(true);
    const handleScroll = () => {
      const totalScroll = document.documentElement.scrollTop;
      const windowHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scroll = `${totalScroll / windowHeight}`;
      setScrollProgress(Number(scroll));
    }
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 font-sans selection:bg-blue-500/30 overflow-x-hidden">
      
      {/* Scroll Progress Bar */}
      <div className="fixed top-0 left-0 h-1 bg-blue-500 z-[100] transition-all duration-150" style={{ width: `${scrollProgress * 100}%` }} />

      {/* Subtle Grain Background */}
      <div className="fixed inset-0 z-0 opacity-10 pointer-events-none" 
           style={{ backgroundImage: 'radial-gradient(circle, #334155 1px, transparent 1px)', backgroundSize: '32px 32px' }}>
      </div>

      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 h-20 border-b border-slate-900 bg-slate-950/80 backdrop-blur-md flex items-center justify-between px-8 lg:px-16">
        <div className="flex items-center gap-4">
          <Waves size={24} className="text-blue-500" />
          <div className="flex flex-col">
            <span className="font-mono text-sm tracking-widest text-slate-100 font-bold uppercase leading-none">Samudra Prahari</span>
            <span className="font-mono text-[10px] tracking-widest text-slate-500 uppercase mt-1">Intelligence Platform</span>
          </div>
        </div>

      </nav>

      {/* Section 1: Hero Split */}
      <section className="relative z-10 grid grid-cols-1 lg:grid-cols-2 min-h-screen pt-20 px-8 lg:px-16 max-w-[1600px] mx-auto items-center gap-16">
        <div className={`flex flex-col items-start transition-all duration-700 ease-out ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
          <div className="inline-flex items-center gap-3 px-3 py-1 bg-slate-900 border border-slate-800 rounded-sm mb-10">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-mono text-[10px] text-slate-400 uppercase tracking-widest">System Online • V3 Pipeline</span>
          </div>
          <h1 className="text-5xl lg:text-7xl font-bold text-white tracking-tight leading-[1.05] mb-6">
            Tactical Marine <br />
            Debris Isolation.
          </h1>
          <p className="text-lg text-slate-400 max-w-[50ch] mb-12 leading-relaxed">
            Ingest raw side-scan sonar telemetry, stitch seamless acoustic maps, and deploy multi-stage AI (U-Net + YOLOv11) to isolate man-made hazards with geodesic precision.
          </p>
          <div className="flex flex-col sm:flex-row items-center gap-6 w-full sm:w-auto">
            <a 
              href="#architecture"
              className="w-full sm:w-auto flex items-center justify-center gap-3 bg-slate-800 text-white border border-slate-700 px-8 py-4 font-mono text-sm font-bold uppercase tracking-wider transition-all hover:bg-slate-700 rounded-none"
            >
              View Architecture
            </a>
            <button 
              onClick={onEnter}
              className="w-full sm:w-auto flex items-center justify-center gap-3 bg-blue-600/20 text-blue-400 border border-blue-500/50 px-8 py-4 font-mono text-sm font-bold uppercase tracking-wider transition-all hover:bg-blue-600/30 hover:text-blue-300 rounded-none"
            >
              Launch System <ArrowRight weight="bold" />
            </button>
          </div>
        </div>
        <div className={`w-full aspect-square max-w-[600px] mx-auto relative flex items-center justify-center transition-all duration-700 delay-200 ease-out ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
          <div className="relative w-full h-full rounded-full border border-slate-800/50 flex items-center justify-center bg-slate-900/20">
            <div className="absolute w-[75%] h-[75%] rounded-full border border-slate-800/50" />
            <div className="absolute w-[50%] h-[50%] rounded-full border border-slate-800/50" />
            <div className="absolute w-[25%] h-[25%] rounded-full border border-slate-800/50 flex items-center justify-center">
               <Target size={24} className="text-slate-700" />
            </div>
            <div className="absolute w-full h-[1px] bg-slate-800/50" />
            <div className="absolute h-full w-[1px] bg-slate-800/50" />
            <div className="absolute inset-0 rounded-full bg-[conic-gradient(from_0deg,transparent_0deg,transparent_270deg,rgba(59,130,246,0.1)_360deg)] animate-[spin_4s_linear_infinite]" />
            <div className="absolute w-1/2 h-[1px] bg-gradient-to-r from-transparent to-blue-500 top-1/2 left-1/2 origin-left animate-[spin_4s_linear_infinite]" />
            <div className="absolute top-[35%] left-[65%] flex items-center gap-3">
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full shadow-[0_0_8px_#3b82f6]" />
            </div>
            <div className="absolute top-[65%] left-[25%] flex items-center gap-3">
              <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full shadow-[0_0_8px_#10b981]" />
            </div>
          </div>
          <div className="absolute bottom-12 -left-8 bg-slate-950 border border-slate-800 p-4 shadow-xl hidden md:block">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-slate-900 border border-slate-800 flex items-center justify-center">
                <ShieldCheck size={20} className="text-emerald-500" />
              </div>
              <div>
                <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">Target Verified</div>
                <div className="text-sm font-bold text-slate-200">Ghost Net Detected</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Architecture */}
      <section id="architecture" className="relative z-10 bg-slate-900/50 border-t border-b border-slate-800 py-32 px-8 lg:px-16">
        <div className="max-w-[1600px] mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 tracking-tight">Multi-Stage Inference Engine</h2>
            <p className="text-slate-400 max-w-2xl mx-auto text-lg">Samudra Prahari executes a proprietary three-stage computer vision pipeline, capable of identifying anomalous topologies and parsing rigid vs organic structures in milliseconds.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-slate-950 border border-slate-800 p-8 flex flex-col items-start hover:border-blue-500/50 transition-colors">
              <div className="w-12 h-12 bg-slate-900 flex items-center justify-center border border-slate-800 mb-6 text-blue-500"><Broadcast size={24} /></div>
              <h3 className="text-xl font-bold text-white mb-3">Stage A: Anomaly Autoencoder</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-4">An unsupervised Convolutional Autoencoder continuously reconstructs the incoming acoustic feed, flagging extreme topological deviations from normal sandy or rocky seabeds.</p>
              <span className="mt-auto text-[10px] font-mono text-slate-500 uppercase tracking-widest border border-slate-800 px-3 py-1">ONNX Runtime</span>
            </div>
            <div className="bg-slate-950 border border-slate-800 p-8 flex flex-col items-start hover:border-emerald-500/50 transition-colors">
              <div className="w-12 h-12 bg-slate-900 flex items-center justify-center border border-slate-800 mb-6 text-emerald-500"><Crosshair size={24} /></div>
              <h3 className="text-xl font-bold text-white mb-3">Stage B: Strict Classification</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-4">A parallel YOLOv11 and U-Net Segmentation network classifies the anomaly into 5 rigid or organic classes (Ghost Nets, Shipwrecks, Aircraft, Pipes, Cylinders) with pixel-perfect masking.</p>
              <span className="mt-auto text-[10px] font-mono text-slate-500 uppercase tracking-widest border border-slate-800 px-3 py-1">TensorRT Accelerated</span>
            </div>
            <div className="bg-slate-950 border border-slate-800 p-8 flex flex-col items-start hover:border-amber-500/50 transition-colors">
              <div className="w-12 h-12 bg-slate-900 flex items-center justify-center border border-slate-800 mb-6 text-amber-500"><Cpu size={24} /></div>
              <h3 className="text-xl font-bold text-white mb-3">Stage C: Shadow Verification</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-4">Proprietary heuristic verification. The pipeline measures acoustic shadow casting, solidity, and contrast ratio to eliminate false positives caused by natural geological formations.</p>
              <span className="mt-auto text-[10px] font-mono text-slate-500 uppercase tracking-widest border border-slate-800 px-3 py-1">Algorithmic Filter</span>
            </div>
          </div>
        </div>
      </section>

      {/* Section 3: Geodesic Tracking */}
      <section className="relative z-10 py-32 px-8 lg:px-16">
        <div className="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div className="order-2 lg:order-1 relative h-[400px] border border-slate-800 bg-slate-900/50 overflow-hidden flex items-center justify-center group">
            <div className="absolute inset-0 opacity-30" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)', backgroundSize: '20px 20px' }}></div>
            <MapTrifold size={120} className="text-slate-800 group-hover:text-slate-700 transition-colors" />
            <div className="absolute bottom-6 left-6 right-6 p-4 bg-slate-950 border border-slate-800">
               <div className="flex items-center gap-3 font-mono text-xs text-blue-400 uppercase tracking-widest">
                  <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                  Live Syncing Telemetry Database
               </div>
            </div>
          </div>
          <div className="order-1 lg:order-2">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 tracking-tight">Geospatial Intelligence.</h2>
            <p className="text-slate-400 text-lg mb-8 leading-relaxed">Every identified target is permanently logged into a high-performance SQLite/PostgreSQL database, anchoring detections to exact latitude and longitude coordinates. Operators can export compiled intelligence reports to CSV, PDF, or JSON instantly.</p>
            <ul className="space-y-4">
              <li className="flex items-center gap-4 text-sm font-bold text-slate-300 font-mono"><Database className="text-blue-500" size={20} /> Persistent Session History</li>
              <li className="flex items-center gap-4 text-sm font-bold text-slate-300 font-mono"><MapTrifold className="text-emerald-500" size={20} /> Real-time Leaflet Cartography</li>
              <li className="flex items-center gap-4 text-sm font-bold text-slate-300 font-mono"><ShieldCheck className="text-amber-500" size={20} /> Manual Operator Validation</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <footer className="relative z-10 border-t border-slate-900 bg-slate-950 py-16">
        <div className="max-w-[1600px] mx-auto px-8 lg:px-16 flex flex-col items-center justify-center text-center">
          <h3 className="text-2xl font-bold text-white mb-8 tracking-wide">Ready to Deploy?</h3>

          
          <div className="mt-16 pt-8 border-t border-slate-900 w-full flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-[10px] font-mono tracking-widest text-slate-600 uppercase">
              Ministry of Earth Sciences (MoES) • NIOT
            </p>
            <span className="text-[10px] font-mono tracking-widest text-slate-600 uppercase">Problem Statement: 26057</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
