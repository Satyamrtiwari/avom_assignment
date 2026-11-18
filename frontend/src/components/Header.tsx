import React from 'react'
import { CheckCircle2, ChevronDown, HelpCircle, Bell, RotateCcw } from 'lucide-react'
import { JobDescriptionItem } from '../types'

interface HeaderProps {
  jds: JobDescriptionItem[]
  activeJd: JobDescriptionItem | null
  onSelectJd: (jd: JobDescriptionItem | null) => void
  backendOnline: boolean
  onResetAll: () => void
  onOpenHelp: () => void
}

export const Header: React.FC<HeaderProps> = ({
  jds,
  activeJd,
  onSelectJd,
  backendOnline,
  onResetAll,
  onOpenHelp
}) => {
  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 px-6 py-3.5 shadow-xs">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Left: Brand & Logo */}
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={onResetAll}>
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm shadow-indigo-200">
              <CheckCircle2 className="w-5 h-5 text-white stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-lg font-extrabold text-slate-900 tracking-tight">
                  ResumeRanker
                </span>
                <span className="text-[10px] font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full border border-indigo-200 uppercase tracking-wider">
                  AI Talent Engine
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                Multi-Signal Resume Matching &amp; Ranking System
              </p>
            </div>
          </div>

          {/* Center-Left: Active Role Selector */}
          <div className="relative hidden md:block">
            <div className="flex items-center space-x-2 bg-slate-50 border border-slate-200 hover:border-indigo-300 rounded-full px-3.5 py-1.5 transition cursor-pointer">
              <span className={`w-2 h-2 rounded-full ${activeJd ? 'bg-indigo-600 animate-pulse' : 'bg-slate-300'}`}></span>
              <span className="text-xs font-semibold text-slate-600">
                Requisition:
              </span>
              <select
                aria-label="Active Job Requisition"
                className="bg-transparent text-xs font-bold text-slate-800 pr-5 appearance-none cursor-pointer outline-none max-w-[240px] truncate"
                value={activeJd?.id || ''}
                onChange={(e) => {
                  const val = e.target.value
                  if (!val) {
                    onSelectJd(null)
                  } else {
                    const selected = jds.find(j => j.id === val)
                    if (selected) onSelectJd(selected)
                  }
                }}
              >
                <option value="" className="text-slate-500">
                  {jds.length === 0 ? "No Saved Requisitions (Upload in Step 1)" : "Select Saved Requisition or Upload New..."}
                </option>
                {jds.map(jd => (
                  <option key={jd.id} value={jd.id} className="text-slate-800">
                    {jd.title} ({jd.required_skills?.length || 0} skills)
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Right: Actions, Status, Docs */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          
          {/* Fresh Start Button (Clears workspace) */}
          <button
            onClick={onResetAll}
            title="Reset workspace to clean fresh state"
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-rose-600 bg-white hover:bg-rose-50 border border-slate-200 hover:border-rose-200 rounded-lg transition cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Fresh Start</span>
          </button>

          {/* Backend Status indicator */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 border border-slate-200 text-slate-600">
            <span
              className={`w-2 h-2 rounded-full ${
                backendOnline ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            ></span>
            <span className="hidden sm:inline">
              {backendOnline ? 'API Connected' : 'Offline'}
            </span>
          </div>

          {/* Docs / Help modal button */}
          <button
            onClick={onOpenHelp}
            title="Algorithm Guide &amp; System Docs"
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition flex items-center space-x-1 cursor-pointer"
          >
            <HelpCircle className="w-4 h-4" />
            <span className="text-xs font-medium hidden md:inline">Docs</span>
          </button>

          {/* User Profile Avatar */}
          <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-xs ring-2 ring-indigo-200 shadow-sm">
            JD
          </div>
        </div>

      </div>
    </header>
  )
}
