import React from 'react'
import { X, Cpu, Layers, ShieldCheck, CheckCircle2 } from 'lucide-react'

interface HelpModalProps {
  isOpen: boolean
  onClose: () => void
}

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto border border-slate-200 shadow-xl p-6">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-slate-900">
                ResumeRanker Algorithm Architecture
              </h3>
              <p className="text-xs text-slate-500">
                Multi-Signal AI Engine &amp; Explainability Guidelines
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-700 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="mt-5 space-y-4 text-xs text-slate-600 leading-relaxed">
          
          <div className="bg-indigo-50/70 border border-indigo-100 rounded-xl p-4">
            <h4 className="font-bold text-indigo-950 text-sm mb-1 flex items-center">
              <Layers className="w-4 h-4 mr-1.5 text-indigo-600" />
              1. The 4-Signal Weighted Formula
            </h4>
            <p className="mb-2">
              Every candidate score is mathematically composed from 4 independently calibrated signals:
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
              <div className="bg-white p-2 rounded-lg border border-indigo-100">
                <span className="block font-extrabold text-indigo-700 text-base">35%</span>
                <span className="font-semibold text-slate-700">Skill Match</span>
              </div>
              <div className="bg-white p-2 rounded-lg border border-indigo-100">
                <span className="block font-extrabold text-indigo-700 text-base">30%</span>
                <span className="font-semibold text-slate-700">SBERT Semantic</span>
              </div>
              <div className="bg-white p-2 rounded-lg border border-indigo-100">
                <span className="block font-extrabold text-indigo-700 text-base">20%</span>
                <span className="font-semibold text-slate-700">Experience Fit</span>
              </div>
              <div className="bg-white p-2 rounded-lg border border-indigo-100">
                <span className="block font-extrabold text-indigo-700 text-base">15%</span>
                <span className="font-semibold text-slate-700">Degree &amp; Qual</span>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-bold text-slate-900 text-sm mb-1">
              2. Primary Skill Weighting &amp; Damping
            </h4>
            <p>
              Skills identified in the Job Description title or repeated prominently (e.g. <em>Java</em> on a Java JD, or <em>Python</em> on a Python JD) carry double weight. Candidates missing the primary required skill are damped dynamically, preventing off-domain candidates with shared infrastructure skills (Docker, Git, SQL) from outranking genuine domain specialists.
            </p>
          </div>

          <div>
            <h4 className="font-bold text-slate-900 text-sm mb-1">
              3. Truth-Grounded Experience Reconciliation
            </h4>
            <p>
              The system calculates chronological tenure from work history dates and cross-references it with stated summary claims. If an inflation or discrepancy is detected, the verified date tenure takes precedence and an audit warning is generated.
            </p>
          </div>

          <div>
            <h4 className="font-bold text-slate-900 text-sm mb-1">
              4. Calibrated SBERT Semantic Floor &amp; Ceiling
            </h4>
            <p>
              Cosine similarity is mapped smoothly across a calibrated floor (0.50) and ceiling (0.80), ensuring off-domain candidates receive zero unwarranted credit while domain experts receive full semantic credit.
            </p>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="mt-6 pt-4 border-t border-slate-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-indigo-600 text-white font-semibold text-xs rounded-xl hover:bg-indigo-700 transition"
          >
            Got it, Back to Dashboard
          </button>
        </div>

      </div>
    </div>
  )
}
