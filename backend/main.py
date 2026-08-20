from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.data_loader import (
    load_all_samples,
    load_samples_from_folder,
    load_samples_from_uploads,
    scan_folder,
)
from app.rule_engine import parse_plan_rules
from app.calculator import calculate_all
from app.validator import validate_results, validate_samples
from app.trace_analyzer import analyze
from app.ai_advisor import generate_advice
from app.report_generator import generate_report
from app.pipeline_runner import build_execution_trace
from app.advanced_model import formula_cards
from app.product_strategy import build_product_strategy

app = FastAPI(title="MemberPilot AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "MemberPilot AI 后端服务"}


@app.get("/api/calculate")
def calculate():
    samples = load_all_samples()
    return _build_calculation_response(
        samples,
        "已基于 CSV 样例数据完成脚本化测算。",
        [],
    )


@app.post("/api/calculate")
async def calculate_with_uploads(payload: dict = Body(default={})):
    upload_payloads = []
    for file in payload.get("files", []):
        upload_payloads.append(
            {
                "filename": file.get("filename", ""),
                "content": file.get("content", "").encode("utf-8"),
            }
        )

    samples, upload_summary = load_samples_from_uploads(upload_payloads)
    message = (
        "已基于上传 CSV 数据完成脚本化测算。"
        if upload_payloads
        else "未检测到上传文件，已回退使用 CSV 样例数据完成测算。"
    )
    return _build_calculation_response(samples, message, upload_summary)


@app.post("/api/scan-folder")
async def scan_data_folder(payload: dict = Body(default={})):
    folder_path = payload.get("folderPath", "")
    summary = scan_folder(folder_path)
    return {
        "status": "ok",
        "message": "已完成本地文件夹扫描，结果未包含真实路径。",
        "matchedCount": len([item for item in summary if item["status"] == "已匹配"]),
        "unmatchedCount": len([item for item in summary if item["status"] == "未使用"]),
        "items": summary,
    }


@app.post("/api/calculate-folder")
async def calculate_with_folder(payload: dict = Body(default={})):
    folder_path = payload.get("folderPath", "")
    samples, folder_summary = load_samples_from_folder(folder_path)
    return _build_calculation_response(
        samples,
        "已基于本地文件夹数据完成脚本化测算。",
        folder_summary,
    )


def _build_calculation_response(
    samples: dict[str, list[dict[str, str]]],
    message: str,
    upload_summary: list[dict],
):
    row_counts = {name: len(rows) for name, rows in samples.items()}
    rules = parse_plan_rules(samples)
    calculation = calculate_all(rules, samples)
    sample_issues = validate_samples(samples)
    result_issues = validate_results(calculation)
    trace = analyze(calculation)
    default_plan = calculation["defaultPlan"]
    default_issues = [
        issue for issue in result_issues if issue.get("planId") == default_plan["planId"]
    ]
    all_issues = sample_issues + result_issues
    advice = generate_advice(default_plan, trace["defaultTrace"], default_issues)
    report = generate_report(default_plan, trace["defaultTrace"], advice)
    pipeline = build_execution_trace(
        samples,
        rules,
        calculation,
        all_issues,
        trace,
        upload_summary,
    )
    product_strategy = build_product_strategy(
        calculation,
        samples,
        trace,
        all_issues,
    )

    return {
        "scenario": f"{default_plan['planName']} 会员 ROI 测算",
        "status": "ok",
        "message": message,
        "uploadSummary": upload_summary,
        "pipeline": pipeline,
        "sampleRowCounts": row_counts,
        "assumptions": calculation["assumptions"],
        "advancedFormulaCards": formula_cards(),
        "productStrategy": product_strategy,
        "metrics": {
            "memberRevenue": default_plan["memberRevenue"],
            "benefitCost": default_plan["benefitCost"],
            "incrementalGmv": default_plan["incrementalGmv"],
            "memberProfit": default_plan["memberProfit"],
            "roi": default_plan["roi"],
            "ltv": default_plan["ltv"],
            "breakEvenRenewalRate": default_plan["breakEvenRenewalRate"],
        },
        "plans": calculation["plans"],
        "alerts": [issue["message"] for issue in all_issues],
        "validationIssues": all_issues,
        "trace": trace,
        "aiAdvice": advice,
        "report": report,
    }
