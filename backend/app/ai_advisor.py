def generate_advice(plan: dict, trace: dict, issues: list[dict]) -> list[str]:
    advice = [
        f"{plan['planName']} 当前 ROI 为 {plan['roi']}x，预估 LTV 为 {plan['ltv']}。",
    ]

    if trace["riskLevel"] == "high":
        advice.append(
            "主要风险：方案经济性偏弱，建议先降低高成本权益或调整价格，再扩大投放。"
        )
    elif trace["riskLevel"] == "medium":
        advice.append(
            "主要风险：ROI 为正但对权益核销较敏感，建议小范围上线并监控成本上限。"
        )
    else:
        advice.append(
            "样例模型下方案较健康，可以优先验证转化率和续费率。"
        )

    if issues:
        advice.append("校验模块发现需要上线前复核的问题。")
    else:
        advice.append("样例数据中暂未发现阻塞性校验问题。")

    advice.append(
        "下一步实验：按高价值用户和价格敏感用户分层，对价格、优惠券数量和免邮上限做 A/B 测试。"
    )
    return advice
