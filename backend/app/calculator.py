from app.data_loader import to_float
from app.advanced_model import calculate_advanced_metrics


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _round(value: float) -> float:
    return round(value, 2)


def market_assumptions(samples: dict[str, list[dict[str, str]]]) -> dict[str, float]:
    orders = samples["orders"]
    member_orders = [row for row in orders if row["is_member"].lower() == "true"]
    non_member_orders = [row for row in orders if row["is_member"].lower() == "false"]
    segments = samples["userSegments"]

    avg_member_order = _safe_div(
        sum(to_float(row["order_amount"]) for row in member_orders), len(member_orders)
    )
    avg_non_member_order = _safe_div(
        sum(to_float(row["order_amount"]) for row in non_member_orders),
        len(non_member_orders),
    )
    avg_member_margin = _safe_div(
        sum(to_float(row["gross_margin"]) for row in member_orders), len(member_orders)
    )
    avg_non_member_margin = _safe_div(
        sum(to_float(row["gross_margin"]) for row in non_member_orders),
        len(non_member_orders),
    )
    avg_lifecycle = _safe_div(
        sum(to_float(row["expected_lifecycle_months"]) for row in segments),
        len(segments),
    )

    return {
        "avgMemberOrder": avg_member_order,
        "avgNonMemberOrder": avg_non_member_order,
        "avgMemberMargin": avg_member_margin,
        "avgNonMemberMargin": avg_non_member_margin,
        "avgLifecycleMonths": avg_lifecycle,
    }


def calculate_plan(rule: dict, assumptions: dict[str, float]) -> dict:
    target_members = rule["targetMembers"]
    period_months = rule["periodMonths"]
    member_revenue = rule["price"] * target_members

    usage_cost = sum(
        item["usedCount"] * item["unitCost"] for item in rule["benefitUsage"]
    )
    service_cost = target_members * rule["serviceCost"]
    benefit_cost = usage_cost + service_cost

    incremental_order_amount = max(
        assumptions["avgMemberOrder"] - assumptions["avgNonMemberOrder"], 0
    )
    incremental_margin_per_order = max(
        assumptions["avgMemberMargin"] - assumptions["avgNonMemberMargin"], 0
    )
    incremental_gmv = incremental_order_amount * target_members * period_months
    incremental_order_margin = incremental_margin_per_order * target_members * period_months

    member_profit = member_revenue + incremental_order_margin - benefit_cost
    roi = _safe_div(member_profit, benefit_cost)
    monthly_profit_per_member = _safe_div(member_profit, target_members * period_months)
    ltv = monthly_profit_per_member * assumptions["avgLifecycleMonths"]
    break_even_renewal_rate = _safe_div(benefit_cost, member_revenue + incremental_order_margin)

    issued_count = sum(item["issuedCount"] for item in rule["benefitUsage"])
    used_count = sum(item["usedCount"] for item in rule["benefitUsage"])
    usage_rate = _safe_div(used_count, issued_count)

    return {
        "planId": rule["planId"],
        "planName": rule["planName"],
        "periodMonths": period_months,
        "price": rule["price"],
        "targetMembers": target_members,
        "expectedRenewalRate": rule["expectedRenewalRate"],
        "memberRevenue": _round(member_revenue),
        "benefitCost": _round(benefit_cost),
        "usageCost": _round(usage_cost),
        "serviceCost": _round(service_cost),
        "incrementalGmv": _round(incremental_gmv),
        "incrementalOrderMargin": _round(incremental_order_margin),
        "memberProfit": _round(member_profit),
        "roi": _round(roi),
        "ltv": _round(ltv),
        "breakEvenRenewalRate": _round(break_even_renewal_rate),
        "benefitUsageRate": _round(usage_rate),
    }


def calculate_all(rules: list[dict], samples: dict[str, list[dict[str, str]]]) -> dict:
    assumptions = market_assumptions(samples)
    plans = []
    for rule in rules:
        plan = calculate_plan(rule, assumptions)
        plan["advancedMetrics"] = calculate_advanced_metrics(plan, samples)
        plans.append(plan)
    default_plan = next(
        (plan for plan in plans if plan["planId"] == "plus_annual"),
        plans[0] if plans else {},
    )
    return {
        "assumptions": {key: _round(value) for key, value in assumptions.items()},
        "plans": plans,
        "defaultPlan": default_plan,
    }
