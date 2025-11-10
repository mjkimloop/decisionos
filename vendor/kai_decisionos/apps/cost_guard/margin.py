from __future__ import annotations


def compute_margin(billed_total: float, model_cost: float, infra_cost: float) -> dict:
    margin = billed_total - (model_cost + infra_cost)
    pct = 0.0 if billed_total == 0 else round(margin / billed_total * 100, 2)
    return {"margin": round(margin, 4), "margin_pct": pct}

