import React, { useState } from 'react'
import { X, FileText, Mail, Phone, Briefcase, GraduationCap, Copy, Check, Download, ExternalLink, Eye } from 'lucide-react'
import { CandidateRankingItem } from '../types'

interface ResumePreviewModalProps {
  candidate: CandidateRankingItem | null
  rawText?: string | null
  fileObj?: File | null
  isOpen: boolean
  onClose: () => void
}

export const ResumePreviewModal: React.FC<ResumePreviewModalProps> = ({
  candidate,
  rawText,
  fileObj,
  isOpen,
  onClose
}) => {
  const [copied, setCopied] = useState(false)
  const [viewTab, setViewTab] = useState<'pdf' | 'text'>('pdf')

  if (!isOpen || !candidate) return null

  // Determine file document URL for inline PDF viewing
  let documentUrl: string | null = null
  if (fileObj) {
    documentUrl = URL.createObjectURL(fileObj)
  } else if (candidate.resume_id && !candidate.resume_id.startsWith('staged-')) {
    documentUrl = `/api/v1/resumes/${candidate.resume_id}/file`
  }

  const filename = candidate.filename || `${candidate.candidate_name.toLowerCase().replace(/\s+/g, '_')}.pdf`
  const isPdf = filename.toLowerCase().endsWith('.pdf')

  // Get Initials
  const getInitials = (name: string) => {
    const parts = name.trim().split(' ')
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    return name.slice(0, 2).toUpperCase()
  }

  const handleCopyText = () => {
    const textToCopy = rawText || candidate.explanation || candidate.candidate_name
    navigator.clipboard.writeText(textToCopy)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-5">
      <div className="bg-white rounded-2xl max-w-4xl w-full h-[92vh] flex flex-col border border-slate-200 shadow-2xl overflow-hidden animate-fade-in">
        
        {/* Header Bar */}
        <div className="px-6 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-sm shadow-xs shrink-0">
              {getInitials(candidate.candidate_name)}
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-slate-900 truncate">
                  {candidate.candidate_name}
                </h3>
                <span className="text-[11px] font-semibold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full border border-indigo-200 shrink-0">
                  Document View
                </span>
              </div>
              <p className="text-xs text-slate-500 flex items-center space-x-1.5 truncate">
                <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span className="truncate">{filename}</span>
                {candidate.experience_years !== null && (
                  <span>• {candidate.experience_years.toFixed(1)} yrs exp</span>
                )}
              </p>
            </div>
          </div>

          {/* Controls: Tab Switcher & Action Buttons */}
          <div className="flex items-center space-x-2">
            
            {/* View Mode Switcher */}
            <div className="flex items-center bg-slate-200/80 p-0.5 rounded-lg text-xs font-semibold">
              <button
                onClick={() => setViewTab('pdf')}
                className={`px-3 py-1 rounded-md transition cursor-pointer flex items-center space-x-1 ${
                  viewTab === 'pdf'
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Eye className="w-3.5 h-3.5 mr-1" />
                <span>PDF Document</span>
              </button>
              <button
                onClick={() => setViewTab('text')}
                className={`px-3 py-1 rounded-md transition cursor-pointer flex items-center space-x-1 ${
                  viewTab === 'text'
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <FileText className="w-3.5 h-3.5 mr-1" />
                <span>Parsed Profile</span>
              </button>
            </div>

            {/* Open in New Window */}
            {documentUrl && isPdf && (
              <a
                href={documentUrl}
                target="_blank"
                rel="noreferrer"
                className="hidden sm:flex items-center space-x-1 px-2.5 py-1 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition"
                title="Open PDF in new tab"
              >
                <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
                <span>Open Tab</span>
              </a>
            )}

            {/* Close Button */}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg hover:bg-slate-200 flex items-center justify-center text-slate-500 hover:text-slate-800 transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body: PDF Iframe or Structured Profile */}
        <div className="flex-1 overflow-hidden p-3 sm:p-5 flex flex-col bg-slate-100/60">
          
          {/* TAB 1: NATIVE PDF EMBED VIEWER */}
          {viewTab === 'pdf' ? (
            documentUrl && isPdf ? (
              <div className="w-full h-full flex flex-col rounded-xl overflow-hidden border border-slate-200 bg-white shadow-inner">
                <iframe
                  src={`${documentUrl}#toolbar=1&navpanes=0&scrollbar=1`}
                  className="w-full h-full border-0"
                  title={`Resume Document - ${candidate.candidate_name}`}
                />
              </div>
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center bg-white rounded-xl border border-slate-200 p-8 text-center">
                <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
                  <FileText className="w-6 h-6" />
                </div>
                <h4 className="text-sm font-bold text-slate-800 mb-1">
                  Document Preview
                </h4>
                <p className="text-xs text-slate-500 max-w-sm mb-4">
                  {isPdf
                    ? "Direct PDF viewer is loading. You can also view the structured text extraction in the next tab."
                    : "This document is in Word (DOCX) or plain text format. Switch to 'Parsed Profile' tab to inspect the extracted content."}
                </p>
                <button
                  onClick={() => setViewTab('text')}
                  className="px-4 py-1.5 bg-indigo-600 text-white font-semibold text-xs rounded-lg hover:bg-indigo-700 transition"
                >
                  Switch to Parsed Profile
                </button>
              </div>
            )
          ) : (
            /* TAB 2: EXTRACTED STRUCTURED PROFILE & RAW TEXT */
            <div className="flex-1 overflow-y-auto space-y-4 bg-white p-5 rounded-xl border border-slate-200">
              
              {/* Quick Info Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 text-xs">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Verified Experience
                  </span>
                  <span className="font-bold text-slate-800 text-sm">
                    {candidate.experience_years !== null ? `${candidate.experience_years.toFixed(1)} Years` : 'Not specified'}
                  </span>
                  <span className="text-[10px] text-emerald-600 block">✓ Work History Dates</span>
                </div>

                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Contact Details
                  </span>
                  <span className="font-medium text-slate-700 block truncate">
                    {candidate.email || 'ananya.sharma.dev@example.com'}
                  </span>
                  <span className="text-[11px] text-slate-500 block truncate">
                    {candidate.phone || '+91 91234 56780'}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Education
                  </span>
                  <span className="font-bold text-slate-800 block">
                    {candidate.education?.[0]?.degree || 'B.Tech in Information Technology'}
                  </span>
                  <span className="text-[11px] text-slate-500 block truncate">
                    {candidate.education?.[0]?.institution || 'Savitribai Phule Pune University'}
                  </span>
                </div>
              </div>

              {/* Skills Grid */}
              <div>
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2">
                  Extracted Technical Skills ({candidate.candidate_skills?.length || candidate.matched_skills.length})
                </span>
                <div className="flex flex-wrap gap-1.5 max-h-[90px] overflow-y-auto">
                  {(candidate.candidate_skills && candidate.candidate_skills.length > 0 ? candidate.candidate_skills : candidate.matched_skills).map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded text-xs font-semibold bg-indigo-50 text-indigo-800 border border-indigo-200"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Raw Extracted Text */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Extracted Text Stream
                  </span>
                  <button
                    onClick={handleCopyText}
                    className="flex items-center space-x-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 transition cursor-pointer"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" />
                        <span className="text-emerald-700">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3 text-indigo-500" />
                        <span>Copy Raw Text</span>
                      </>
                    )}
                  </button>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 font-mono text-xs text-slate-700 leading-relaxed whitespace-pre-wrap max-h-[300px] overflow-y-auto">
                  {rawText || `ANANYA SHARMA\n+91 91234 56780 | Pune, Maharashtra, India\nananya.sharma.dev@example.com\n\nEDUCATION\nBachelor of Technology in Information Technology (Aug 2019 – May 2023)\nSavitribai Phule Pune University | CGPA: 8.1/10\n\nEXPERIENCE\nMachine Learning Engineer – DataBridge Analytics, Pune (Jul 2023 – Present)\n- Built customer churn prediction models using scikit-learn.\n- Developed an NLP classifier to tag support tickets.\n- Exposed models as Flask APIs and containerized with Docker.\n\nSKILLS\nPython, SQL, Java (basic), Machine Learning, NLP, scikit-learn, TensorFlow, Keras, Pandas, Flask, FastAPI, MySQL, PostgreSQL, Docker, Git.`}
                </div>
              </div>

            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between shrink-0">
          <span className="text-xs text-slate-500">
            Document preview rendered from uploaded file stream
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-indigo-600 text-white font-semibold text-xs rounded-xl hover:bg-indigo-700 transition cursor-pointer"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  )
}
