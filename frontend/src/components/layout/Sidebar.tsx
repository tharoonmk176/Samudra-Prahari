import { Target, Pulse, Database, Gear, Crosshair, Waveform, Plus, Folder, Trash } from "@phosphor-icons/react";

export default function Sidebar({ activeTab, setActiveTab, sessions = [], activeSessionId, setActiveSessionId, createNewSession, deleteSession }: any) {
  const navItems = [
    { id: "analysis", label: "Sonar Pipeline", icon: Crosshair },
    { id: "history", label: "Sonar Sessions Database", icon: Database },
    { id: "ledger", label: "Master Ledger", icon: Pulse },
  ];

  return (
    <aside className="w-16 md:w-20 lg:w-64 border-r border-slate-800 bg-slate-950 flex flex-col justify-between py-6 shrink-0 z-50">
      <div className="flex flex-col items-center lg:items-start w-full px-4 lg:px-6 h-full overflow-hidden">
        <div className="flex items-center gap-3 mb-10 w-full justify-center lg:justify-start group cursor-pointer shrink-0">
          <div className="w-10 h-10 flex items-center justify-center bg-blue-600 rounded-none shadow-md shadow-blue-900/20 shrink-0">
            <Waveform size={24} className="text-white" weight="bold" />
          </div>
          <div className="hidden lg:flex flex-col">
            <span className="text-white font-bold tracking-widest text-xs uppercase leading-tight">Samudra</span>
            <span className="text-blue-500 font-bold tracking-widest text-xs uppercase leading-tight">Prahari</span>
          </div>
        </div>

        <nav className="flex flex-col gap-2 w-full shrink-0">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button 
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-4 w-full p-3 rounded-none transition-all duration-200 group ${activeTab === id ? "bg-slate-800/80 text-blue-400" : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"}`}
              title={label}
            >
              <div className="flex items-center justify-center w-6 h-6 shrink-0">
                <Icon size={20} weight={activeTab === id ? "fill" : "regular"} className={activeTab === id ? "text-blue-400" : "text-slate-500 group-hover:text-slate-300"} />
              </div>
              <span className="hidden lg:block text-xs font-semibold uppercase tracking-wider">{label}</span>
            </button>
          ))}
        </nav>

        <div className="mt-8 w-full flex-1 overflow-hidden flex flex-col">
          <div className="hidden lg:flex items-center justify-between mb-3 shrink-0">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Sonar Sessions</span>
            <button onClick={createNewSession} className="text-slate-400 hover:text-white p-1 bg-slate-800 hover:bg-slate-700 rounded-none transition-colors" title="New Sonar Session"><Plus size={12} weight="bold" /></button>
          </div>
          <div className="flex lg:hidden justify-center mb-3 shrink-0">
             <button onClick={createNewSession} className="text-slate-400 hover:text-white p-2 bg-slate-800 hover:bg-slate-700 rounded-none transition-colors" title="New Sonar Session"><Plus size={16} weight="bold" /></button>
          </div>
          <div className="flex flex-col gap-1 overflow-y-auto no-scrollbar w-full">
             {sessions.map((s: any) => (
               <div key={s.id} className={`flex items-center w-full rounded-none group transition-colors ${activeSessionId === s.id ? "bg-slate-800 border-l-2 border-blue-500" : "hover:bg-slate-900 border-l-2 border-transparent"}`}>
                 <button onClick={() => setActiveSessionId(s.id)} className={`flex-1 flex items-center justify-center lg:justify-start gap-3 p-2 text-xs text-left transition-colors ${activeSessionId === s.id ? "text-blue-400" : "text-slate-400"}`} title={s.name}>
                   <Folder size={16} weight={activeSessionId === s.id ? "fill" : "regular"} className="shrink-0 group-hover:text-slate-300" />
                   <span className="truncate hidden lg:block uppercase tracking-wider font-semibold text-[10px]">{s.name}</span>
                 </button>
                 <button onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }} className="hidden lg:flex p-2 text-slate-500 hover:text-red-400 hover:bg-white/5 transition-colors items-center justify-center rounded-none" title="Delete Sonar Session">
                   <Trash size={14} weight="bold" />
                 </button>
               </div>
             ))}
          </div>
        </div>
      </div>


    </aside>
  );
}
