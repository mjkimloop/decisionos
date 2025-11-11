#!/usr/bin/env python3
"""
Posterior Drift Check Job
- 사전(prior) p_win과 사후(posterior) p_win 비교
- KL divergence + 절대 차이로 drift severity 분류
- var/alerts/posterior_drift.json 출력
"""
import os, json, argparse
from apps.ops.monitor.drift import classify_drift

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prior", default="configs/optimizer/prior_pwin.json")
    ap.add_argument("--posterior", default="var/ab_reports/posterior_pwin.json")
    ap.add_argument("--out", default="var/alerts/posterior_drift.json")
    ap.add_argument("--kl-warn", type=float, default=0.1)
    ap.add_argument("--kl-crit", type=float, default=0.5)
    ap.add_argument("--abs-warn", type=float, default=0.15)
    ap.add_argument("--abs-crit", type=float, default=0.30)
    args = ap.parse_args()

    # Load prior
    prior = json.load(open(args.prior, "r", encoding="utf-8"))
    prior_alpha = float(prior.get("alpha", 2.0))
    prior_beta = float(prior.get("beta", 2.0))

    # Load posterior
    posterior = json.load(open(args.posterior, "r", encoding="utf-8"))
    post_alpha = float(posterior.get("posterior", {}).get("alpha", 2.0))
    post_beta = float(posterior.get("posterior", {}).get("beta", 2.0))

    # Classify drift
    result = classify_drift(
        prior_alpha, prior_beta,
        post_alpha, post_beta,
        kl_warn=args.kl_warn, kl_crit=args.kl_crit,
        abs_warn=args.abs_warn, abs_crit=args.abs_crit
    )

    # Output
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] Drift check → {args.out}")
    print(f"  severity={result['severity']}, kl={result['kl']}, abs_diff={result['abs_diff']}")
    print(f"  reason_codes={result['reason_codes']}")

if __name__ == "__main__":
    main()
