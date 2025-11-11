#!/usr/bin/env python3
"""
Posterior Drift Monitor
- prior(사전) p_win ↔ posterior(관측) 괴리 측정
- KL divergence + absolute difference
- severity: info|warn|critical, reason_codes
"""
import math

def beta_kl(alpha1, beta1, alpha2, beta2, samples=1000):
    """
    Beta(α1,β1) || Beta(α2,β2) KL divergence (Monte Carlo 근사)
    """
    import random
    random.seed(42)
    kl = 0.0
    for _ in range(samples):
        # Beta(α1,β1) 샘플
        x = random.betavariate(alpha1, beta1)
        # log(p(x|α1,β1) / p(x|α2,β2))
        # 간단 근사: Beta PDF 비율 로그
        # 정확한 구현은 scipy.stats.beta.pdf 필요하지만, 순수 Python으로 근사
        # p(x|α,β) ∝ x^(α-1) * (1-x)^(β-1)
        if x <= 0 or x >= 1:
            continue
        log_p1 = (alpha1 - 1) * math.log(x) + (beta1 - 1) * math.log(1 - x)
        log_p2 = (alpha2 - 1) * math.log(x) + (beta2 - 1) * math.log(1 - x)
        kl += (log_p1 - log_p2) / samples
    return max(0.0, kl)

def classify_drift(prior_alpha, prior_beta, post_alpha, post_beta, kl_warn=0.1, kl_crit=0.5, abs_warn=0.15, abs_crit=0.30):
    """
    Drift 분류: info|warn|critical + reason_codes
    Args:
        prior_alpha, prior_beta: 사전분포
        post_alpha, post_beta: 사후분포
        kl_warn, kl_crit: KL divergence 임계
        abs_warn, abs_crit: 절대 차이 임계
    Returns:
        {severity, kl, abs_diff, reason_codes}
    """
    kl = beta_kl(post_alpha, post_beta, prior_alpha, prior_beta)

    # 평균 차이
    prior_mean = prior_alpha / (prior_alpha + prior_beta)
    post_mean = post_alpha / (post_alpha + post_beta)
    abs_diff = abs(post_mean - prior_mean)

    reason_codes = []
    severity = "info"

    # KL 판정
    if kl >= kl_crit:
        severity = "critical"
        reason_codes.append("kl_divergence_critical")
    elif kl >= kl_warn:
        if severity == "info":
            severity = "warn"
        reason_codes.append("kl_divergence_warn")

    # 절대 차이 판정
    if abs_diff >= abs_crit:
        severity = "critical"
        reason_codes.append("abs_diff_critical")
    elif abs_diff >= abs_warn:
        if severity == "info":
            severity = "warn"
        reason_codes.append("abs_diff_warn")

    if not reason_codes:
        reason_codes.append("no_drift")

    return {
        "severity": severity,
        "kl": round(kl, 4),
        "abs_diff": round(abs_diff, 4),
        "reason_codes": reason_codes
    }
