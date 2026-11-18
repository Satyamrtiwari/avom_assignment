import { CandidateRankingItem, JobDescriptionItem } from '../types'

export const DEFAULT_JDS: JobDescriptionItem[] = [
  {
    id: "jd-senior-java",
    title: "Senior Java Backend Developer",
    raw_text: "We are seeking a Senior Java Backend Developer with 4+ years experience in Java, Spring Boot, Microservices, Hibernate, AWS, Docker, PostgreSQL, and REST APIs.",
    required_skills: ["Java", "Spring Boot", "Microservices", "Hibernate", "AWS", "Docker", "PostgreSQL", "REST APIs"],
    preferred_skills: ["Apache Kafka", "Kubernetes", "Redis", "CI/CD"],
    experience_years: 4.0,
    experience_required: "4+ years of relevant backend production engineering experience",
    qualifications: ["Bachelor of Technology in Computer Science", "B.E. or equivalent MCA degree"],
    responsibilities: [
      "Architect and scale high-throughput Java microservices using Spring Boot",
      "Deploy scalable containerized applications on AWS cloud",
      "Design relational database schemas and optimize PostgreSQL queries"
    ],
    resumes_count: 12
  },
  {
    id: "jd-ai-engineer",
    title: "AI Engineer (LLMs & Vision)",
    raw_text: "Seeking an AI Engineer with expertise in PyTorch, Python, HuggingFace, Transformers, LangChain, RAG, and Vector Databases. 3+ years experience required.",
    required_skills: ["Python", "PyTorch", "Transformers", "LangChain", "RAG", "HuggingFace", "Vector Databases"],
    preferred_skills: ["MLflow", "Docker", "FastAPI", "Kubeflow"],
    experience_years: 3.0,
    experience_required: "3+ years AI/ML research or production development",
    qualifications: ["B.Tech / M.Tech in AI, Data Science, or Computer Science"],
    resumes_count: 5
  },
  {
    id: "jd-python-dev",
    title: "Senior Python Backend Engineer",
    raw_text: "Looking for a Senior Python Developer with Django/FastAPI, Celery, Redis, PostgreSQL, Docker, and AWS experience. Minimum 4 years experience.",
    required_skills: ["Python", "FastAPI", "Django", "PostgreSQL", "Redis", "Docker", "REST APIs"],
    preferred_skills: ["Celery", "AWS", "GraphQL", "Pytest"],
    experience_years: 4.0,
    experience_required: "4+ years production Python backend development",
    qualifications: ["B.S. / B.Tech Computer Science or related degree"],
    resumes_count: 8
  },
  {
    id: "jd-data-scientist",
    title: "Data Scientist (Predictive Modeling)",
    raw_text: "Data Scientist with strong background in Statistics, Machine Learning, Python, Pandas, Scikit-Learn, SQL, and Tableau. 3+ years experience.",
    required_skills: ["Python", "Machine Learning", "Statistics", "SQL", "Scikit-Learn", "Pandas"],
    preferred_skills: ["Tableau", "Apache Spark", "Docker", "A/B Testing"],
    experience_years: 3.0,
    experience_required: "3+ years analytics and predictive modeling",
    qualifications: ["Master's or B.Sc in Statistics, Mathematics, or Computer Science"],
    resumes_count: 6
  }
]

export const MOCK_JAVA_CANDIDATES: CandidateRankingItem[] = [
  {
    rank: 1,
    resume_id: "res-rohit-verma",
    candidate_name: "Rohit Verma",
    filename: "rohit_verma_sr_java.pdf",
    email: "rohit.verma@email.com",
    phone: "+91 98765 43210",
    experience_years: 7.9,
    total_experience_years: 7.9,
    relevant_experience_years: 7.9,
    experience_source: "work_history_dates",
    is_experience_unknown: false,
    overall_score: 81.8,
    skill_score: 85.0,
    semantic_score: 78.0,
    experience_score: 100.0,
    qualification_score: 100.0,
    matched_skills: ["Java", "Spring Boot", "Microservices", "Hibernate", "AWS", "Docker", "PostgreSQL", "REST APIs", "Apache Kafka"],
    missing_skills: ["Kubernetes", "Redis"],
    explanation: "Candidate exhibits exceptional technical alignment with core Senior Java Backend requirements. Primary skills (Java, Spring Boot) verified across 7.9 years of direct production tenure. AWS, Hibernate, and Microservices match the JD architecture directly. Strong educational grounding in Computer Science.",
    warnings: [],
    education: [
      { degree: "B.Tech", field: "Computer Science & Engineering", institution: "National Institute of Technology", year: "2016", is_in_progress: false }
    ],
    work_history: [
      { role: "Lead Backend Engineer", company: "TechCorp Systems", duration: "2021 - Present (4.7 yrs)", years: 4.7, verified: true },
      { role: "Senior Java Developer", company: "FinTech Labs Ltd", duration: "2018 - 2021 (3.2 yrs)", years: 3.2, verified: true }
    ]
  },
  {
    rank: 2,
    resume_id: "res-amit-sharma",
    candidate_name: "Amit Sharma",
    filename: "amit_sharma_lead.pdf",
    email: "amit.sharma@email.com",
    phone: "+91 98123 45678",
    experience_years: 8.9,
    total_experience_years: 8.9,
    relevant_experience_years: 8.9,
    experience_source: "work_history_dates",
    is_experience_unknown: false,
    overall_score: 76.6,
    skill_score: 82.0,
    semantic_score: 74.0,
    experience_score: 100.0,
    qualification_score: 100.0,
    matched_skills: ["Java", "Spring Boot", "Microservices", "Hibernate", "AWS", "Kubernetes", "Docker", "PostgreSQL", "REST APIs"],
    missing_skills: ["Apache Kafka", "Redis"],
    explanation: "Extensive 8.9-year trajectory in distributed Java enterprise applications. High degree of overlap across containerization, AWS cloud, and Spring framework. Proven leadership in microservices migrations.",
    warnings: [],
    education: [
      { degree: "B.E.", field: "Information Technology", institution: "Pune University", year: "2015", is_in_progress: false }
    ],
    work_history: [
      { role: "Principal Architect", company: "CloudScale India", duration: "2020 - Present (4.0 yrs)", years: 4.0, verified: true },
      { role: "Senior Java Developer", company: "Infosys Ltd", duration: "2015 - 2020 (4.9 yrs)", years: 4.9, verified: true }
    ]
  },
  {
    rank: 3,
    resume_id: "res-neha-patel",
    candidate_name: "Neha Patel",
    filename: "neha_patel_java.pdf",
    email: "neha.patel@email.com",
    phone: "+91 97234 56789",
    experience_years: 7.0,
    total_experience_years: 7.0,
    relevant_experience_years: 7.0,
    experience_source: "work_history_dates",
    is_experience_unknown: false,
    overall_score: 65.6,
    skill_score: 72.0,
    semantic_score: 68.0,
    experience_score: 100.0,
    qualification_score: 100.0,
    matched_skills: ["Java", "Spring Boot", "Microservices", "AWS", "Docker", "PostgreSQL", "REST APIs"],
    missing_skills: ["Hibernate", "Apache Kafka", "Kubernetes"],
    explanation: "Solid 7.0 years background delivering Spring Boot microservices on AWS cloud. Core Java language skills and REST architectural patterns verified. Missing secondary ORM (Hibernate) but demonstrates quick transferability.",
    warnings: [],
    education: [
      { degree: "B.Tech", field: "Computer Science", institution: "Gujarat Technological University", year: "2017", is_in_progress: false }
    ],
    work_history: [
      { role: "Senior Backend Developer", company: "E-Commerce Solutions", duration: "2020 - Present (4.2 yrs)", years: 4.2, verified: true },
      { role: "Software Engineer", company: "Wipro Technologies", duration: "2017 - 2020 (2.8 yrs)", years: 2.8, verified: true }
    ]
  },
  {
    rank: 4,
    resume_id: "res-vikas-singh",
    candidate_name: "Vikas Singh",
    filename: "vikas_singh_backend.pdf",
    email: "vikas.singh@email.com",
    phone: "+91 98345 67890",
    experience_years: 6.0,
    total_experience_years: 6.0,
    relevant_experience_years: 6.0,
    experience_source: "work_history_dates",
    is_experience_unknown: false,
    overall_score: 60.5,
    skill_score: 64.0,
    semantic_score: 62.0,
    experience_score: 100.0,
    qualification_score: 100.0,
    matched_skills: ["Java", "Spring Boot", "Docker", "SQL", "REST APIs"],
    missing_skills: ["AWS", "Hibernate", "Microservices", "Apache Kafka"],
    explanation: "Demonstrates 6.0 years of backend development with core Java and Spring Boot. Good database indexing knowledge, but cloud infrastructure (AWS) and distributed messaging (Kafka) are absent from profile.",
    warnings: [],
    education: [
      { degree: "MCA", field: "Computer Applications", institution: "Delhi University", year: "2018", is_in_progress: false }
    ],
    work_history: [
      { role: "Java Developer", company: "PayMatrix Solutions", duration: "2018 - Present (6.0 yrs)", years: 6.0, verified: true }
    ]
  },
  {
    rank: 5,
    resume_id: "res-sneha-reddy",
    candidate_name: "Sneha Reddy",
    filename: "sneha_reddy_java.pdf",
    email: "sneha.reddy@email.com",
    phone: "+91 98456 78901",
    experience_years: 6.0,
    total_experience_years: 6.0,
    relevant_experience_years: 6.0,
    experience_source: "work_history_dates",
    is_experience_unknown: false,
    overall_score: 60.3,
    skill_score: 65.0,
    semantic_score: 60.0,
    experience_score: 100.0,
    qualification_score: 100.0,
    matched_skills: ["Java", "Spring Boot", "Hibernate", "PostgreSQL", "REST APIs", "SQL"],
    missing_skills: ["AWS", "Docker", "Kubernetes", "Apache Kafka"],
    explanation: "Strong enterprise persistence layer background with Hibernate and PostgreSQL. Missing modern DevOps and container orchestration components.",
    warnings: [],
    education: [
      { degree: "B.Tech", field: "Computer Science", institution: "JNTU Hyderabad", year: "2018", is_in_progress: false }
    ],
    work_history: [
      { role: "Backend Engineer", company: "CyberSystems", duration: "2018 - Present (6.0 yrs)", years: 6.0, verified: true }
    ]
  },
  {
    rank: 6,
    resume_id: "res-ananya-sharma",
    candidate_name: "Ananya Sharma",
    filename: "medium_candidate_AI_engineer.pdf",
    email: "ananya.sharma@email.com",
    phone: "+91 98567 89012",
    experience_years: 5.0,
    total_experience_years: 5.0,
    relevant_experience_years: 2.5,
    experience_source: "work_history_dates",
    is_experience_unknown: false,
    overall_score: 41.2,
    skill_score: 38.0,
    semantic_score: 45.0,
    experience_score: 75.0,
    qualification_score: 100.0,
    matched_skills: ["Java", "Docker", "REST APIs", "SQL"],
    missing_skills: ["Spring Boot", "Hibernate", "Microservices", "AWS"],
    explanation: "AI/Data Engineer with secondary Java exposure. Missing core framework (Spring Boot) and enterprise persistence stack. Lower relevance damping applied.",
    warnings: ["Profile has primary emphasis on Data Science rather than Java enterprise backend."],
    education: [
      { degree: "B.Tech", field: "Information Science", institution: "VTU Belgaum", year: "2019", is_in_progress: false }
    ],
    work_history: [
      { role: "Machine Learning Engineer", company: "DataPulse AI", duration: "2021 - Present (3.0 yrs)", years: 3.0, verified: true },
      { role: "Junior Software Engineer", company: "Tata Consultancy Services", duration: "2019 - 2021 (2.0 yrs)", years: 2.0, verified: true }
    ]
  },
  {
    rank: 7,
    resume_id: "res-arjun-kumar",
    candidate_name: "Arjun Kumar",
    filename: "arjun_kumar_python.pdf",
    email: "arjun.kumar@email.com",
    phone: "+91 98678 90123",
    experience_years: 5.2,
    total_experience_years: 5.2,
    relevant_experience_years: 0.5,
    experience_source: "work_history_dates",
    is_experience_unknown: false,
    overall_score: 32.5,
    skill_score: 22.0,
    semantic_score: 42.0,
    experience_score: 50.0,
    qualification_score: 100.0,
    matched_skills: ["Docker", "PostgreSQL", "REST APIs", "SQL"],
    missing_skills: ["Java", "Spring Boot", "Hibernate", "Microservices", "AWS"],
    explanation: "Off-domain Python backend candidate. Missing primary required language (Java) and primary framework (Spring Boot). Automatic primary skill damping applied.",
    warnings: ["Candidate does not list primary skill 'Java'. Experience is in Python ecosystem."],
    education: [
      { degree: "B.Tech", field: "Computer Engineering", institution: "IIT Roorkee", year: "2019", is_in_progress: false }
    ],
    work_history: [
      { role: "Python Backend Developer", company: "Zomato", duration: "2019 - Present (5.2 yrs)", years: 5.2, verified: true }
    ]
  },
  {
    rank: 8,
    resume_id: "res-manish-gupta",
    candidate_name: "Manish Gupta",
    filename: "manish_gupta_junior.pdf",
    email: "manish.gupta@email.com",
    phone: "+91 98789 01234",
    experience_years: 1.5,
    total_experience_years: 1.5,
    relevant_experience_years: 1.5,
    experience_source: "work_history_dates",
    is_experience_unknown: false,
    overall_score: 21.1,
    skill_score: 28.0,
    semantic_score: 31.0,
    experience_score: 35.0,
    qualification_score: 90.0,
    matched_skills: ["Java", "REST APIs", "SQL"],
    missing_skills: ["Spring Boot", "Microservices", "Hibernate", "AWS", "Docker", "PostgreSQL"],
    explanation: "Junior level developer with 1.5 years experience against 4.0 years required. Substantial skills gap in cloud, ORM, and microservices architecture.",
    warnings: ["Experience deficit: 1.5 years verified vs 4.0 years required."],
    education: [
      { degree: "BCA", field: "Computer Applications", institution: "Indira Gandhi Open University", year: "2023", is_in_progress: false }
    ],
    work_history: [
      { role: "Junior Java Programmer", company: "ByteSoft", duration: "2023 - Present (1.5 yrs)", years: 1.5, verified: true }
    ]
  }
]
