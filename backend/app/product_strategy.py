from app.data_loader import to_float, to_int


def build_product_strategy(
    calculation: dict,
    samples: dict[str, list[dict[str, str]]],
    trace: dict,
    validation_issues: list[dict],
) -> dict:
    ranked_plans = sorted(
        calculation["plans"],
        key=lambda plan: (
            plan["advancedMetrics"]["memberValueScore"],
            plan["roi"],
            plan["memberProfit"],
        ),
        reverse=True,
    )
    best_plan = ranked_plans[0] if ranked_plans else {}
    issue_count_by_plan = _issue_count_by_plan(validation_issues)

    return {
        "decisionSummary": _decision_summary(best_plan, issue_count_by_plan),
        "planDecisions": [
            _plan_decision(plan, issue_count_by_plan.get(plan["planId"], 0))
            for plan in ranked_plans
        ],
        "segmentOpportunities": _segment_opportunities(samples),
        "experimentPlan": _experiment_plan(best_plan),
        "metricGuardrails": _metric_guardrails(best_plan),
        "pmNarrative": _pm_narrative(best_plan, trace),
    }


def _decision_summary(best_plan: dict, issue_count_by_plan: dict[str, int]) -> dict:
    if not best_plan:
        return {
            "recommendation": "暂不决策",
            "reason": "缺少可评估的会员方案。",
            "priorityPlan": "",
        }

    issue_count = issue_count_by_plan.get(best_plan["planId"], 0)
    if best_plan["roi"] >= 1 and best_plan["advancedMetrics"]["memberValueScore"] >= 70 and issue_count == 0:
        recommendation = "建议小流量上线"
        reason = "ROI、会员价值分和校验结果均达到灰度标准。"
    elif best_plan["roi"] >= 0.5 and best_plan["advancedMetrics"]["memberValueScore"] >= 55:
        recommendation = "建议先做策略实验"
        reason = "方案具备潜力，但需要通过价格和权益实验确认真实转化。"
    else:
        recommendation = "建议暂缓上线"
        reason = "当前方案经济性或长期价值不足，需先收敛权益成本。"

    return {
        "recommendation": recommendation,
        "reason": reason,
        "priorityPlan": best_plan["planName"],
        "expectedROI": best_plan["roi"],
        "memberValueScore": best_plan["advancedMetrics"]["memberValueScore"],
    }


def _issue_count_by_plan(validation_issues: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for issue in validation_issues:
        plan_id = issue.get("planId")
        if not plan_id:
            continue
        counts[plan_id] = counts.get(plan_id, 0) + 1
    return counts


def _plan_decision(plan: dict, issue_count: int) -> dict:
    advanced = plan["advancedMetrics"]
    if plan["roi"] >= 1 and advanced["memberValueScore"] >= 70 and issue_count == 0:
        action = "灰度上线"
    elif advanced["priceSensitivityIndex"] > 0.18:
        action = "调整定价"
    elif advanced["benefitCrowdingLoss"] > plan["memberProfit"] * 0.12:
        action = "收敛权益"
    else:
        action = "进入实验"

    return {
        "planId": plan["planId"],
        "planName": plan["planName"],
        "action": action,
        "roi": plan["roi"],
        "memberValueScore": advanced["memberValueScore"],
        "netSequenceValue": advanced["netSequenceValue"],
        "issueCount": issue_count,
    }


def _segment_opportunities(samples: dict[str, list[dict[str, str]]]) -> list[dict]:
    opportunities = []
    for row in samples["userSegments"]:
        user_count = to_int(row["user_count"])
        conversion_rate = to_float(row["member_conversion_rate"])
        baseline_arpu = to_float(row["baseline_arpu"])
        margin_rate = to_float(row["gross_margin_rate"])
        lifecycle = to_float(row["expected_lifecycle_months"])
        opportunity_score = (
            user_count * conversion_rate * baseline_arpu * margin_rate * max(lifecycle, 1) / 1000
        )
        opportunities.append(
            {
                "segmentName": row["segment_name"],
                "opportunityScore": round(opportunity_score, 2),
                "suggestedTactic": _segment_tactic(baseline_arpu, conversion_rate, lifecycle),
            }
        )
    return sorted(opportunities, key=lambda item: item["opportunityScore"], reverse=True)[:5]


def _segment_tactic(arpu: float, conversion_rate: float, lifecycle: float) -> str:
    if arpu >= 120 and lifecycle >= 12:
        return "优先推年卡或高阶权益包，强调长期专属权益。"
    if conversion_rate < 0.08:
        return "先用低门槛体验卡验证付费意愿。"
    if lifecycle < 8:
        return "减少前置权益成本，用短周期任务提升留存。"
    return "用中档权益包做转化实验，观察复购和续费。"


def _experiment_plan(best_plan: dict) -> list[dict]:
    if not best_plan:
        return []

    return [
        {
            "name": "价格弹性实验",
            "hypothesis": "轻微调整价格不会显著降低转化，但能提升单会员净贡献。",
            "variantA": "当前价格与当前权益包",
            "variantB": "价格上调 10%，保留核心高感知权益",
            "primaryMetric": "付费转化率 x 会员毛利",
            "guardrail": "退款率、投诉率、权益核销成本",
        },
        {
            "name": "权益核销上限实验",
            "hypothesis": "限制低感知高成本权益，可以降低挤压损失且不明显影响续费。",
            "variantA": "当前权益核销规则",
            "variantB": "设置优惠券与免邮使用上限",
            "primaryMetric": "权益成本率与 ROI",
            "guardrail": "会员活跃率、复购率",
        },
        {
            "name": "用户分层投放实验",
            "hypothesis": "高 ARPU 与高生命周期用户对会员价值贡献更稳定。",
            "variantA": "全量用户统一投放",
            "variantB": "优先面向高机会分层投放",
            "primaryMetric": "分层 LTV 与续费率",
            "guardrail": "获客成本、转化成本",
        },
    ]


def _metric_guardrails(best_plan: dict) -> list[dict]:
    if not best_plan:
        return []

    return [
        {
            "metric": "权益成本率",
            "target": "权益成本 / 会员收入 <= 80%",
            "current": round(best_plan["benefitCost"] / max(best_plan["memberRevenue"], 1), 2),
        },
        {
            "metric": "续费安全线",
            "target": "预估续费率 >= 盈亏平衡续费率",
            "current": best_plan["expectedRenewalRate"],
        },
        {
            "metric": "模型置信度",
            "target": ">= 0.6 后进入大流量",
            "current": best_plan["advancedMetrics"]["formulaConfidenceScore"],
        },
        {
            "metric": "会员价值分",
            "target": ">= 70 可灰度上线",
            "current": best_plan["advancedMetrics"]["memberValueScore"],
        },
    ]


def _pm_narrative(best_plan: dict, trace: dict) -> list[str]:
    if not best_plan:
        return []
    default_trace = trace["defaultTrace"]
    return [
        f"先用 {best_plan['planName']} 作为优先验证方案，因为它在当前样例中会员价值分最高。",
        "决策不只看 ROI，还同时观察权益挤压损失、续费质量和模型置信度，避免短期盈利掩盖长期风险。",
        f"当前主要追溯结论：{default_trace['drivers'][0]}",
    ]
