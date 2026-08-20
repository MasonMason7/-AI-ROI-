def risk_level(plan: dict) -> str:
    if plan["roi"] < 0 or plan["breakEvenRenewalRate"] > plan["expectedRenewalRate"]:
        return "high"
    if plan["roi"] < 1 or plan["benefitUsageRate"] > 0.55:
        return "medium"
    return "low"


def explain_plan(plan: dict) -> list[str]:
    traces = []
    if plan["roi"] >= 1:
        traces.append(
            f"{plan['planName']} 在样例模型中具备正向收益，会员毛利可以覆盖权益成本。"
        )
    else:
        traces.append(
            f"{plan['planName']} 的 ROI 偏弱，主要因为权益成本接近或超过当前可捕获价值。"
        )

    if plan["benefitUsageRate"] > 0.55:
        traces.append(
            "权益核销率偏高，是当前方案的主要成本驱动项，建议检查免邮和优惠券限制。"
        )
    if plan["breakEvenRenewalRate"] > plan["expectedRenewalRate"]:
        traces.append(
            "预估续费率低于盈亏平衡续费率，说明长期价值存在不确定性。"
        )
    if plan["price"] < plan["benefitCost"] / max(plan["targetMembers"], 1):
        traces.append(
            "单会员权益成本高于会员价格，方案需要依赖增量订单毛利来覆盖成本。"
        )
    if len(traces) == 1:
        traces.append("样例数据中暂未发现严重成本或续费异常。")
    return traces


def analyze(calculation: dict) -> dict:
    plan_traces = []
    for plan in calculation["plans"]:
        plan_traces.append(
            {
                "planId": plan["planId"],
                "planName": plan["planName"],
                "riskLevel": risk_level(plan),
                "drivers": explain_plan(plan),
            }
        )

    default_plan_id = calculation["defaultPlan"]["planId"]
    default_trace = next(item for item in plan_traces if item["planId"] == default_plan_id)
    return {"defaultTrace": default_trace, "planTraces": plan_traces}
