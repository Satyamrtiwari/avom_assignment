import React, { useState, useRef } from 'react'
import { FileText, Upload, Check, AlertCircle, Sparkles, X, Plus } from 'lucide-react'
import { JobDescriptionItem } from '../types'

interface JobDescriptionCardProps {
  jd: JobDescriptionItem | null
  onUploadFile: (file: File) => Promise<void>
  onUploadText: (title: string, text: string) => Promise<void>
  onClearJd: () => void
  isUploading: boolean
}

export const JobDescriptionCard: React.FC<JobDescriptionCardProps> = ({
  jd,
  onUploadFile,
  onUploadText,
  onClearJd,
  isUploading
}) => {
  const [activeTab, setActiveTab] = useState<'upload_file' | 'enter_text'>('upload_file')
  const [textTitle, setTextTitle] = useState('')
  const [textContent, setTextContent] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUploadFile(e.dataTransfer.files[0])
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUploadFile(e.target.files[0])
    }
  }

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!textContent.trim()) return
    await onUploadText(textTitle || "Custom Job Description", textContent)
    setTextTitle('')
    setTextContent('')
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs hover:shadow-sm transition-all duration-200 p-5 flex flex-col justify-between h-full min-h-[340px]">

      {/* Top Card Header */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2.5">
            <span className="w-6 h-6 rounded-lg bg-indigo-50 border border-indigo-200/70 text-indigo-700 flex items-center justify-center font-extrabold text-xs">
              1
            </span>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Job Description
            </h2>
          </div>

          {/* Action Tabs / Switcher */}
          {!jd ? (
            <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg text-xs">
              <button
                onClick={() => setActiveTab('upload_file')}
                className={`px-2.5 py-1 rounded-md font-semibold transition ${activeTab === 'upload_file'
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                  }`}
              >
                Upload File
              </button>
              <button
                onClick={() => setActiveTab('enter_text')}
                className={`px-2.5 py-1 rounded-md font-semibold transition ${activeTab === 'enter_text'
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                  }`}
              >
                Paste Text
              </button>
            </div>
          ) : (
            <button
              onClick={onClearJd}
              className="text-xs font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 px-2.5 py-1 rounded-lg transition flex items-center space-x-1"
            >
              <X className="w-3 h-3" />
              <span>Clear JD</span>
            </button>
          )}
        </div>

        <p className="text-xs text-slate-500 mb-3.5">
          {jd
            ? "Requisition parsed. Core competencies and experience benchmarks extracted."
            : "Upload a Job Description document or paste requirements to extract skills and benchmarks."}
        </p>

        {/* STATE A: JD IS UPLOADED / ACTIVE */}
        {jd ? (
          <div>
            {/* Active JD File Chip */}
            <div className="bg-indigo-50/50 border border-indigo-200/70 rounded-xl p-3 mb-3.5 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-xs">
                  <FileText className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-900 truncate max-w-[200px] sm:max-w-[240px]">
                      {jd.title}
                    </span>
                    <span className="inline-flex items-center px-1.5 py-0.2 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <Check className="w-2.5 h-2.5 mr-0.5" />
                      Uploaded
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500">
                    Required Tenure: {jd.experience_years ? `${jd.experience_years}+ Years Experience` : "Not specified"}
                  </span>
                </div>
              </div>

              <button
                onClick={onClearJd}
                className="text-xs font-semibold text-slate-500 hover:text-slate-800 bg-white border border-slate-200 px-2 py-1 rounded-lg hover:border-slate-300 transition"
              >
                Change
              </button>
            </div>

            {/* Extracted Skills Section */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  Extracted Skills &amp; Requirements
                </span>
                <span className="text-[10px] text-indigo-600 font-semibold bg-indigo-50 px-1.5 py-0.2 rounded">
                  {jd.required_skills?.length || 0} Required • {jd.preferred_skills?.length || 0} Preferred
                </span>
              </div>

              {/* Legend indicator */}
              <div className="flex items-center space-x-3 text-[10px] text-slate-400 mb-2">
                <span className="flex items-center">
                  <span className="w-2 h-2 rounded bg-indigo-100 border border-indigo-300 mr-1 inline-block"></span>
                  <strong className="text-indigo-900 font-semibold mr-0.5">Blue:</strong> Required (Must-Have)
                </span>
                <span className="flex items-center">
                  <span className="w-2 h-2 rounded bg-white border border-dashed border-slate-400 mr-1 inline-block"></span>
                  <strong className="text-slate-700 font-semibold mr-0.5">+ White:</strong> Preferred (Nice-to-Have)
                </span>
              </div>

              <div className="flex flex-wrap gap-1.5 max-h-[110px] overflow-y-auto pr-1">
                {/* Experience Tag */}
                {jd.experience_years && (
                  <span
                    className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200/90"
                    title="Experience Requirement: Minimum verified production tenure"
                  >
                    ⚡ {jd.experience_years}+ Yrs Req
                  </span>
                )}

                {/* Primary & Required Skills */}
                {jd.required_skills && jd.required_skills.length > 0 ? (
                  jd.required_skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-indigo-50 text-indigo-800 border border-indigo-200/80 shadow-2xs cursor-help"
                      title="Required Skill (Must-Have): Full weight in match scoring"
                    >
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-400 italic">
                    No required skills extracted
                  </span>
                )}

                {/* Preferred skills with lighter shade */}
                {jd.preferred_skills?.map((skill, idx) => (
                  <span
                    key={`pref-${idx}`}
                    className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-slate-50 text-slate-600 border border-dashed border-slate-300 cursor-help"
                    title="Preferred Skill (Nice-to-Have): Bonus credit, not penalized if missing"
                  >
                    + {skill}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* STATE B: NO JD YET (FRESH EMPTY STATE) */
          <div>
            {activeTab === 'upload_file' ? (
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${dragOver
                    ? 'border-indigo-500 bg-indigo-50/50'
                    : 'border-slate-300 hover:border-indigo-400 bg-slate-50/60'
                  }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  accept=".pdf,.docx,.txt,.md"
                  className="hidden"
                />
                <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-2">
                  <Upload className="w-5 h-5" />
                </div>
                <p className="text-xs font-bold text-slate-900 mb-1">
                  Click to upload or drag &amp; drop JD document
                </p>
                <p className="text-[11px] text-slate-500">
                  Supports PDF, DOCX, TXT up to 5MB
                </p>
              </div>
            ) : (
              <form onSubmit={handleTextSubmit} className="space-y-2">
                <input
                  type="text"
                  placeholder="Job Title (e.g. Senior Java Backend Developer)"
                  value={textTitle}
                  onChange={(e) => setTextTitle(e.target.value)}
                  className="w-full text-xs px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-indigo-500"
                />
                <textarea
                  placeholder="Paste job description requirements and tech stack here..."
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  rows={4}
                  className="w-full text-xs px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-indigo-500 resize-none"
                />
                <div className="flex justify-end space-x-2">
                  <button
                    type="submit"
                    disabled={isUploading || !textContent.trim()}
                    className="text-xs px-3 py-1.5 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition cursor-pointer"
                  >
                    {isUploading ? "Extracting..." : "Parse Job Description"}
                  </button>
                </div>
              </form>
            )}

            {/* Empty placeholder for skills */}
            <div className="mt-4 p-3 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center text-xs text-slate-400">
              Extracted skills and requirements will appear here once a JD is uploaded.
            </div>
          </div>
        )}
      </div>

      {/* Card Footer status info */}
      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
        <span></span>
        {jd?.qualifications?.[0] ? (
          <span className="truncate max-w-[180px]" title={jd.qualifications[0]}>
            🎓 {jd.qualifications[0]}
          </span>
        ) : (
          <span>Step 1 of 3</span>
        )}
      </div>

    </div>
  )
}
