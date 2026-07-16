def calculate_priority_score(triage_level: int, waiting_time_minutes: float, suitability_score: float, downstream_impact_count: int) -> dict:
    """
    Computes a multi-criteria priority score.
    Returns the total score and a detailed breakdown of sub-metrics.
    """
    # 1. Triage Priority (1 = Critical, 5 = Non-Urgent)
    # Triage contribution scaled 0 - 100
    triage_score = (6 - triage_level) * 20.0  # level 1 = 100, level 5 = 20

    # 2. Waiting Time Priority
    # Scaled to 0 - 100, cap at 2 hours (120 minutes)
    wait_score = min((waiting_time_minutes / 120.0) * 100.0, 100.0)

    # 3. Downstream Cascade Impact Penalty
    # The more resources/cases are locked downstream, the higher the penalty (scaled 0 - 100)
    impact_penalty = min(downstream_impact_count * 20.0, 100.0)

    # Weights
    w_triage = 0.45
    w_wait = 0.20
    w_suitability = 0.25
    w_impact = 0.10

    total_score = (
        (w_triage * triage_score) +
        (w_wait * wait_score) +
        (w_suitability * suitability_score) -
        (w_impact * impact_penalty)
    )

    # Keep within [0, 100] limits
    total_score = max(0.0, min(total_score, 100.0))

    return {
        "total_score": round(total_score, 2),
        "triage_score": round(triage_score, 2),
        "wait_score": round(wait_score, 2),
        "suitability_score": round(suitability_score, 2),
        "impact_penalty": round(impact_penalty, 2),
        "weights": {
            "triage": w_triage,
            "wait": w_wait,
            "suitability": w_suitability,
            "impact": w_impact
        }
    }
