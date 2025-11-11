from __future__ import annotations
from typing import Dict, Any
import math

def wilson_ci(success: int, n: int, z: float = 1.644853626):  # ~90% CI
    if n == 0:
        return (0.0, 1.0)
    phat = success / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = (z * math.sqrt((phat * (1 - phat) / n) + (z * z / (4 * n * n)))) / denom
    return (max(0.0, center - half), min(1.0, center + half))

def update_pwin_beta(prior_alpha: float, prior_beta: float, wins: int, trials: int) -> Dict[str, Any]:
    post_a = prior_alpha + wins
    post_b = prior_beta + (trials - wins)
    mean = post_a / (post_a + post_b) if (post_a + post_b) > 0 else 0.5
    ci90 = wilson_ci(wins, trials, z=1.644853626)
    return {
        "prior": {"alpha": prior_alpha, "beta": prior_beta},
        "observed": {"wins": wins, "trials": trials},
        "posterior": {
            "alpha": post_a,
            "beta": post_b,
            "mean": mean,
            "ci90_low": ci90[0],
            "ci90_high": ci90[1]
        }
    }
