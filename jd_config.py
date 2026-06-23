"""
jd_config.py — Job Description Configuration
Redrob AI Hackathon — Senior AI Engineer, Founding Team

Single source of truth for all scoring weights, skill taxonomies,
keyword lists, and disqualifier rules. The scorer (scorer.py) is
JD-agnostic — swap this file to rank for a different role.
"""

# =========================================================================
# JOB DESCRIPTION METADATA
# =========================================================================
JD_TITLE   = "Senior AI Engineer — Founding Team"
JD_COMPANY = "Redrob AI"

# =========================================================================
# COMPONENT WEIGHTS  (must sum to 1.0)
# =========================================================================
WEIGHTS = {
    "ai_skills":      0.30,   # Technical depth: embeddings, retrieval, LLMs
    "career_quality": 0.25,   # AI production evidence vs consulting/keyword-stuffing
    "experience_fit": 0.20,   # 5–9yr range; AI-specific career time
    "availability":   0.15,   # Behavioral signals — actually reachable?
    "platform":       0.10,   # GitHub, location, logistics
}

# =========================================================================
# CORE SKILLS  (relevance weight 1–10 for this JD)
# "We care about production experience, not which specific tool."  — JD
# Keys are lowercase substrings matched against the candidate's skill name.
# Use multi-word keys (>= 3 chars) to avoid false substring matches.
# =========================================================================
CORE_SKILLS = {
    # ── Embeddings & Vector Retrieval  (MUST HAVE per JD) ──────────────
    "sentence-transformers":  10,
    "sentence transformer":   10,
    "faiss":                   9,
    "pinecone":                9,
    "weaviate":                9,
    "qdrant":                  9,
    "milvus":                  9,
    "elasticsearch":           8,
    "opensearch":              8,
    "chromadb":                8,
    "vector search":           9,
    "vector database":         9,
    "vector db":               9,
    "hybrid search":           9,
    "dense retrieval":         9,
    "semantic search":         8,
    "embeddings":              8,
    "embedding":               8,
    "text embedding":          8,
    "sentence embedding":      8,
    "bm25":                    8,
    "approximate nearest":     7,
    "nearest neighbor":        7,

    # ── Ranking & Information Retrieval  (MUST HAVE per JD) ────────────
    "re-ranking":              8,
    "reranking":               8,
    "learning to rank":        9,
    "information retrieval":   9,
    "recommendation system":   8,
    "recommender system":      8,
    "recommender":             7,
    "search system":           8,
    "search relevance":        8,
    "retrieval system":        8,
    "ranking system":          8,
    "ndcg":                    9,
    "mrr metric":              8,
    "mean reciprocal":         8,
    "mean average precision":  8,
    "a/b testing":             7,
    "ab testing":              7,
    "online experimentation":  7,
    "eval framework":          7,
    "offline evaluation":      7,

    # ── NLP & LLMs ─────────────────────────────────────────────────────
    "natural language processing": 8,
    "nlp":                     8,
    "large language model":    8,
    "llm":                     8,
    "retrieval augmented":     8,
    "rag pipeline":            8,
    "fine-tuning":             7,
    "fine tuning":             7,
    "finetuning":              7,
    "lora":                    8,
    "qlora":                   8,
    "peft":                    7,
    "transformers":            7,
    "huggingface":             7,
    "hugging face":            7,
    "bert":                    7,
    "langchain":               5,
    "llama":                   6,
    "openai api":              5,
    "text classification":     6,
    "named entity recognition":6,
    "question answering":      6,

    # ── Core ML / Deep Learning ─────────────────────────────────────────
    "pytorch":                 7,
    "tensorflow":              6,
    "machine learning":        6,
    "deep learning":           6,
    "neural network":          5,
    "xgboost":                 6,
    "lightgbm":                5,
    "scikit-learn":            5,
    "feature engineering":     5,
    "model serving":           6,
    "model deployment":        6,
    "mlops":                   6,
    "mlflow":                  5,
    "kubeflow":                5,
    "weights & biases":        5,
    "wandb":                   5,

    # ── Languages & Infrastructure ──────────────────────────────────────
    "python":                  7,
    "fastapi":                 5,
    "docker":                  4,
    "kubernetes":              4,
    "aws sagemaker":           5,
    "gcp vertex":              5,
    "azure ml":                5,
    "kafka":                   3,
    "spark":                   4,
    "databricks":              4,

    # ── Open Source / Research signal ──────────────────────────────────
    "open source":             5,
    "distributed systems":     4,
    "systems design":          4,
}

# =========================================================================
# CONSULTING / SERVICES FIRMS
# JD: "All-consulting career = bad fit. One product stint saves them."
# =========================================================================
CONSULTING_FIRMS = {
    "tcs", "tata consultancy", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "tech mahindra", "hcl technologies",
    "mphasis", "hexaware", "mindtree", "l&t infotech", "ltimindtree",
    "dxc technology", "dxc", "unisys", "ntt data", "ibm consulting",
    "kpit", "cyient", "mastech", "niit technologies", "zensar",
    "persistent systems", "mphasist",
}

# =========================================================================
# CAREER DESCRIPTION KEYWORDS
# =========================================================================

# Evidence of REAL AI/ML production work (positive signal)
CAREER_POSITIVE_KEYWORDS = [
    # Production deployment
    "production", "deployed", "shipped", "real users", "at scale",
    "live system", "serving", "prod environment",
    # Search / retrieval systems
    "retrieval", "ranking", "recommendation", "search engine",
    "vector search", "semantic search", "hybrid search",
    "embedding pipeline", "index", "inverted index",
    # ML/AI systems
    "nlp", "machine learning", "deep learning", "neural",
    "language model", "transformer", "fine-tun",
    "model training", "model evaluation", "feature engineering",
    # LLM / modern AI
    "llm", "rag", "retrieval augmented", "prompt engineering",
    "langchain", "openai", "anthropic",
    # Evaluation & quality
    "a/b test", "offline eval", "online eval", "ndcg", "mrr",
    "search quality", "relevance", "recall", "precision",
    "latency", "throughput", "inference optimization",
    # Product signals
    "startup", "saas", "product company", "founding",
    # Quality signals
    "open source", "github", "arxiv", "published", "conference",
    "mentored engineers", "architected", "led team",
]

# Signals of clearly NON-AI work — catches keyword stuffers
CAREER_NEGATIVE_KEYWORDS = [
    "marketing campaign", "seo strategy", "content creation", "social media",
    "mechanical design", "cad ", "solidworks", "creo", "ansys",
    "civil engineering", "structural design", "construction site",
    "accounting", "financial reporting", "tax filing", "gst filing",
    "customer support agent", "tier-1 ticket", "tier-2 ticket",
    "call center", "bpo operations",
    "graphic design", "adobe illustrator", "brand identity",
    "cold calling", "lead generation", "sales target",
]

# =========================================================================
# TITLE TAXONOMY
# =========================================================================

# AI-relevant job titles  (positive signal in career quality + experience)
# Deliberately narrow: generic "engineer" titles excluded because a
# candidate with a generic title but real AI work gets credit via
# description-content scoring, which is more reliable.
AI_TITLES = {
    "ml engineer", "machine learning engineer", "ai engineer",
    "data scientist", "research scientist", "applied scientist",
    "nlp engineer", "deep learning engineer", "research engineer",
    "applied ml", "applied ai", "ai researcher",
    "search engineer", "mlops engineer",
    "recommendation systems engineer", "ai specialist",
    "ai research engineer", "data engineer",
    # NOTE: deliberately excludes "computer vision engineer" -- the JD
    # explicitly disqualifies CV/speech/robotics specialists without
    # significant NLP/IR exposure. A genuine CV->NLP crossover candidate
    # still earns AI-years credit via career description content, not title.
}

# Clearly non-AI titles (all-non-AI-title career triggers penalty)
NON_AI_TITLES = {
    "marketing manager", "hr manager", "human resources",
    "operations manager", "sales executive", "sales manager",
    "business analyst", "project manager", "program manager",
    "accountant", "graphic designer", "content writer",
    "customer support", "civil engineer", "mechanical engineer",
    "electrical engineer", "structural engineer",
}

# =========================================================================
# LOCATION PREFERENCES
# JD: "Pune/Noida preferred. Hyderabad, Mumbai, Delhi NCR, Bangalore OK."
# =========================================================================
PREFERRED_LOCATIONS = {
    "pune", "noida", "gurgaon", "gurugram", "new delhi", "delhi ncr",
    "delhi", "ncr", "greater noida",
}
ACCEPTABLE_LOCATIONS = {
    "hyderabad", "mumbai", "bangalore", "bengaluru", "chennai",
    "kolkata", "ahmedabad", "india",
}

# =========================================================================
# EXPERIENCE THRESHOLDS
# =========================================================================
EXP_IDEAL_MIN    = 5.0   # JD explicit range
EXP_IDEAL_MAX    = 9.0
EXP_SWEET_MIN    = 6.0   # JD "imagined candidate": 6–8 yrs
EXP_SWEET_MAX    = 8.0
EXP_MAX_PENALTY  = 15.0  # Below this yrs, hard cap on experience score

# =========================================================================
# HONEYPOT DETECTION THRESHOLDS
# Spec §7: ~80 candidates have "subtly impossible profiles" in 100K dataset.
# Verified against real data — these thresholds flag ~99 candidates (0.10%).
# =========================================================================

# Two-tier skill-duration check:
#   EXPERT claims: if skill duration > career + 24mo, implausible fabrication
#   Any proficiency: if skill duration > career + 60mo, physically impossible
SKILL_DURATION_SLACK_MONTHS_EXPERT = 24
SKILL_DURATION_SLACK_MONTHS        = 60

# "Expert" in N skills with 0 months used = fabrication signal
EXPERT_ZERO_DURATION_LIMIT = 3

# Single job tenure beyond career total by >12mo = impossible
MAX_PLAUSIBLE_TENURE_MONTHS = 360
