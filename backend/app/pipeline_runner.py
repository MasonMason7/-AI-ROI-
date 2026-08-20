SCRIPT_REGISTRY = [
    {
        "id": "M01",
        "name": "数据导入与完整性检查",
        "module": "data_loader.py",
        "inputs": ["member_plans.csv", "user_segments.csv", "orders.csv", "benefit_usage.csv"],
        "outputs": ["sampleRowCounts", "fileCompleteness"],
        "description": "统一读取会员方案、用户分层、订单和权益核销数据。",
    },
    {
        "id": "M02",
        "name": "会员规则清洗计算层",
        "module": "rule_engine.py",
        "inputs": ["member_plans.csv", "benefit_usage.csv"],
        "outputs": ["parsedRules"],
        "description": "解析会员价格、权益包、核销限制和续费假设。",
    },
    {
        "id": "M03",
        "name": "增量价值与权益成本测算",
        "module": "calculator.py",
        "inputs": ["parsedRules", "user_segments.csv", "orders.csv"],
        "outputs": ["memberRevenue", "benefitCost", "incrementalGmv", "memberProfit"],
        "description": "按写死公式计算会员收入、权益成本、增量 GMV、毛利、ROI 和 LTV。",
    },
    {
        "id": "M03A",
        "name": "会员价值重估模型",
        "module": "advanced_model.py",
        "inputs": ["calculation", "user_segments.csv", "benefit_usage.csv"],
        "outputs": ["memberValueScore", "netSequenceValue", "benefitCrowdingLoss"],
        "description": "引入价格敏感度、权益挤压损失、续费质量和模型置信度，评估长期会员价值。",
    },
    {
        "id": "M04",
        "name": "异常校验与正确率控制",
        "module": "validator.py",
        "inputs": ["sampleRowCounts", "calculation"],
        "outputs": ["validationIssues"],
        "description": "检查缺失字段、异常价格、高成本权益、负 ROI 和续费压力。",
    },
    {
        "id": "M05",
        "name": "ROI 偏差追溯",
        "module": "trace_analyzer.py",
        "inputs": ["calculation"],
        "outputs": ["riskLevel", "drivers"],
        "description": "解释 ROI 受哪些因素影响，例如权益核销率、会员价格和续费率。",
    },
    {
        "id": "M06",
        "name": "AI 建议与复盘报告",
        "module": "ai_advisor.py + report_generator.py",
        "inputs": ["defaultPlan", "trace", "validationIssues"],
        "outputs": ["aiAdvice", "report"],
        "description": "用规则模板生成自然语言建议和结构化复盘。",
    },
    {
        "id": "M07",
        "name": "产品决策与实验设计",
        "module": "product_strategy.py",
        "inputs": ["plans", "advancedMetrics", "validationIssues"],
        "outputs": ["decisionSummary", "experimentPlan", "metricGuardrails"],
        "description": "将测算结果转成上线建议、用户分层机会、实验设计和指标护栏。",
    },
]

FILE_ALIASES = {
    "member_plans.csv": ["member_plans", "membership", "plan", "方案"],
    "user_segments.csv": ["user_segments", "segment", "user", "用户", "分层"],
    "orders.csv": ["orders", "order", "订单"],
    "benefit_usage.csv": ["benefit_usage", "benefit", "usage", "权益", "核销"],
}


def build_file_manifest(samples: dict[str, list[dict[str, str]]]) -> list[dict]:
    source_map = {
        "member_plans.csv": ("memberPlans", "会员方案数据"),
        "user_segments.csv": ("userSegments", "用户分层数据"),
        "orders.csv": ("orders", "订单数据"),
        "benefit_usage.csv": ("benefitUsage", "权益核销数据"),
    }
    manifest = []
    for filename, (sample_key, label) in source_map.items():
        manifest.append(
            {
                "filename": filename,
                "label": label,
                "matchedModule": _match_file_to_script(filename),
                "rowCount": len(samples.get(sample_key, [])),
                "status": "已锁定",
            }
        )
    return manifest


def build_script_matches(samples: dict[str, list[dict[str, str]]]) -> list[dict]:
    row_counts = {
        "member_plans.csv": len(samples.get("memberPlans", [])),
        "user_segments.csv": len(samples.get("userSegments", [])),
        "orders.csv": len(samples.get("orders", [])),
        "benefit_usage.csv": len(samples.get("benefitUsage", [])),
    }
    matches = []
    for script in SCRIPT_REGISTRY:
        file_inputs = [item for item in script["inputs"] if item.endswith(".csv")]
        matched_count = sum(1 for item in file_inputs if row_counts.get(item, 0) > 0)
        matches.append(
            {
                **script,
                "matchedInputs": matched_count,
                "totalFileInputs": len(file_inputs),
                "status": "可执行" if matched_count == len(file_inputs) else "待补齐",
            }
        )
    return matches


def build_execution_trace(
    samples: dict[str, list[dict[str, str]]],
    rules: list[dict],
    calculation: dict,
    validation_issues: list[dict],
    trace: dict,
    upload_summary: list[dict] | None = None,
) -> dict:
    upload_summary = upload_summary or []
    row_counts = {name: len(rows) for name, rows in samples.items()}
    default_plan = calculation["defaultPlan"]
    default_trace = trace["defaultTrace"]
    steps = [
        {
            "id": "1",
            "title": "数据导入",
            "status": "完成",
            "summary": (
                f"已接入 {len(upload_summary)} 个本地数据源，并用样例数据补齐缺失类型。"
                if upload_summary
                else f"已读取 4 类样例数据，共 {sum(row_counts.values())} 行。"
            ),
            "logs": [
                f"M01 读取会员方案 {row_counts['memberPlans']} 行。",
                f"M01 读取用户分层 {row_counts['userSegments']} 行。",
                f"M01 读取订单数据 {row_counts['orders']} 行。",
                f"M01 读取权益核销 {row_counts['benefitUsage']} 行。",
            ],
        },
        {
            "id": "2",
            "title": "规则清洗",
            "status": "完成",
            "summary": f"已解析 {len(rules)} 个会员方案，并绑定权益核销规则。",
            "logs": [
                "M02 将 plan_id 映射为中文方案名。",
                "M02 将会员价格、周期、续费率和权益成本转为可计算字段。",
            ],
        },
        {
            "id": "3",
            "title": "正式测算",
            "status": "完成",
            "summary": (
                f"{default_plan['planName']} ROI 为 {default_plan['roi']}x，"
                f"会员毛利为 {default_plan['memberProfit']}。"
            ),
            "logs": [
                "M03 计算会员收入 = 会员价格 * 目标会员数。",
                "M03 计算权益成本 = 权益核销成本 + 会员服务成本。",
                "M03 计算 ROI = 会员毛利 / 权益成本。",
                "M03A 计算会员价值分、权益挤压损失、净序列价值和模型置信度。",
            ],
        },
        {
            "id": "4",
            "title": "异常校验",
            "status": "完成",
            "summary": f"共发现 {len(validation_issues)} 条校验提醒。",
            "logs": [
                "M04 检查价格、目标会员数、ROI、权益核销率和续费压力。",
                "M04 将异常项写入 validationIssues，供前端提醒和复盘使用。",
            ],
        },
        {
            "id": "5",
            "title": "追溯、报告与产品决策",
            "status": "完成",
            "summary": f"默认方案风险等级为 {default_trace['riskLevel']}。",
            "logs": default_trace["drivers"] + [
                "M07 将测算结果转成产品决策建议、实验方案和指标护栏。",
            ],
        },
    ]
    return {
        "fileManifest": build_file_manifest(samples),
        "scriptRegistry": SCRIPT_REGISTRY,
        "scriptMatches": build_script_matches(samples),
        "steps": steps,
        "runMode": "本地数据源测算" if upload_summary else "本地样例数据演示",
        "dataSourceNote": (
            "已接入本机数据源；文件仅在 FastAPI 内存中解析，不保存到项目目录。"
            if upload_summary
            else "当前未上传文件，后端仅读取项目 samples 目录中的 CSV 样例数据。"
        ),
    }


def _match_file_to_script(filename: str) -> str:
    lowered = filename.lower()
    for target, aliases in FILE_ALIASES.items():
        if target == lowered or any(alias in lowered for alias in aliases):
            if target in {"member_plans.csv", "benefit_usage.csv"}:
                return "M02 / rule_engine.py"
            if target in {"orders.csv", "user_segments.csv"}:
                return "M03 / calculator.py"
    return "M01 / data_loader.py"
