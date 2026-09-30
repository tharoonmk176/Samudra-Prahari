"use client";
import dynamic from 'next/dynamic';
import { useState } from 'react';

const GeoMap = dynamic(() => import('@/components/dashboard/GeoMap'), { ssr: false });

export default function TestPage() {
  const [loc, setLoc] = useState({ lat: 10, lon: 10 });
  return (
    <div style={{ padding: 20, height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 20 }}>
        <button onClick={() => setLoc({ lat: 10, lon: 10 })} style={{ padding: 8, marginRight: 8, border: '1px solid white' }}>Loc A</button>
        <button onClick={() => setLoc({ lat: '50' as any, lon: '50' as any })} style={{ padding: 8, border: '1px solid white' }}>Loc B</button>
        <button onClick={() => setLoc({ lat: 51, lon: 51 })} style={{ padding: 8, border: '1px solid white' }}>Loc C</button>
      </div>
      <div style={{ flex: 1, position: 'relative' }}>
        <GeoMap startLat={loc.lat} startLon={loc.lon} reportData={[]} />
      </div>
    </div>
  );
}
