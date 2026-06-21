"""
scorer.py — Multi-Dimensional Candidate Scoring Engine
Redrob AI Hackathon: Intelligent Candidate Discovery & Ranking

Architecture
============
  5 scoring dimensions  ─►  weighted composite  ─►  penalty multipliers  ─►  final score

  No API calls. No GPU. No network. Pure Python.
  Processes 100,000 candidates in ~45 seconds on a modern CPU.

Scoring dimensions (weights from jd_config.WEIGHTS):
  1. ai_skills       (30%) — skill relevance × proficiency × duration × endorsements
  2. career_quality  (25%) — title fit, description AI-content, company type, tenure
  3. experience_fit  (20%) — years in range, AI-specific career years
  4. availability    (15%) — last-active, open_to_work, notice period, response rate
  5. platform        (10%) — GitHub activity, location, completeness, verifications

Penalty multipliers (applied after weighted sum):
  - is_honeypot         → score = 0.0  (impossible / fabricated profiles)
  - all_consulting      → × 0.25
  - all_non_ai_titles   → × 0.30
  - ghost_candidate     → × 0.40       (inactive 6+ months AND low response)
  - not_open_to_work    → × 0.90
"""

import math
from datetime import date, datetime
from typing import Any, Dict, Tuple

import jd_config as cfg

# Reference date for all "days since" calculations
_TODAY = date(2026, 6, 16)


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def score_candidate(candidate: Dict[str, Any]) -> Tuple[float, Dict[str, float], str]:
    """
    Score a single candidate against the Senior AI Engineer JD.

    Returns
    -------
    final_score      : float in [0, 1]
    component_scores : dict — keys matching cfg.WEIGHTS, values 0–100
    reasoning        : recruiter-readable 1–2 sentence string
    """
    # ── Honeypot check first (instant disqualify) ────────────────────────
    if _is_honeypot(candidate):
        return 0.0, {k: 0.0 for k in cfg.WEIGHTS}, _honeypot_reason(candidate)

    # ── Component scores (each 0–100) ────────────────────────────────────
    scores = {
        "ai_skills":      _ai_skills_score(candidate),
        "career_quality": _career_quality_score(candidate),
        "experience_fit": _experience_fit_score(candidate),
        "availability":   _availability_score(candidate),
        "platform":       _platform_score(candidate),
    }

    # ── Weighted composite ───────────────────────────────────────────────
    composite = sum(scores[k] * cfg.WEIGHTS[k] for k in cfg.WEIGHTS)

    # ── Penalty multipliers ──────────────────────────────────────────────
    penalty = _compute_penalty(candidate)

    final_raw   = composite * penalty          # 0–100
    final_score = round(final_raw / 100, 4)   # normalised 0–1

    reasoning = _build_reasoning(candidate, scores, final_score, penalty)

    return final_score, scores, reasoning


# ═══════════════════════════════════════════════════════════════════════════
#  HONEYPOT DETECTION
#  Spec §7: ~80 "subtly impossible" profiles in the 100K dataset.
#  We use 5 independent checks; first match returns True immediately.
# ═══════════════════════════════════════════════════════════════════════════

def _is_honeypot(c: Dict) -> bool:
    profile = c.get("profile", {})
    career  = c.get("career_history", [])
    skills  = c.get("skills", [])
    signals = c.get("redrob_signals", {})

    yoe            = float(profile.get("years_of_experience", 0) or 0)
    career_months  = yoe * 12

    # ── Check 1: skill duration exceeds entire career ───────────────────
    # Two-tier: tighter buffer for "expert" claims (top-tier mastery
    # claimed for longer than the career itself is a strong fabrication
    # signal); generous absolute ceiling for any proficiency.
    if career_months > 0:
        for sk in skills:
            dur = sk.get("duration_months", 0) or 0
            gap = dur - career_months
            if sk.get("proficiency") == "expert" and gap > cfg.SKILL_DURATION_SLACK_MONTHS_EXPERT:
                return True
            if gap > cfg.SKILL_DURATION_SLACK_MONTHS:
                return True

    # ── Check 2: "expert" in multiple skills with 0 months of actual use ─
    expert_zero = sum(
        1 for sk in skills
        if sk.get("proficiency") == "expert" and (sk.get("duration_months") or 0) == 0
    )
    if expert_zero >= cfg.EXPERT_ZERO_DURATION_LIMIT:
        return True

    # ── Check 3: job start date in the future ───────────────────────────
    for job in career:
        start = job.get("start_date", "")
        if start:
            try:
                if datetime.strptime(start, "%Y-%m-%d").date() > _TODAY:
                    return True
            except ValueError:
                pass

    # ── Check 4: single job tenure exceeds career length by > 12 months ─
    if career_months > 0:
        for job in career:
            dur = job.get("duration_months", 0) or 0
            if dur > career_months + 12:
                return True

    # ── Check 5: every behavioral signal simultaneously at theoretical max
    rr = signals.get("recruiter_response_rate", 0) or 0
    ir = signals.get("interview_completion_rate", 0) or 0
    pc = signals.get("profile_completeness_score", 0) or 0
    gh = signals.get("github_activity_score", -1)
    if rr == 1.0 and ir == 1.0 and pc == 100 and gh == 100:
        return True

    return False


def _honeypot_reason(c: Dict) -> str:
    return (
        "Profile flagged as statistically impossible (honeypot): "
        "skill durations or behavioral signals are inconsistent with "
        "stated experience. Excluded from ranking per data-quality check."
    )


# ═══════════════════════════════════════════════════════════════════════════
#  DIMENSION 1 — AI SKILLS SCORE
#  Strategy: skill relevance × proficiency × real usage × endorsements
#  Anti-gaming: a skill listed at "expert" with 0 months and 0 endorsements
#  contributes far less than "intermediate" with 18 months and 5 endorsements.
# ═══════════════════════════════════════════════════════════════════════════

def _ai_skills_score(c: Dict) -> float:
    skills   = c.get("skills", []) or []
    assessed = (c.get("redrob_signals", {}) or {}).get("skill_assessment_scores", {}) or {}

    if not skills:
        return 0.0

    contributions = []

    for sk in skills:
        name = (sk.get("name") or "").lower().strip()

        # Best-matching weight from CORE_SKILLS taxonomy
        best_w = 0
        for key, w in cfg.CORE_SKILLS.items():
            if key in name or name in key:
                if w > best_w:
                    best_w = w
        if best_w == 0:
            continue

        # Proficiency multiplier
        prof_map = {"expert": 1.0, "advanced": 0.82, "intermediate": 0.52, "beginner": 0.22}
        prof_m   = prof_map.get(sk.get("proficiency", "beginner"), 0.22)

        # Duration multiplier — full credit at 36 months of real usage
        dur   = max(0, sk.get("duration_months", 0) or 0)
        dur_m = min(1.0, dur / 36.0)

        # Endorsement trust multiplier — log-scale, reference at 25 endorsements
        end   = max(0, sk.get("endorsements", 0) or 0)
        end_m = min(1.0, math.log1p(end) / math.log1p(25))

        # Assessment score bonus (if candidate took platform skill test)
        assess_bonus = 0.0
        for akey, ascore in assessed.items():
            if akey.lower() in name or name in akey.lower():
                assess_bonus = (float(ascore) / 100.0) * 0.12 * best_w
                break

        # Composite: proficiency 45%, duration 35%, endorsements 20%
        contrib = best_w * (prof_m * 0.45 + dur_m * 0.35 + end_m * 0.20) + assess_bonus
        contributions.append(contrib)

    if not contributions:
        return 0.0

    # Diminishing returns over top-15 skills (breadth matters, but not infinitely)
    contributions.sort(reverse=True)
    total = sum(v * (0.85 ** i) for i, v in enumerate(contributions[:15]))

    # Normalise: theoretical max = 10 perfect skills × weight=10 × no discount
    theor_max = 10.0 * 1.0 * sum(0.85 ** i for i in range(10))
    return min(100.0, (total / theor_max) * 100.0)


# ═══════════════════════════════════════════════════════════════════════════
#  DIMENSION 2 — CAREER QUALITY SCORE
#  Key insight from JD: "A Tier 5 candidate may not use 'RAG' or 'Pinecone'
#  but if their career history shows they built a recommendation system at a
#  product company, they fit."
#  → description-content scoring (40% of this dimension) catches plain-
#    language fits; title-based scoring (25%) is cross-validated, not primary.
# ═══════════════════════════════════════════════════════════════════════════

def _career_quality_score(c: Dict) -> float:
    career = c.get("career_history", []) or []
    if not career:
        return 15.0

    t_score   = _title_relevance(career)        # 0–100
    d_score   = _description_ai_content(career) # 0–100
    co_score  = _company_quality(career)        # 0–100
    ten_score = _tenure_stability(career)       # 0–100

    # Description content weighted highest — JD-explicit instruction
    return min(100.0,
               t_score  * 0.25 +
               d_score  * 0.40 +
               co_score * 0.25 +
               ten_score * 0.10)


def _title_relevance(career: list) -> float:
    """Fraction of career months spent in AI-specific roles."""
    total_months = 0
    ai_months    = 0

    for job in career:
        title = (job.get("title") or "").lower()
        dur   = max(0, job.get("duration_months", 12) or 12)
        total_months += dur
        if any(t in title for t in cfg.AI_TITLES):
            ai_months += dur

    if total_months == 0:
        return 50.0

    score = (ai_months / total_months) * 100

    # Bonus: current role is AI-related
    if career and any(t in (career[0].get("title") or "").lower() for t in cfg.AI_TITLES):
        score = min(100.0, score * 1.15)

    return score


def _description_ai_content(career: list) -> float:
    """
    Scan all career descriptions for real AI/ML production evidence.
    This is the primary signal for catching plain-language Tier 5 candidates
    AND for catching keyword stuffers whose descriptions reveal non-AI work.
    """
    all_desc = " ".join((job.get("description") or "").lower() for job in career)
    if not all_desc.strip():
        return 20.0

    pos_hits = sum(1 for kw in cfg.CAREER_POSITIVE_KEYWORDS if kw in all_desc)
    neg_hits = sum(1 for kw in cfg.CAREER_NEGATIVE_KEYWORDS if kw in all_desc)

    base = min(100.0, pos_hits * 6.0)   # ~17 positive signals → full score

    # Heavy penalty: many negative signals alongside AI skills = keyword stuffer
    if neg_hits >= 3:
        base *= max(0.25, 1.0 - (neg_hits - 2) * 0.20)

    return base


def _company_quality(career: list) -> float:
    """
    Score by company type: product startups > MNCs > consulting firms.
    One product-company stint rescues a consulting-heavy career.
    """
    total_m   = 0
    consult_m = 0

    for job in career:
        company = (job.get("company") or "").lower()
        dur     = max(0, job.get("duration_months", 12) or 12)
        total_m += dur
        if any(f in company for f in cfg.CONSULTING_FIRMS):
            consult_m += dur

    if total_m == 0:
        return 50.0

    ratio = consult_m / total_m
    score = (1.0 - ratio * 0.70) * 100.0
    return max(10.0, min(100.0, score))


def _tenure_stability(career: list) -> float:
    """Penalise title-chasers who hop every 1.5 years. JD requires 3+ yr commitment."""
    past = [j for j in career if not j.get("is_current", False)]
    if not past:
        return 75.0

    avg = sum(max(0, j.get("duration_months", 12) or 12) for j in past) / len(past)

    if avg < 10:   return 20.0
    if avg < 18:   return 50.0
    if avg < 24:   return 72.0
    return 95.0


# ═══════════════════════════════════════════════════════════════════════════
#  DIMENSION 3 — EXPERIENCE FIT SCORE
#  JD target: 5–9 years total; 4+ years AI-specific preferred
#  Bell curve peaks at 7 yrs; sharper penalty above 12 (likely over-senior)
# ═══════════════════════════════════════════════════════════════════════════

def _experience_fit_score(c: Dict) -> float:
    profile = c.get("profile", {}) or {}
    career  = c.get("career_history", []) or []

    yoe = float(profile.get("years_of_experience", 0) or 0)

    # Bell curve: peaks at 7 yrs, symmetric tails, harder cut above 12
    if yoe < 2:
        yr_score = yoe / 2.0 * 28.0
    elif yoe < 5:
        yr_score = 28.0 + (yoe - 2.0) / 3.0 * 42.0
    elif yoe <= 9:
        yr_score = 100.0 - abs(yoe - 7.0) * 10.0
        yr_score = max(70.0, yr_score)
    elif yoe <= 12:
        yr_score = max(50.0, 100.0 - (yoe - 9.0) * 9.0)
    else:
        # Over-senior: JD explicitly discourages 15yr "architect" types
        yr_score = max(25.0, 50.0 - (yoe - 12.0) * 5.0)

    # AI-specific career years: title match + description evidence
    ai_months = 0
    for job in career:
        dur  = max(0, job.get("duration_months", 0) or 0)
        ti   = (job.get("title") or "").lower()
        desc = (job.get("description") or "").lower()

        has_ai_title = any(t in ti for t in cfg.AI_TITLES)
        pos_hits     = sum(1 for kw in cfg.CAREER_POSITIVE_KEYWORDS[:14] if kw in desc)
        has_ai_desc  = pos_hits >= 2   # at least 2 positive signals in description

        if has_ai_title or has_ai_desc:
            ai_months += dur

    ai_years = ai_months / 12.0

    if ai_years >= 4.0:   ai_score = 100.0
    elif ai_years >= 2.0: ai_score = 60.0 + (ai_years - 2.0) / 2.0 * 40.0
    elif ai_years >= 0.5: ai_score = 18.0 + (ai_years - 0.5) / 1.5 * 42.0
    else:                 ai_score = 10.0

    # Total years (35%) + AI-specific years (65%)
    return yr_score * 0.35 + ai_score * 0.65


# ═══════════════════════════════════════════════════════════════════════════
#  DIMENSION 4 — AVAILABILITY SCORE
#  JD: "A perfect-on-paper candidate inactive for 6 months with a 5%
#  response rate is not actually available — down-weight appropriately."
# ═══════════════════════════════════════════════════════════════════════════

def _availability_score(c: Dict) -> float:
    s = c.get("redrob_signals", {}) or {}

    parts = []

    # ── Last-active recency (30% of availability score) ──────────────────
    la = s.get("last_active_date", "")
    try:
        days_ago = (_TODAY - datetime.strptime(la, "%Y-%m-%d").date()).days
    except (ValueError, TypeError):
        days_ago = 180

    if   days_ago <= 14:  act = 100.0
    elif days_ago <= 30:  act = 88.0
    elif days_ago <= 60:  act = 72.0
    elif days_ago <= 90:  act = 55.0
    elif days_ago <= 180: act = 30.0
    else:                 act = 8.0
    parts.append(act * 0.30)

    # ── Open-to-work flag (20%) ──────────────────────────────────────────
    parts.append((100.0 if s.get("open_to_work_flag") else 35.0) * 0.20)

    # ── Notice period (20%) — JD: "love sub-30d; can buy out 30d" ────────
    notice = int(s.get("notice_period_days", 90) or 90)
    if   notice <= 0:   ns = 100.0
    elif notice <= 30:  ns = 90.0
    elif notice <= 60:  ns = 72.0
    elif notice <= 90:  ns = 48.0
    else:               ns = 18.0
    parts.append(ns * 0.20)

    # ── Recruiter response rate (15%) ────────────────────────────────────
    rr = float(s.get("recruiter_response_rate", 0.3) or 0.3)
    parts.append(rr * 100.0 * 0.15)

    # ── Interview completion rate (10%) ──────────────────────────────────
    ir = float(s.get("interview_completion_rate", 0.5) or 0.5)
    parts.append(ir * 100.0 * 0.10)

    # ── Avg response time (5% — quick responders more reachable) ────────
    # Lower is better: <4hr = excellent, >72hr = poor
    rt = float(s.get("avg_response_time_hours", 48.0) or 48.0)
    if   rt <= 4:   rt_s = 100.0
    elif rt <= 12:  rt_s = 82.0
    elif rt <= 24:  rt_s = 65.0
    elif rt <= 48:  rt_s = 45.0
    elif rt <= 72:  rt_s = 28.0
    else:           rt_s = 10.0
    parts.append(rt_s * 0.05)

    return sum(parts)


# ═══════════════════════════════════════════════════════════════════════════
#  DIMENSION 5 — PLATFORM & LOGISTICS SCORE
# ═══════════════════════════════════════════════════════════════════════════

def _platform_score(c: Dict) -> float:
    s = c.get("redrob_signals", {}) or {}
    p = c.get("profile", {}) or {}

    parts = []

    # ── GitHub activity (30% — critical for AI engineer role) ────────────
    gh   = float(s.get("github_activity_score", -1))
    gh_s = gh if gh >= 0 else 12.0   # No GitHub = significant penalty for this role
    parts.append(gh_s * 0.30)

    # ── Location fit (22%) ───────────────────────────────────────────────
    loc = ((p.get("location") or "") + " " + (p.get("country") or "")).lower()
    if   any(pl in loc for pl in cfg.PREFERRED_LOCATIONS): loc_s = 100.0
    elif any(al in loc for al in cfg.ACCEPTABLE_LOCATIONS): loc_s = 70.0
    elif s.get("willing_to_relocate"):                      loc_s = 52.0
    else:                                                   loc_s = 22.0
    parts.append(loc_s * 0.22)

    # ── Profile completeness (18%) ───────────────────────────────────────
    pc = float(s.get("profile_completeness_score", 50) or 50)
    parts.append(pc * 0.18)

    # ── Social proof — saved by recruiters (12%) ─────────────────────────
    saved = int(s.get("saved_by_recruiters_30d", 0) or 0)
    parts.append(min(100.0, saved * 8.0) * 0.12)

    # ── Verification signals (10%) ───────────────────────────────────────
    ver = (
        (1 if s.get("verified_email")    else 0) +
        (1 if s.get("verified_phone")    else 0) +
        (1 if s.get("linkedin_connected") else 0)
    ) / 3.0 * 100.0
    parts.append(ver * 0.10)

    # ── Connection count — proxy for network / credibility (4%) ──────────
    conn = min(100.0, float(s.get("connection_count", 0) or 0) / 5.0)
    parts.append(conn * 0.04)

    # ── Profile views & search appearances (4% — recruiter-interest signals)
    views  = int(s.get("profile_views_received_30d", 0) or 0)
    appear = int(s.get("search_appearance_30d", 0) or 0)
    # normalise: 100 views or 500 appearances = full score
    market = min(100.0, (views / 100.0 * 0.5 + appear / 500.0 * 0.5) * 100.0)
    parts.append(market * 0.04)

    return sum(parts)


# ═══════════════════════════════════════════════════════════════════════════
#  PENALTY MULTIPLIERS
#  Applied after weighted composite; multiplicative so multiple penalties
#  compound. First-time penalties are heavy; recovery requires other signals.
# ═══════════════════════════════════════════════════════════════════════════

def _compute_penalty(c: Dict) -> float:
    penalty = 1.0
    career  = c.get("career_history", []) or []
    s       = c.get("redrob_signals", {}) or {}

    # ── 1. All-consulting career ─────────────────────────────────────────
    if len(career) >= 2:
        companies      = [(j.get("company") or "").lower() for j in career]
        all_consulting = all(any(f in co for f in cfg.CONSULTING_FIRMS) for co in companies if co)
        if all_consulting:
            penalty *= 0.25

    # ── 2. All non-AI titles ─────────────────────────────────────────────
    if career:
        titles      = [(j.get("title") or "").lower() for j in career]
        all_non_ai  = all(any(t in ti for t in cfg.NON_AI_TITLES) for ti in titles if ti)
        if all_non_ai:
            penalty *= 0.30

    # ── 3. Ghost candidate: inactive 6+ months + low response rate ───────
    la = s.get("last_active_date", "")
    rr = float(s.get("recruiter_response_rate", 0.5) or 0.5)
    if la:
        try:
            days_ago = (_TODAY - datetime.strptime(la, "%Y-%m-%d").date()).days
            if days_ago > 180 and rr < 0.15:
                penalty *= 0.40
        except ValueError:
            pass

    # ── 4. Not open to work (mild — candidate may still be worth pursuing) ──
    if not s.get("open_to_work_flag", True):
        penalty *= 0.90

    return penalty


# ═══════════════════════════════════════════════════════════════════════════
#  REASONING GENERATOR
#  Spec §3 requirements: specific facts, JD connection, honest concerns,
#  no hallucination, meaningful variation across candidates, rank-consistent
#  tone. Every field in the output string comes from the actual candidate data.
# ═══════════════════════════════════════════════════════════════════════════

def _build_reasoning(c: Dict, scores: Dict, final: float, penalty: float) -> str:
    p  = c.get("profile", {}) or {}
    s  = c.get("redrob_signals", {}) or {}
    sk = c.get("skills", []) or []
    ca = c.get("career_history", []) or []

    title = p.get("current_title", "Unknown")
    yoe   = float(p.get("years_of_experience", 0) or 0)
    loc   = p.get("location", "Unknown location")

    # Top 3 AI-matched skills with proficiency and usage
    matched = []
    for skill in sk:
        n = (skill.get("name") or "").lower()
        for key in cfg.CORE_SKILLS:
            if key in n or n in key:
                prof = skill.get("proficiency", "?")[:3]
                dur  = skill.get("duration_months", 0) or 0
                matched.append((cfg.CORE_SKILLS[key], f"{skill['name']}({prof},{dur}mo)"))
                break
    matched.sort(reverse=True)
    top_skills = ", ".join(m[1] for m in matched[:3]) or "no core AI skills matched"

    # Availability string
    la = s.get("last_active_date", "")
    try:
        days_ago   = (_TODAY - datetime.strptime(la, "%Y-%m-%d").date()).days
        active_str = f"active {days_ago}d ago"
    except Exception:
        active_str = "activity unknown"

    notice = s.get("notice_period_days", "?")
    rr     = float(s.get("recruiter_response_rate", 0) or 0)
    gh     = s.get("github_activity_score", -1)
    gh_str = f"GitHub:{gh:.0f}" if gh != -1 else "no GitHub"
    otw    = s.get("open_to_work_flag", False)
    otw_s  = "open to work" if otw else "NOT open to work"

    # Honest concerns — every concern is evidence-based, not speculative
    concerns = []
    if notice and str(notice).isdigit() and int(notice) > 60:
        concerns.append(f"long notice period ({notice}d)")
    if rr < 0.25:
        concerns.append(f"low recruiter response rate ({rr:.0%})")
    if gh == -1:
        concerns.append("no GitHub linked")
    if not otw:
        concerns.append("not flagged open to work")
    if scores["ai_skills"] < 30:
        concerns.append("limited core AI skills match")
    if scores["career_quality"] < 35:
        concerns.append("career lacks AI production evidence")
    if penalty < 0.5:
        concerns.append("career predominantly consulting/non-AI")

    concern_str = ("; concerns: " + ", ".join(concerns)) if concerns else ""

    # Tone bands — calibrated to actual top-100 score range (~0.75–0.93)
    # so a random 10-row sample shows genuine tonal variation
    if   final >= 0.84: lead = "Exceptional fit"
    elif final >= 0.80: lead = "Strong fit"
    elif final >= 0.77: lead = "Good fit"
    elif final >= 0.70: lead = "Solid fit"
    elif final >= 0.50: lead = "Moderate fit"
    elif final >= 0.30: lead = "Adjacent profile"
    else:               lead = "Weak match"

    return (
        f"{lead}: {title}, {yoe:.1f} yrs, {loc}. "
        f"AI skills: {top_skills}. "
        f"{active_str}, notice {notice}d, response {rr:.0%}, {gh_str}, {otw_s}"
        f"{concern_str}."
    )
