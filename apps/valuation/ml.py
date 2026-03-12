from decimal import Decimal, ROUND_HALF_UP


MODEL_VERSION = "baseline_v1_proxy"


def _round_metric(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _round_money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clamp(value, lower, upper):
    return max(Decimal(lower), min(Decimal(value), Decimal(upper)))


def _signal(label, impact, explanation):
    tone = "positive" if Decimal(impact) >= 0 else "negative"
    return {
        "label": label,
        "impact": _round_metric(impact),
        "tone": tone,
        "explanation": explanation,
    }


def build_ml_baseline_forecast(*, portfolio, feature_vector, expected_recovery_rate, recommended_bid_pct, projected_roi, confidence_score):
    contactability_share = Decimal(feature_vector["contactability_share"])
    low_risk_share = Decimal(feature_vector["low_risk_share"])
    high_risk_share = Decimal(feature_vector["high_risk_share"])
    paying_share = Decimal(feature_vector["paying_share"])
    ptp_share = Decimal(feature_vector["ptp_share"])
    collection_efficiency = Decimal(feature_vector["collection_efficiency_pct"])
    avg_dpd = Decimal(feature_vector["avg_days_past_due"])
    purchase_price_pct = Decimal(feature_vector["purchase_price_pct_of_face"])

    signals = [
        _signal("Contactability coverage", (contactability_share - Decimal(50)) * Decimal("0.08"), "Higher debtor reach pushes the baseline recovery estimate upward."),
        _signal("Low-risk concentration", (low_risk_share - Decimal(30)) * Decimal("0.06"), "A healthier low-risk share improves the modeled collection potential."),
        _signal("High-risk concentration", -(high_risk_share - Decimal(20)) * Decimal("0.07"), "Heavy high-risk concentration drags down baseline recovery and pricing appetite."),
        _signal("Paying share", paying_share * Decimal("0.09"), "Active paying debtors strengthen near-term recovery confidence."),
        _signal("Promise-to-pay share", ptp_share * Decimal("0.05"), "PTP behavior provides a modest positive recovery signal."),
        _signal("Collection efficiency", (collection_efficiency - Decimal(5)) * Decimal("0.04"), "Observed collections give the baseline model a realized performance anchor."),
        _signal("Aging pressure", -max(Decimal(0), avg_dpd - Decimal(90)) * Decimal("0.03"), "Older delinquency pushes the baseline model toward a more conservative recovery path."),
        _signal("Purchase discipline", -purchase_price_pct * Decimal("0.04"), "Higher acquisition leverage reduces bid tolerance in the baseline model."),
    ]

    raw_adjustment = sum((signal["impact"] for signal in signals), Decimal("0.00"))
    baseline_recovery = _clamp(Decimal(expected_recovery_rate) + raw_adjustment * Decimal("0.10"), Decimal("5.00"), Decimal("78.00"))

    baseline_bid_pct = _clamp(
        (baseline_recovery * Decimal("0.34"))
        + (paying_share * Decimal("0.05"))
        + (ptp_share * Decimal("0.02"))
        - (high_risk_share * Decimal("0.04")),
        Decimal("3.00"),
        Decimal("24.00"),
    )

    baseline_collections = _round_money(Decimal(portfolio.face_value) * (baseline_recovery / Decimal("100")))
    baseline_bid_amount = _round_money(Decimal(portfolio.face_value) * (baseline_bid_pct / Decimal("100")))

    baseline_roi = Decimal("0.00")
    if baseline_bid_amount > 0:
        baseline_roi = _round_metric(((baseline_collections - baseline_bid_amount) / baseline_bid_amount) * Decimal("100"))

    baseline_confidence = _clamp(
        Decimal(confidence_score)
        + (contactability_share * Decimal("0.05"))
        + (collection_efficiency * Decimal("0.04"))
        - (high_risk_share * Decimal("0.05")),
        Decimal("20.00"),
        Decimal("96.00"),
    )

    delta_recovery = _round_metric(baseline_recovery - Decimal(expected_recovery_rate))
    delta_bid = _round_metric(baseline_bid_pct - Decimal(recommended_bid_pct))
    delta_roi = _round_metric(baseline_roi - Decimal(projected_roi))

    alignment = "Aligned"
    if delta_recovery >= Decimal("2.50"):
        alignment = "More optimistic than rule engine"
    elif delta_recovery <= Decimal("-2.50"):
        alignment = "More conservative than rule engine"

    ranked_signals = sorted(signals, key=lambda item: abs(item["impact"]), reverse=True)[:4]

    return {
        "model_name": "Baseline Recovery Model",
        "model_version": MODEL_VERSION,
        "predicted_recovery_rate": _round_metric(baseline_recovery),
        "predicted_collections": baseline_collections,
        "predicted_bid_pct": _round_metric(baseline_bid_pct),
        "predicted_bid_amount": baseline_bid_amount,
        "predicted_roi": baseline_roi,
        "confidence": _round_metric(baseline_confidence),
        "alignment": alignment,
        "delta_recovery": delta_recovery,
        "delta_bid": delta_bid,
        "delta_roi": delta_roi,
        "top_signals": ranked_signals,
    }
