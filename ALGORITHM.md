# 🧠 ALGORITHM.md — Matching & Scoring Methodology

> **Project**: AI-Based Resume Matching & Candidate Ranking System  
> **Author**: Candidate  
> **Model**: Sentence Transformers (`all-MiniLM-L6-v2`) + spaCy (`en_core_web_sm`)

---

## 1. Executive Summary & Design Philosophy

A critical requirement of hiring algorithms is **explainability and transparency**. Pure black-box models (such as zero-shot prompts to external LLMs) suffer from:
1. Inconsistent scoring across identical runs.
2. High latency (1–3 seconds per resume) and external API costs.
3. Inability to mathematically audit or justify *why* Candidate A ranked higher than Candidate B.
4. Privacy concerns when sending candidate PII to external services.

Conversely, legacy keyword-matching systems (e.g. basic ATS systems) fail when candidates use synonyms (e.g., "K8s" instead of "Kubernetes") or describe concepts contextually rather than listing exact buzzwords.

**Our Solution**: A **hybrid, multi-signal scoring architecture** that marries:
- **Curated taxonomy-backed skill matching** with alias resolution.
- **Dense semantic vector embeddings** capturing contextual alignment.
- **Graduated experience evaluation** preventing arbitrary cliffs.
- **Discipline-aware qualification scoring**.

---

## 2. Multi-Signal Scoring Formula

The overall score is a normalized weighted sum across four orthogonal dimensions:

$$\text{OverallScore} = w_{\text{skill}} \cdot S_{\text{skill}} + w_{\text{semantic}} \cdot S_{\text{semantic}} + w_{\text{experience}} \cdot S_{\text{experience}} + w_{\text{qualification}} \cdot S_{\text{qualification}}$$

Where default weights configured in `.env` are:

| Signal | Weight ($w_i$) | Focus / Rationale |
|---|---|---|
| **$S_{\text{skill}}$ — Skill Coverage** | **35%** ($0.35$) | Core required competencies; directly interpretable by recruiters. |
| **$S_{\text{semantic}}$ — Semantic Fit** | **30%** ($0.30$) | Deep contextual understanding of project experience & responsibilities. |
| **$S_{\text{experience}}$ — Relevant Experience** | **20%** ($0.20$) | Seniority and domain track record vs job requirements. |
| **$S_{\text{qualification}}$ — Education & Discipline** | **15%** ($0.15$) | Educational baseline and technical relevance. |

$$\sum w_i = 0.35 + 0.30 + 0.20 + 0.15 = 1.0 \implies \text{OverallScore} \in [0, 100]$$

---

## 3. Mathematical Formulation of Component Signals

### 3.1. Skill Match Score ($S_{\text{skill}}$)

1. Skills from both the Job Description and candidate resumes are identified using spaCy's `PhraseMatcher` indexed against a comprehensive taxonomy (`skills.json`).
2. Every matched token or alias is mapped back to its canonical representation:
   - e.g., `"k8s"`, `"kube"` $\to$ `"Kubernetes"`
   - e.g., `"springboot"`, `"spring-boot"` $\to$ `"Spring Boot"`
   - e.g., `"postgres"`, `"psql"` $\to$ `"PostgreSQL"`
3. The overlap ratio is calculated strictly on canonical names:

$$S_{\text{skill}} = \frac{|\text{Skills}_{\text{JD}} \cap \text{Skills}_{\text{Resume}}|}{|\text{Skills}_{\text{JD}}|} \times 100$$

- **Matched Skills**: $\text{Skills}_{\text{JD}} \cap \text{Skills}_{\text{Resume}}$
- **Missing Skills**: $\text{Skills}_{\text{JD}} \setminus \text{Skills}_{\text{Resume}}$
- *Edge case*: If the JD specifies 0 extractable skills, $S_{\text{skill}}$ defaults to $100\%$ so the semantic and experience signals drive the ranking.

---

### 3.2. Semantic Similarity Score ($S_{\text{semantic}}$)

Captures contextual meaning that keyword lists miss entirely (e.g. matching *"architected resilient REST microservices"* with *"high-scale API development"*).

1. **Chunking & Mean-Pooling**:
   Sentence transformers have a maximum sequence length (256 word-pieces). Resumes typically span 400–1000 words. Rather than truncating, the document is segmented by paragraphs into cohesive chunks $C_1, C_2, \dots, C_k$, encoded into vectors $\vec{v}_1, \vec{v}_2, \dots, \vec{v}_k$, and mean-pooled:

   $$\vec{E} = \frac{1}{k} \sum_{i=1}^k \vec{v}_i, \quad \hat{E} = \frac{\vec{E}}{\|\vec{E}\|_2}$$

2. **Cosine Similarity**:
   Because embeddings are $L_2$-normalized unit vectors ($\|\hat{E}\| = 1$), cosine similarity simplifies to the dot product:

   $$\cos(\theta) = \hat{E}_{\text{JD}} \cdot \hat{E}_{\text{Resume}} = \sum_{j=1}^{384} \hat{E}_{\text{JD}, j} \cdot \hat{E}_{\text{Resume}, j}$$

3. **Scaling**:
   The value is clamped to $[0.0, 1.0]$ and scaled:

   $$S_{\text{semantic}} = \max(0.0, \min(1.0, \cos(\theta))) \times 100$$

---

### 3.3. Relevant Experience Score ($S_{\text{experience}}$)

Experience is extracted using both direct duration statements (`"5+ years of experience"`) and employment date-range calculations (`"2019 - Present"` $\implies 5\text{ years}$).

Let $Y_{\text{req}}$ be the required experience in years, and $Y_{\text{actual}}$ be the candidate's verified experience. We define the ratio $R = \frac{Y_{\text{actual}}}{Y_{\text{req}}}$.

$$S_{\text{experience}} = \begin{cases} 
100.0 & \text{if } R \ge 1.0 \text{ (Meets or exceeds)} \\
70.0 + \left(\frac{R - 0.70}{0.30}\right) \times 30.0 & \text{if } 0.70 \le R < 1.0 \text{ (Slightly below)} \\
\left(\frac{R}{0.70}\right) \times 70.0 & \text{if } R < 0.70 \text{ (Significantly below)}
\end{cases}$$

**Why this curve?**
- **No Overqualification Bias**: A candidate with 10 years experience applying for a 4-year role receives $100\%$ (not a bonus that unfairly penalizes capable candidates).
- **Graceful Degradation**: A candidate with 3.5 years for a 4-year requirement ($R=0.875$) receives $87.5\%$ rather than being abruptly filtered out.

---

### 3.4. Qualification Score ($S_{\text{qualification}}$)

Evaluates academic level and technical discipline alignment:

1. **Degree Level Hierarchy**:
   $\text{PhD} (4) > \text{Master's/M.Tech} (3) > \text{Bachelor's/B.Tech} (2) > \text{Diploma} (1)$.
2. **Discipline Relevance**:
   Checks for technical fields: *Computer Science, IT, Software Engineering, Electronics, Data Science*.
3. **Scoring Table**:
   - Candidate degree level $\ge$ JD requirement in technical discipline $\to 100\%$
   - Candidate degree level $\ge$ JD requirement without specified field $\to 90\%$
   - Candidate degree level 1 level below requirement (e.g. B.Tech for Master's) in tech field $\to 80\%$
   - Any recognized post-secondary degree $\to 65\%$
   - No education section detected (fallback for industry professionals) $\to 55\%$

---

## 4. Explainability & Human-Readable Reasoning

Recruiters need to understand why a candidate was ranked where they were. For every candidate evaluated, the system dynamically constructs an audit narrative:

```text
"{Name} achieved an overall match score of {Overall}%. 
Matched {N} of {Total} required skills ({Matched_Preview}). Key missing skills: {Missing_Preview}. 
Experience: {Experience_Verdict}. 
{Semantic_Alignment_Commentary}. 
{Education_Commentary}."
```

Example output:
> *"Amit Sharma achieved an overall match score of 89.2%. Matched 11 of 12 required skills (Java, Spring Boot, PostgreSQL, Docker, Kubernetes (+6 more)). Key missing skills: Apache Kafka. Experience: Meets or exceeds requirement (6 years actual vs 4 years required). Project and work history show strong semantic alignment with the role's responsibilities. Educational background fully satisfies degree and technical discipline criteria."*

---

## 5. Caching & Performance Considerations

1. **Persistent Embedding Cache**:
   Embeddings are generated once during document upload and saved to SQLite's `embedding` JSON column. Re-running matching queries against existing candidates requires **0 neural forward passes** ($O(1)$ database retrieval).
2. **Batch Encoding**:
   When batch uploading 10–20 resumes, all document chunks are passed to `model.encode(batch_size=32)` in a single vectorized forward pass, achieving ~15–20 resumes/second throughput on CPU without requiring GPU hardware.

