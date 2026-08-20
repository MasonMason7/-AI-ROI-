def generate_report(plan: dict, trace: dict, advice: list[str]) -> dict:
    return {
        "title": f"{plan['planName']} 会员 ROI 复盘",
        "summary": (
            f"{plan['planName']} 在样例模型中预估会员毛利为 {plan['memberProfit']}，"
            f"ROI 为 {plan['roi']}x。"
        ),
        "riskLevel": trace["riskLevel"],
        "keyDrivers": trace["drivers"],
        "recommendations": advice,
        "nextStep": "建议先做小范围灰度上线，对比预测 ROI、真实续费率和权益核销数据。",
    }
