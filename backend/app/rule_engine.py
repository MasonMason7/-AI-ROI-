from app.data_loader import to_float, to_int


PLAN_NAME_ZH = {
    "basic_monthly": "基础月卡",
    "plus_quarterly": "Plus 季卡",
    "plus_annual": "Plus 年卡",
    "premium_annual": "高级年卡",
    "student_annual": "学生年卡",
    "family_annual": "家庭年卡",
    "trial_monthly": "体验月卡",
    "vip_annual": "VIP 年卡",
    "city_plus": "城市 Plus 卡",
    "lite_annual": "轻量年卡",
}


def parse_plan_rules(samples: dict[str, list[dict[str, str]]]) -> list[dict]:
    usage_by_plan: dict[str, list[dict]] = {}
    for row in samples["benefitUsage"]:
        usage_by_plan.setdefault(row["plan_id"], []).append(
            {
                "benefitType": row["benefit_type"],
                "issuedCount": to_int(row["issued_count"]),
                "usedCount": to_int(row["used_count"]),
                "unitCost": to_float(row["unit_cost"]),
                "month": row["month"],
            }
        )

    rules = []
    for row in samples["memberPlans"]:
        plan_id = row["plan_id"]
        rules.append(
            {
                "planId": plan_id,
                "planName": PLAN_NAME_ZH.get(plan_id, row["plan_name"]),
                "periodMonths": to_int(row["period_months"], 1),
                "price": to_float(row["price"]),
                "targetMembers": to_int(row["target_members"]),
                "couponValue": to_float(row["coupon_value"]),
                "couponCount": to_int(row["coupon_count"]),
                "shippingBenefitCost": to_float(row["shipping_benefit_cost"]),
                "serviceCost": to_float(row["service_cost"]),
                "expectedRenewalRate": to_float(row["expected_renewal_rate"]),
                "benefitUsage": usage_by_plan.get(plan_id, []),
            }
        )
    return rules
