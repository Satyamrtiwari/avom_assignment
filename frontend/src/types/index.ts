export interface SkillMatchDetail {
  skill: string
  weight: number
  matched: boolean
  is_primary?: boolean
  section?: string
}

export interface CandidateRankingItem {
  rank: number
  resume_id: string
  candidate_name: string
  filename?: string
  email?: string
  phone?: string
  experience_years: number | null
  total_experience_years?: number | null
  relevant_experience_years?: number | null
  experience_source?: string
  is_experience_unknown?: boolean
  overall_score: number
  skill_score: number
  semantic_score: number
  experience_score: number
  qualification_score: number
  matched_skills: string[]
  missing_skills: string[]
  candidate_skills?: string[]
  explanation?: string
  warnings?: string[]
  education?: Array<{
    degree: string
    field?: string
    institution?: string
    year?: string
    is_in_progress?: boolean
  }>
  work_history?: Array<{
    role: string
    company: string
    duration: string
    years: number
    verified: boolean
  }>
}

export interface JobDescriptionItem {
  id: string
  title: string
  raw_text?: string
  required_skills: string[]
  preferred_skills: string[]
  experience_years: number | null
  experience_required?: string
  qualifications?: string[]
  responsibilities?: string[]
  created_at?: string
  resumes_count?: number
}

export interface CandidateDetail {
  resume_id: string
  jd_id: string
  candidate_name: string
  email?: string
  phone?: string
  experience_years: number | null
  total_experience_years: number | null
  relevant_experience_years: number | null
  experience_source: string
  is_experience_unknown: boolean
  education: Array<{
    degree: string
    field?: string
    institution?: string
    year?: string
    is_in_progress?: boolean
  }>
  overall_score: number
  raw_cosine: number
  score_breakdown: {
    semantic_similarity: number
    skill_match: number
    experience_match: number
    qualification_match: number
  }
  matched_skills: string[]
  missing_skills: string[]
  candidate_skills?: string[]
  matched_skills_detailed?: Array<{
    skill: string
    weight: number
    matched: boolean
    is_primary?: boolean
  }>
  experience_comparison: {
    candidate_years: number
    required_years: number
    delta_years: number
    verdict: string
  }
  explanation: string
  warnings: string[]
  work_history?: Array<{
    role: string
    company: string
    duration: string
    years: number
    verified: boolean
  }>
}
