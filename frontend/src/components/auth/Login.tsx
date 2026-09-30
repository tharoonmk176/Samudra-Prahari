"use client";
import React, { useState } from "react";
import { motion } from "motion/react";
import { Broadcast, ArrowRight, ShieldCheck, Spinner } from "@phosphor-icons/react";

export default function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  
  



  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      if (isRegistering) {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password })
        });
        if (!res.ok) {
          const data = await res.json();
          let errMsg = "Registration failed";
          if (data.detail) {
            if (typeof data.detail === "string") errMsg = data.detail;
            else if (Array.isArray(data.detail)) errMsg = data.detail.map((e: any) => e.msg).join(", ");
            else errMsg = JSON.stringify(data.detail);
          }
          setError(errMsg);
        } else {
          setIsRegistering(false);
          setError("Registration successful! Please login.");
          setPassword("");
        }
      } else {
        const formData = new FormData();
        formData.append("username", username);
        formData.append("password", password);
        
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/login`, {
          method: "POST",
          body: formData
        });
        if (!res.ok) {
          const data = await res.json();
          let errMsg = "Login failed";
          if (data.detail) {
            if (typeof data.detail === "string") errMsg = data.detail;
            else if (Array.isArray(data.detail)) errMsg = data.detail.map((e: any) => e.msg).join(", ");
            else errMsg = JSON.stringify(data.detail);
          }
          setError(errMsg);
        } else {
          const data = await res.json();
          const token = data.access_token;
          onLogin(token);
        }
      }
    } catch {
      setError("Network error occurred.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex w-full min-h-[100dvh] items-center justify-center bg-transparent text-slate-300 font-mono p-4 relative overflow-hidden">
      {/* Tactical Background Grid */}
      <div className="absolute inset-0 pointer-events-none opacity-20" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>

      
      <motion.div 
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-[420px] relative z-10"
      >
        <div className="mb-10 text-center flex flex-col items-center">
          <div className="w-12 h-12 bg-slate-900 rounded-none border border-slate-800 flex items-center justify-center mb-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
            <Broadcast weight="duotone" className="text-blue-500 text-2xl" />
          </div>
          <h2 className="text-2xl md:text-3xl font-medium tracking-tight text-slate-100 mb-2">Samudra Prahari</h2>
          <p className="text-sm text-slate-500 max-w-[280px] mt-2">
            {isRegistering 
              ? "Create an account to access the dashboard." 
              : "Sign in to access your dashboard."}
          </p>
        </div>

        <div className="bg-slate-900/60 backdrop-blur-md border border-slate-700/50 p-8 rounded-none shadow-[inset_0_1px_0_rgba(255,255,255,0.02)] relative">
          
          {/* Corner accents */}
          <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-slate-500" />
          <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-slate-500" />
          <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-slate-500" />
          <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-slate-500" />

          {error && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className={`overflow-hidden mb-6 p-3 rounded-none text-[11px] uppercase tracking-wider border flex items-center gap-3 ${
                error.includes("successful") 
                  ? "bg-blue-950/30 border-blue-900/50 text-blue-400"
                  : "bg-red-950/30 border-red-900/50 text-red-400"
              }`}
            >
              {error.includes("successful") ? <ShieldCheck className="text-lg shrink-0" /> : null}
              {error}
            </motion.div>
          )}
          
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="space-y-1.5">
              <label className="text-[11px] uppercase tracking-widest font-semibold text-slate-400" htmlFor="username">
                Ident
              </label>
              <input 
                id="username"
                type="text" 
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-700/50 rounded-none px-4 py-2.5 text-slate-200 text-sm font-mono focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all placeholder:text-slate-600"
                placeholder="Enter your username"
                required
              />
            </div>
            
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[11px] uppercase tracking-widest font-semibold text-slate-400" htmlFor="password">
                  Passcode
                </label>
              </div>
              <input 
                id="password"
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-700/50 rounded-none px-4 py-2.5 text-slate-200 text-sm font-mono focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all placeholder:text-slate-600"
                placeholder="••••••••"
                required
              />
            </div>
            
            <button 
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 group relative flex items-center justify-center gap-2 bg-slate-800 text-slate-100 uppercase tracking-widest font-semibold text-xs py-3 rounded-none hover:bg-slate-700 border border-slate-700 hover:border-slate-600 transition-all active:scale-[0.98] disabled:opacity-70 disabled:active:translate-y-[1px] overflow-hidden"
            >
              {isLoading ? (
                <Spinner className="animate-spin text-lg text-blue-500" />
              ) : (
                <>
                  <span className="group-hover:text-blue-400 transition-colors">{isRegistering ? "Create Account" : "Sign In"}</span>
                  <ArrowRight weight="bold" className="text-base group-hover:translate-x-0.5 group-hover:text-blue-400 transition-all" />
                </>
              )}
            </button>
          </form>
          
          <div className="mt-8 pt-6 border-t border-slate-800 text-center text-[11px] uppercase tracking-widest text-slate-500">
            {isRegistering ? "Already have an account? " : "Don't have an account? "}
            <button 
              type="button"
              className="text-slate-300 hover:text-blue-400 font-semibold transition-colors ml-1"
              onClick={() => {
                setIsRegistering(!isRegistering);
                setError("");
              }}
            >
              {isRegistering ? "Sign in instead" : "Create one"}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
