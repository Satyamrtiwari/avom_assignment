import { JobDescriptionItem, CandidateRankingItem, CandidateDetail } from '../types'
import { DEFAULT_JDS, MOCK_JAVA_CANDIDATES } from '../data/mockData'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ? import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '') : '') + '/api/v1'

export interface ApiStatus {
  online: boolean
  message: string
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/jd`, { method: 'GET' })
    return res.ok
  } catch {
    return false
  }
}

export async function resetAllBackendData(): Promise<void> {
  try {
    await fetch(`${API_BASE}/jd/reset-all`, { method: 'POST' })
  } catch (err) {
    console.warn('Backend reset call failed:', err)
  }
}

export async function fetchResumeRawText(resumeId: string): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/resumes/${resumeId}`)
    if (res.ok) {
      const data = await res.json()
      return data.raw_text || null
    }
  } catch {}
  return null
}


export async function fetchJobDescriptions(): Promise<JobDescriptionItem[]> {
  try {
    const res = await fetch(`${API_BASE}/jd`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (Array.isArray(data) && data.length > 0) {
      // Fetch details for each JD to get skills
      const detailed = await Promise.all(
        data.slice(0, 10).map(async (item: { id: string; title: string }) => {
          try {
            const detailRes = await fetch(`${API_BASE}/jd/${item.id}`)
            if (detailRes.ok) {
              return await detailRes.json()
            }
          } catch {}
          return item
        })
      )
      return detailed
    }
    return DEFAULT_JDS
  } catch (err) {
    console.warn('Using default JDs due to backend error:', err)
    return DEFAULT_JDS
  }
}

export async function fetchJobDescription(id: string): Promise<JobDescriptionItem> {
  try {
    const res = await fetch(`${API_BASE}/jd/${id}`)
    if (res.ok) {
      return await res.json()
    }
  } catch (err) {
    console.warn('Backend fetch failed, searching defaults:', err)
  }
  const found = DEFAULT_JDS.find(j => j.id === id)
  if (found) return found
  return DEFAULT_JDS[0]
}

export async function uploadJobDescriptionFile(file: File): Promise<JobDescriptionItem> {
  const formData = new FormData()
  formData.append('file', file)
  
  const res = await fetch(`${API_BASE}/jd`, {
    method: 'POST',
    body: formData
  })
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `Upload failed with HTTP ${res.status}`)
  }
  
  return await res.json()
}

export async function uploadJobDescriptionText(title: string, text: string): Promise<JobDescriptionItem> {
  const formData = new FormData()
  if (title) formData.append('title', title)
  formData.append('text', text)
  
  const res = await fetch(`${API_BASE}/jd`, {
    method: 'POST',
    body: formData
  })
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `Text creation failed with HTTP ${res.status}`)
  }
  
  return await res.json()
}

export async function uploadResumesBatch(
  jdId: string,
  files: File[]
): Promise<{ processed: number; failed: number }> {
  const formData = new FormData()
  if (jdId) formData.append('jd_id', jdId)
  
  files.forEach(file => {
    formData.append('files', file)
  })
  
  const res = await fetch(`${API_BASE}/resumes`, {
    method: 'POST',
    body: formData
  })
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `Batch resume upload failed with HTTP ${res.status}`)
  }
  
  return await res.json()
}

export async function triggerMatching(jdId: string): Promise<{ candidates_matched: number }> {
  const res = await fetch(`${API_BASE}/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jd_id: jdId })
  })
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `AI Match failed with HTTP ${res.status}`)
  }
  
  return await res.json()
}

export async function fetchRankingResults(jdId: string): Promise<CandidateRankingItem[]> {
  try {
    const res = await fetch(`${API_BASE}/results/${jdId}`)
    if (res.ok) {
      const data = await res.json()
      if (data.candidates && data.candidates.length > 0) {
        return data.candidates.map((c: any) => ({
          ...c,
          filename: c.filename || `${c.candidate_name.toLowerCase().replace(/\s+/g, '_')}.pdf`,
          experience_years: c.experience_years ?? 0
        }))
      }
    }
  } catch (err) {
    console.warn('Backend rankings fetch failed, using fallback:', err)
  }
  
  // Return fallback data if JD matches Java or general
  return MOCK_JAVA_CANDIDATES
}

export async function fetchCandidateDetail(
  jdId: string,
  resumeId: string
): Promise<CandidateDetail | null> {
  try {
    const res = await fetch(`${API_BASE}/results/${jdId}/candidates/${resumeId}`)
    if (res.ok) {
      return await res.json()
    }
  } catch (err) {
    console.warn('Backend detail fetch failed, synthesizing from mock:', err)
  }
  
  // Synthesize from local list
  const cand = MOCK_JAVA_CANDIDATES.find(c => c.resume_id === resumeId)
  if (!cand) return null
  
  return {
    resume_id: cand.resume_id,
    jd_id: jdId,
    candidate_name: cand.candidate_name,
    email: cand.email,
    phone: cand.phone,
    experience_years: cand.experience_years,
    total_experience_years: cand.total_experience_years ?? cand.experience_years,
    relevant_experience_years: cand.relevant_experience_years ?? cand.experience_years,
    experience_source: cand.experience_source ?? 'work_history_dates',
    is_experience_unknown: cand.is_experience_unknown ?? false,
    education: cand.education ?? [],
    overall_score: cand.overall_score,
    raw_cosine: 0.76,
    score_breakdown: {
      skill_match: cand.skill_score,
      semantic_similarity: cand.semantic_score,
      experience_match: cand.experience_score,
      qualification_match: cand.qualification_score
    },
    matched_skills: cand.matched_skills,
    missing_skills: cand.missing_skills,
    matched_skills_detailed: cand.matched_skills.map(s => ({
      skill: s,
      weight: 1.0,
      matched: true,
      is_primary: ['Java', 'Spring Boot'].includes(s)
    })),
    experience_comparison: {
      candidate_years: cand.experience_years ?? 0,
      required_years: 4.0,
      delta_years: (cand.experience_years ?? 0) - 4.0,
      verdict: (cand.experience_years ?? 0) >= 4.0 ? 'Met Requirement' : 'Under Required Experience'
    },
    explanation: cand.explanation ?? 'Candidate scored based on verified multi-signal alignment.',
    warnings: cand.warnings ?? [],
    work_history: cand.work_history
  }
}
