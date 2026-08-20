import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.calculator import calculate_plan


def test_calculate_plan_core_formula():
    rule = {
        "planId": "test",
        "planName": "Test Plan",
        "periodMonths": 12,
        "price": 100,
        "targetMembers": 10,
        "serviceCost": 2,
        "expectedRenewalRate": 0.5,
        "benefitUsage": [
            {
                "benefitType": "coupon",
                "issuedCount": 100,
                "usedCount": 20,
                "unitCost": 3,
                "month": "2026-07",
            }
        ],
    }
    assumptions = {
        "avgMemberOrder": 80,
        "avgNonMemberOrder": 50,
        "avgMemberMargin": 20,
        "avgNonMemberMargin": 12,
        "avgLifecycleMonths": 10,
    }

    result = calculate_plan(rule, assumptions)

    assert result["memberRevenue"] == 1000
    assert result["benefitCost"] == 80
    assert result["incrementalGmv"] == 3600
    assert result["incrementalOrderMargin"] == 960
    assert result["memberProfit"] == 1880
    assert result["roi"] == 23.5
    assert result["benefitUsageRate"] == 0.2
