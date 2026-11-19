import React, { useState, useMemo } from 'react'
import { Search, SlidersHorizontal, Download, ArrowUpDown, ChevronRight, CheckCircle2, AlertTriangle, FileText, Users, Eye, Loader2, Sparkles, Cpu, Layers } from 'lucide-react'
import { CandidateRankingItem } from '../types'

interface CandidateTableProps {
  candidates: CandidateRankingItem[]
  selectedCandidate: CandidateRankingItem | null
  onSelectCandidate: (candidate: CandidateRankingItem) => void
  onPreviewResume: (candidate: CandidateRankingItem) => void
  onExportCSV: () => void
  isMatching?: boolean
  stagedCount?: number
  jdTitle?: string
}

export const CandidateTable: React.FC<CandidateTableProps> = ({
  candidates,
  selectedCandidate,
  onSelectCandidate,
  onPreviewResume,
  onExportCSV,
  isMatching = false,
  stagedCount = 0,
  jdTitle = ""
}) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<'score' | 'exp' | 'name'>('score')
  const [minScoreFilter, setMinScoreFilter] = useState<number>(0)

  // Filter & Sort logic
  const filteredCandidates = useMemo(() => {
    return candidates
      .filter(c => {
        const matchesSearch =
          c.candidate_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          c.matched_skills.some(s => s.toLowerCase().includes(searchTerm.toLowerCase())) ||
          (c.filename && c.filename.toLowerCase().includes(searchTerm.toLowerCase()))
        const matchesScore = c.overall_score >= minScoreFilter
        return matchesSearch && matchesScore
      })
      .sort((a, b) => {
        if (sortBy === 'score') return b.overall_score - a.overall_score
        if (sortBy === 'exp') return (b.experience_years ?? 0) - (a.experience_years ?? 0)
        if (sortBy === 'name') return a.candidate_name.localeCompare(b.candidate_name)
        return 0
      })
  }, [candidates, searchTerm, sortBy, minScoreFilter])

  // Get Initials for Avatar
  const getInitials = (name: string) => {
    const parts = name.trim().split(' ')
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    return name.slice(0, 2).toUpperCase()
  }

  // Get Rank Badge Style
  const getRankBadge = (rank: number) => {
    if (rank === 1) return 'bg-amber-100 text-amber-900 border-amber-300 font-extrabold'
    if (rank === 2) return 'bg-slate-200 text-slate-800 border-slate-300 font-extrabold'
    if (rank === 3) return 'bg-amber-50 text-amber-800 border-amber-200 font-bold'
    return 'bg-slate-100 text-slate-600 border-slate-200 font-medium'
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs hover:shadow-sm transition-all duration-200 p-5">
      
      {/* Table Card Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4 pb-4 border-b border-slate-100">
        
        {/* Title & Count */}
        <div className="flex items-center space-x-3">
          <span className="w-6 h-6 rounded-lg bg-indigo-50 border border-indigo-200/70 text-indigo-700 flex items-center justify-center font-extrabold text-xs">
            3
          </span>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-slate-900 tracking-tight">
                Candidate Rankings
              </h2>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
                candidates.length > 0
                  ? 'text-indigo-700 bg-indigo-50 border-indigo-200'
                  : 'text-slate-500 bg-slate-100 border-slate-200'
              }`}>
                {candidates.length} Evaluated
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Ranked by multi-signal model: Skill Match, Semantic Matching, Experience, Degree.
            </p>
          </div>
        </div>

        {/* Toolbar: Search, Filters, Export (Shown only when candidates exist) */}
        {candidates.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            
            {/* Search bar */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search candidate or skill..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-indigo-500 focus:bg-white w-48 sm:w-56 transition"
              />
            </div>

            {/* Sort Dropdown */}
            <div className="flex items-center space-x-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-600">
              <ArrowUpDown className="w-3 h-3 text-slate-400" />
              <span className="text-[11px] font-semibold text-slate-500">Sort:</span>
              <select
                aria-label="Sort Candidates By"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-transparent font-medium text-slate-800 outline-none cursor-pointer"
              >
                <option value="score">Match Score</option>
                <option value="exp">Experience</option>
                <option value="name">Name</option>
              </select>
            </div>

            {/* Export Button */}
            <button
              onClick={onExportCSV}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 hover:border-slate-300 transition shadow-2xs cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Export CSV</span>
            </button>

          </div>
        )}
      </div>

      {/* Candidate Table OR Matching In Progress OR Clean Empty State */}
      {isMatching ? (
        /* MATCHING IN PROGRESS STATE */
        <div className="py-14 px-6 text-center bg-indigo-50/50 rounded-xl border border-indigo-100 flex flex-col items-center justify-center animate-fade-in">
          <div className="relative mb-4">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-lg shadow-indigo-200">
              <Sparkles className="w-8 h-8 animate-pulse text-indigo-200" />
            </div>
            <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 border-2 border-white flex items-center justify-center">
              <Loader2 className="w-3 h-3 text-white animate-spin" />
            </div>
          </div>
          
          <h3 className="text-base font-extrabold text-slate-900 mb-1">
            AI Multi-Signal Matching in Progress...
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mb-5">
            Evaluating {stagedCount || 'staged'} candidate resumes against <strong className="text-indigo-900 font-bold">"{jdTitle || 'Job Description'}"</strong>. Computing dense semantic vectors and cross-referencing experience tenures...
          </p>

          {/* 4 Pipeline Stages */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5 max-w-2xl w-full text-left">
            <div className="bg-white p-3 rounded-xl border border-indigo-100 shadow-2xs">
              <div className="flex items-center space-x-1.5 text-xs font-bold text-indigo-700 mb-0.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>1. Parsing Documents</span>
              </div>
              <p className="text-[10px] text-slate-400">PDF text &amp; layout extraction</p>
            </div>

            <div className="bg-white p-3 rounded-xl border border-indigo-100 shadow-2xs">
              <div className="flex items-center space-x-1.5 text-xs font-bold text-indigo-700 mb-0.5">
                <Loader2 className="w-3.5 h-3.5 text-indigo-600 animate-spin shrink-0" />
                <span>2. Semantic Matching</span>
              </div>
              <p className="text-[10px] text-slate-400">384-d semantic embedding</p>
            </div>

            <div className="bg-white p-3 rounded-xl border border-indigo-100 shadow-2xs">
              <div className="flex items-center space-x-1.5 text-xs font-bold text-indigo-700 mb-0.5">
                <Loader2 className="w-3.5 h-3.5 text-indigo-600 animate-spin shrink-0" />
                <span>3. Skill Matching</span>
              </div>
              <p className="text-[10px] text-slate-400">IDF weights &amp; primary damping</p>
            </div>

            <div className="bg-white p-3 rounded-xl border border-indigo-100 shadow-2xs">
              <div className="flex items-center space-x-1.5 text-xs font-bold text-indigo-700 mb-0.5">
                <Loader2 className="w-3.5 h-3.5 text-indigo-600 animate-spin shrink-0" />
                <span>4. Experience Audit</span>
              </div>
              <p className="text-[10px] text-slate-400">Work history &amp; degree fit</p>
            </div>
          </div>
        </div>
      ) : candidates.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-y border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-2.5 px-3 rounded-l-lg w-16 text-center">Rank</th>
                <th className="py-2.5 px-4 min-w-[220px]">Candidate Name</th>
                <th className="py-2.5 px-4 min-w-[130px]">Experience</th>
                <th className="py-2.5 px-4 min-w-[110px]">Match %</th>
                <th className="py-2.5 px-4 min-w-[280px]">Matched Skills</th>
                <th className="py-2.5 px-3 rounded-r-lg w-12 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {filteredCandidates.length > 0 ? (
                filteredCandidates.map((cand) => {
                  const isSelected = selectedCandidate?.resume_id === cand.resume_id
                  return (
                    <tr
                      key={cand.resume_id}
                      onClick={() => onSelectCandidate(cand)}
                      className={`cursor-pointer transition duration-150 ${
                        isSelected
                          ? 'bg-indigo-50/70 border-l-4 border-l-indigo-600'
                          : 'hover:bg-slate-50/80'
                      }`}
                    >
                      {/* Rank */}
                      <td className="py-3 px-3 text-center">
                        <span className={`inline-flex items-center justify-center w-7 h-7 rounded-lg text-xs border ${getRankBadge(cand.rank)}`}>
                          #{cand.rank}
                        </span>
                      </td>

                      {/* Candidate Name & Avatar */}
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-3">
                          <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
                            isSelected
                              ? 'bg-indigo-600 text-white'
                              : 'bg-indigo-100/80 text-indigo-800'
                          }`}>
                            {getInitials(cand.candidate_name)}
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center space-x-1.5">
                              <p className="font-bold text-slate-900 truncate">
                                {cand.candidate_name}
                              </p>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  onPreviewResume(cand)
                                }}
                                className="p-1 rounded-md text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition cursor-pointer"
                                title="View Full Resume"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>
                            </div>
                            <p className="text-[11px] text-slate-400 truncate flex items-center">
                              <FileText className="w-3 h-3 mr-1 text-slate-400 shrink-0" />
                              {cand.filename || `${cand.candidate_name.toLowerCase().replace(/\s+/g, '_')}.pdf`}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* Experience */}
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-1.5">
                          <span className="font-bold text-slate-800">
                            {cand.experience_years !== null ? `${cand.experience_years.toFixed(1)} yrs` : 'N/A'}
                          </span>
                          <span className="inline-flex items-center text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                            <CheckCircle2 className="w-2.5 h-2.5 mr-0.5" />
                            Verified
                          </span>
                        </div>
                      </td>

                      {/* Match % */}
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-extrabold border ${
                          cand.overall_score >= 80
                            ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                            : cand.overall_score >= 60
                            ? 'bg-indigo-50/50 text-indigo-600 border-indigo-200/60'
                            : cand.overall_score >= 40
                            ? 'bg-slate-100 text-slate-700 border-slate-200'
                            : 'bg-slate-100 text-slate-500 border-slate-200'
                        }`}>
                          {cand.overall_score.toFixed(1)}% Match
                        </span>
                      </td>

                      {/* Matched Skills */}
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1 max-w-sm">
                          {cand.matched_skills.slice(0, 4).map((skill, sIdx) => (
                            <span
                              key={sIdx}
                              className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200"
                            >
                              {skill}
                            </span>
                          ))}
                          {cand.matched_skills.length > 4 && (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold text-slate-500 bg-slate-50 border border-slate-200">
                              +{cand.matched_skills.length - 4} more
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Action: Eye Preview + Drawer Arrow */}
                      <td className="py-3 px-3 text-center">
                        <div className="flex items-center justify-center space-x-1">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              onPreviewResume(cand)
                            }}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition cursor-pointer"
                            title="View Full Resume"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <div className={`w-7 h-7 rounded-full flex items-center justify-center transition ${
                            isSelected ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
                          }`}>
                            <ChevronRight className="w-4 h-4" />
                          </div>
                        </div>
                      </td>
                    </tr>
                  )
                })
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    No candidates match the search filters. Try adjusting your search query.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        /* CLEAN EMPTY STATE */
        <div className="py-16 text-center">
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto mb-3 text-indigo-500 shadow-xs">
            <Users className="w-7 h-7 stroke-[1.75]" />
          </div>
          <h3 className="text-sm font-bold text-slate-900 mb-1">
            No Candidate Rankings Yet
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
            Upload a Job Description in Step 1, add candidate resumes in Step 2, and click <strong className="text-indigo-600 font-semibold">"Run AI Match"</strong> to generate candidate rankings.
          </p>
          <div className="inline-flex items-center space-x-2 text-[11px] font-medium text-slate-400 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200">
            <span>Awaiting input: Step 1 (JD) &amp; Step 2 (Resumes)</span>
          </div>
        </div>
      )}

      {/* Table Footer */}
      {candidates.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <span>Showing {filteredCandidates.length} of {candidates.length} candidates</span>
          <span className="text-[11px] text-slate-400">Click any candidate row to view detailed AI signal breakdown</span>
        </div>
      )}

    </div>
  )
}
