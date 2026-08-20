from app.data_loader import to_float, to_int


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _round(value: float) -> float:
    return round(value, 2)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def segment_weighted_profile(samples: dict[str, list[dict[str, str]]]) -> dict[str, float]:
    segments = samples["userSegments"]
    weighted_users = sum(
        to_int(row["user_count"]) * to_float(row["member_conversion_rate"])
        for row in segments
    )

    weighted_arpu = _safe_div(
        sum(
            to_int(row["user_count"])
            * to_float(row["member_conversion_rate"])
            * to_float(row["baseline_arpu"])
            for row in segments
        ),
        weighted_users,
    )
    weighted_margin_rate = _safe_div(
        sum(
            to_int(row["user_count"])
            * to_float(row["member_conversion_rate"])
            * to_float(row["gross_margin_rate"])
            for row in segments
        ),
        weighted_users,
    )
    weighted_lifecycle = _safe_div(
        sum(
            to_int(row["user_count"])
            * to_float(row["member_conversion_rate"])
            * to_float(row["expected_lifecycle_months"])
            for row in segments
        ),
        weighted_users,
    )

    return {
        "weightedArpu": weighted_arpu,
        "weightedMarginRate": weighted_margin_rate,
        "weightedLifecycleMonths": weighted_lifecycle,
        "weightedConvertedUsers": weighted_users,
    }


def calculate_advanced_metrics(
    plan: dict,
    samples: dict[str, list[dict[str, str]]],
) -> dict[str, float]:
    profile = segment_weighted_profile(samples)
    period_months = max(plan["periodMonths"], 1)
    target_members = max(plan["targetMembers"], 1)

    price_anchor = profile["weightedArpu"] * period_months
    price_sensitivity_index = _clamp(_safe_div(plan["price"], price_anchor), 0, 2)

    benefit_crowding_loss = (
        plan["benefitCost"] * plan["benefitUsageRate"] * (0.12 + price_sensitivity_index * 0.08)
    )
    renewal_quality_score = _clamp(
        plan["expectedRenewalRate"] * _safe_div(profile["weightedLifecycleMonths"], 12),
        0,
        1.5,
    )
    net_sequence_value = (
        plan["memberProfit"]
        - benefit_crowding_loss
        + renewal_quality_score * target_members * profile["weightedMarginRate"] * 10
    )
    value_contribution_index = _safe_div(
        net_sequence_value,
        plan["benefitCost"] + benefit_crowding_loss + 1,
    )

    row_confidence = _clamp(
        (
            len(samples["memberPlans"])
            + len(samples["userSegments"])
            + len(samples["orders"])
            + len(samples["benefitUsage"])
        )
        / 60,
        0.35,
        1,
    )
    formula_confidence_score = _clamp(
        row_confidence
        + min(plan["benefitUsageRate"], 1) * 0.08
        + min(plan["expectedRenewalRate"], 1) * 0.08
        - price_sensitivity_index * 0.06,
        0,
        1,
    )
    member_value_score = _clamp(
        48
        + plan["roi"] * 6
        + renewal_quality_score * 18
        + value_contribution_index * 2
        - price_sensitivity_index * 10,
        0,
        100,
    )

    return {
        "weightedArpu": _round(profile["weightedArpu"]),
        "weightedMarginRate": _round(profile["weightedMarginRate"]),
        "priceSensitivityIndex": _round(price_sensitivity_index),
        "benefitCrowdingLoss": _round(benefit_crowding_loss),
        "renewalQualityScore": _round(renewal_quality_score),
        "netSequenceValue": _round(net_sequence_value),
        "valueContributionIndex": _round(value_contribution_index),
        "formulaConfidenceScore": _round(formula_confidence_score),
        "memberValueScore": _round(member_value_score),
    }


def formula_cards() -> list[dict[str, str]]:
    return [
        {
            "title": "价格敏感度指数",
            "formula": "priceSensitivityIndex = 会员价格 / 加权用户 ARPU / 会员周期",
            "meaning": "衡量当前定价相对目标用户消费能力是否过高。",
        },
        {
            "title": "权益挤压损失",
            "formula": "benefitCrowdingLoss = 权益成本 * 核销率 * 动态挤压系数",
            "meaning": "量化高核销权益对会员净贡献的挤压。",
        },
        {
            "title": "续费质量分",
            "formula": "renewalQualityScore = 预估续费率 * 加权生命周期 / 12",
            "meaning": "把续费概率和生命周期合并为长期质量指标。",
        },
        {
            "title": "会员净序列价值",
            "formula": "netSequenceValue = 会员毛利 - 权益挤压损失 + 续费质量增益",
            "meaning": "回答一个会员方案进入长期序列后是否真的创造净价值。",
        },
    ]
