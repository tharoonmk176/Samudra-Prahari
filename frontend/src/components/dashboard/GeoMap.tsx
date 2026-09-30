import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';


function MapUpdater({ center, zoom }: { center: [number, number], zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}


// Custom icons to match the screenshot
const createCustomIcon = (color: string) => {
  return L.divIcon({
    className: 'custom-icon',
    html: `<div style="background-color: ${color}; width: 12px; height: 12px; transform: rotate(45deg); border: 1px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.5);"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6]
  });
};

const redIcon = createCustomIcon('#EF4444');
const grayIcon = createCustomIcon('#64748B');
const yellowIcon = createCustomIcon('#F59E0B');



export default function GeoMap({ startLat, startLon, reportData }: any) {
  const [activeLayer, setActiveLayer] = useState('hybrid');
  const [mapRef, setMapRef] = useState<L.Map | null>(null);
  
  const isValidLocation = startLat != null && startLon != null && !isNaN(Number(startLat)) && !isNaN(Number(startLon));
  const safeLat = isValidLocation ? Number(startLat) : 0;
  const safeLon = isValidLocation ? Number(startLon) : 0;

  useEffect(() => {
    if (mapRef && isValidLocation) {
      mapRef.setView([safeLat, safeLon], 17);
      // Invalidate size after a short delay to ensure container is fully rendered/resized
      const timeout = setTimeout(() => {
        mapRef.invalidateSize();
      }, 200);
      return () => clearTimeout(timeout);
    }
  }, [mapRef, safeLat, safeLon, isValidLocation]);

  const layers: Record<string, string> = {
    hybrid: 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    maps: 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
    satellite: 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'
  };

  return (
    <div className="flex flex-col w-full h-full bg-white/[0.02] rounded-none overflow-hidden border border-white/5 shadow-2xl ">
      
      {/* Top Toolbar */}
      <div className="flex justify-between items-center bg-white/[0.04] border-b border-white/5 px-4 py-2">
        <div className="flex items-center gap-6 text-[10px] font-mono text-slate-400 tracking-widest uppercase">
          <div className="flex items-center gap-2">
            <span className="text-blue-500">▲</span> TOWFISH
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-slate-500 transform rotate-45 border border-white/50"></div>
            CONTACT (ID)
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0 border-t-2 border-dashed border-blue-500"></div>
            TRACKLINE
          </div>
        </div>
        
        <div className="flex items-center bg-white/5 rounded-none p-1 border border-white/10 gap-1">
          <button onClick={() => setActiveLayer('hybrid')} className={`px-3 py-1.5 text-xs font-semibold rounded-none transition-all ${activeLayer === 'hybrid' ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
            Google Hybrid
          </button>
          <button onClick={() => setActiveLayer('maps')} className={`px-3 py-1.5 text-xs font-semibold rounded-none transition-all ${activeLayer === 'maps' ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
            Google Maps
          </button>
          <button onClick={() => setActiveLayer('satellite')} className={`px-3 py-1.5 text-xs font-semibold rounded-none transition-all ${activeLayer === 'satellite' ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
            Google Satellite
          </button>
          <div className="w-px h-5 bg-white/10 mx-1"></div>
          <button 
            onClick={() => mapRef?.setView([safeLat, safeLon], 17)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-slate-400 hover:text-white hover:bg-white/5 rounded-none transition-all text-xs font-semibold"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            Reset
          </button>
        </div>
      </div>

      {/* Map Container */}
      <div className="relative flex-1 min-h-[500px] bg-slate-950">
        <MapContainer ref={setMapRef as any} center={[safeLat, safeLon]} zoom={17} style={{ height: '100%', width: '100%' }} zoomControl={false} className="tactical-leaflet-map">
          <MapUpdater center={[safeLat, safeLon]} zoom={17} />
          
          <TileLayer 
            url={layers[activeLayer]} 
            attribution='&copy; Google Maps'
            maxZoom={20}
            className={activeLayer === 'maps' ? 'map-filter-dark' : ''}
          />
          <Polyline positions={[[safeLat, safeLon], [safeLat + 0.005, safeLon]]} color="#F59E0B" weight={2} dashArray="5, 10" />
          
          <Marker position={[safeLat, safeLon]} icon={yellowIcon}>
            <Popup>Towfish Origin</Popup>
          </Marker>

          {reportData?.map((d: any, i: number) => {
            if (!d.lat) return null;
            const isTarget = ['shipwreck', 'aircraft', 'ghost_net'].includes(d.class.toLowerCase());
            return (
              <Marker key={i} position={[Number(d.lat), Number(d.lon)]} icon={isTarget ? redIcon : grayIcon}>
                <Popup className="custom-popup">
                  <div className="bg-slate-900 text-white p-2 rounded shadow-xl border border-white/10">
                    <div className="text-[10px] font-mono text-slate-400 mb-1">det_{(i+1).toString().padStart(3, '0')}</div>
                    <div className="font-bold text-sm uppercase">{d.class}</div>
                    <div className="text-xs text-slate-300 mt-1">Conf: {d.confidence_pct}%</div>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>

        {/* Bottom Left Info Box */}
        <div className="absolute bottom-4 left-4 z-[400] bg-slate-900/80  border border-white/5 rounded-none p-3 flex items-start gap-3 shadow-2xl">
          <svg className="w-4 h-4 text-blue-500 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd"/></svg>
          <div>
            <div className="text-xs font-bold text-white tracking-wide">Active Telemetry Feed</div>
            <div className="text-[10px] font-mono text-slate-400 mt-0.5">Origin: {safeLat.toFixed(4)}°N, {safeLon.toFixed(4)}°E</div>
          </div>
        </div>
      </div>

      {/* Detection List */}
      <div className="bg-transparent flex flex-col border-t border-white/5">
        {reportData?.map((d: any, i: number) => {
          if (!d.lat) return null;
          const isTarget = ['shipwreck', 'aircraft', 'ghost_net'].includes(d.class.toLowerCase());
          return (
            <div key={i} className="flex items-center justify-between px-6 py-3 border-b border-white/5 hover:bg-white/[0.02] transition-colors">
              <div className="flex items-center gap-4">
                <div className={`w-2.5 h-2.5 transform rotate-45 ${isTarget ? 'bg-red-500' : 'bg-slate-500'} shadow-[0_0_10px_rgba(239,68,68,0.5)]`}></div>
                <div className="text-xs font-mono text-white/80">det_{(i+1).toString().padStart(3, '0')}</div>
                <div className="text-xs font-mono text-blue-400/80 uppercase tracking-wider">{d.class}</div>
                <div className="text-white/20 text-xs">·</div>
                <div className="flex items-center gap-1.5 text-slate-400 text-xs font-mono">
                  <svg className="w-3 h-3 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd"/></svg>
                  Contact Recorded
                </div>
              </div>
              <div className="text-[10px] font-mono text-slate-500">
                {Number(d.lat).toFixed(4)}°N / {Number(d.lon).toFixed(4)}°E
              </div>
            </div>
          );
        })}
        {(!reportData || reportData.length === 0) && (
          <div className="p-6 text-center text-sm font-mono text-slate-500">
            No geographic telemetry available.
          </div>
        )}
      </div>
      
    </div>
  );
}
