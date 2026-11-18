import React, { useRef } from 'react'
import { Upload, Sparkles, Check, FileCheck, X, Loader2, Trash2 } from 'lucide-react'

interface ResumeUploadCardProps {
  stagedFiles: File[]
  onUploadResumes: (files: File[]) => void
  onRemoveStagedFile: (index: number) => void
  onClearAllStaged: () => void
  onRunMatch: () => Promise<void>
  isUploading: boolean
  isMatching: boolean
  hasJd: boolean
}

export const ResumeUploadCard: React.FC<ResumeUploadCardProps> = ({
  stagedFiles,
  onUploadResumes,
  onRemoveStagedFile,
  onClearAllStaged,
  onRunMatch,
  isUploading,
  isMatching,
  hasJd
}) => {
  const [dragOver, setDragOver] = React.useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return
    onUploadResumes(Array.from(files))
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const canRunMatch = hasJd && stagedFiles.length > 0 && !isMatching && !isUploading

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs hover:shadow-sm transition-all duration-200 p-5 flex flex-col justify-between h-full min-h-[340px]">
      
      {/* Top Card Header */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2.5">
            <span className="w-6 h-6 rounded-lg bg-indigo-50 border border-indigo-200/70 text-indigo-700 flex items-center justify-center font-extrabold text-xs">
              2
            </span>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Upload Resumes
            </h2>
          </div>

          {/* Staged count badge */}
          {stagedFiles.length > 0 ? (
            <div className="flex items-center space-x-2">
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <Check className="w-3 h-3 mr-1 text-emerald-600" />
                {stagedFiles.length} Resume{stagedFiles.length > 1 ? 's' : ''} Staged
              </span>
              <button
                onClick={onClearAllStaged}
                className="text-[11px] text-slate-400 hover:text-rose-600 transition"
                title="Clear all staged resumes"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-500 border border-slate-200">
              0 Resumes Staged
            </span>
          )}
        </div>

        <p className="text-xs text-slate-500 mb-3.5">
          Batch dropzone for multi-candidate evaluation (PDF, DOCX, TXT supported).
        </p>

        {/* Drag & Drop Dropzone Box */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition ${
            dragOver
              ? 'border-indigo-600 bg-indigo-50/70'
              : 'border-indigo-200 hover:border-indigo-400 bg-indigo-50/20'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => handleFiles(e.target.files)}
            multiple
            accept=".pdf,.docx,.txt"
            className="hidden"
          />
          <div className="w-9 h-9 rounded-full bg-indigo-100/70 text-indigo-600 flex items-center justify-center mx-auto mb-2">
            <Upload className="w-4 h-4 stroke-[2.2]" />
          </div>
          <p className="text-xs font-bold text-slate-900 mb-0.5">
            Drag-and-drop batch dropzone
          </p>
          <p className="text-[11px] text-slate-500">
            Click to browse or drop candidate resume files here
          </p>
        </div>

        {/* Staged Files List (Only Real Uploaded Files) */}
        <div className="mt-3">
          {stagedFiles.length > 0 ? (
            <div className="space-y-1 max-h-[85px] overflow-y-auto pr-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Staged Files ({stagedFiles.length})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {stagedFiles.map((file, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200 group"
                  >
                    <FileCheck className="w-3 h-3 mr-1 text-emerald-600 shrink-0" />
                    <span className="max-w-[130px] truncate" title={file.name}>
                      {file.name}
                    </span>
                    <span className="text-[10px] text-slate-400 ml-1">
                      ({formatFileSize(file.size)})
                    </span>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); onRemoveStagedFile(i) }}
                      className="ml-1 text-slate-400 hover:text-rose-600 p-0.5 rounded transition"
                      title="Remove file"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-3 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center text-xs text-slate-400">
              No resumes uploaded yet. Upload one or more resumes to match against the JD.
            </div>
          )}
        </div>
      </div>

      {/* Primary Action Button: RUN AI MATCH */}
      <div className="mt-4 pt-3 border-t border-slate-100">
        <button
          onClick={onRunMatch}
          disabled={!canRunMatch}
          className={`w-full py-2.5 px-4 font-bold text-sm rounded-xl transition-all flex items-center justify-center space-x-2 ${
            canRunMatch
              ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-200 hover:shadow-indigo-300 cursor-pointer'
              : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
          }`}
        >
          {isMatching ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-white" />
              <span>Analyzing Multi-Signal Model...</span>
            </>
          ) : (
            <>
              <Sparkles className={`w-4 h-4 ${canRunMatch ? 'text-indigo-200' : 'text-slate-300'}`} />
              <span>
                {!hasJd
                  ? "Upload JD in Step 1 to Begin"
                  : stagedFiles.length === 0
                  ? "Upload Resumes to Run Match"
                  : `Run AI Match (${stagedFiles.length} Resume${stagedFiles.length > 1 ? 's' : ''})`}
              </span>
            </>
          )}
        </button>
      </div>

    </div>
  )
}
