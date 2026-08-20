REQUIRED_PLAN_FIELDS = {
    "plan_id",
    "plan_name",
    "period_months",
    "price",
    "target_members",
    "expected_renewal_rate",
}


def validate_samples(samples: dict[str, list[dict[str, str]]]) -> list[dict]:
    issues = []
    for index, row in enumerate(samples["memberPlans"], start=1):
        missing = [field for field in REQUIRED_PLAN_FIELDS if not row.get(field)]
        if missing:
            issues.append(
                {
                    "level": "error",
                    "scope": "memberPlans",
                    "message": f"会员方案表第 {index} 行缺少字段：{', '.join(missing)}。",
                }
            )
    return issues


def validate_plan_result(plan: dict) -> list[dict]:
    issues = []
    if plan["price"] <= 0:
        issues.append({"level": "error", "message": "会员价格必须大于 0。"})
    if plan["targetMembers"] <= 0:
        issues.append({"level": "error", "message": "目标会员数必须大于 0。"})
    if plan["roi"] < 0:
        issues.append(
            {
                "level": "warning",
                "message": f"{plan['planName']} 的 ROI 为负，权益成本已经超过当前可捕获价值。",
            }
        )
    if plan["benefitUsageRate"] > 0.65:
        issues.append(
            {
                "level": "warning",
                "message": f"{plan['planName']} 的权益核销率偏高，建议检查优惠券或免邮使用限制。",
            }
        )
    if plan["breakEvenRenewalRate"] > plan["expectedRenewalRate"]:
        issues.append(
            {
                "level": "warning",
                "message": f"{plan['planName']} 的预估续费率低于盈亏平衡续费率。",
            }
        )
    if plan["benefitCost"] > plan["memberRevenue"] * 0.8:
        issues.append(
            {
                "level": "warning",
                "message": f"{plan['planName']} 的权益成本超过会员收入的 80%。",
            }
        )
    return issues


def validate_results(calculation: dict) -> list[dict]:
    issues = []
    for plan in calculation["plans"]:
        for issue in validate_plan_result(plan):
            issues.append({"planId": plan["planId"], **issue})
    return issues
