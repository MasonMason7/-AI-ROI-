from csv import DictReader
from io import StringIO
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLES_DIR = ROOT_DIR / "samples"

DATASET_RULES = {
    "memberPlans": {
        "sampleFile": "member_plans.csv",
        "label": "会员方案数据",
        "aliases": ["member", "membership", "plan", "会员", "方案"],
        "requiredFields": {"plan_id", "price", "target_members"},
    },
    "userSegments": {
        "sampleFile": "user_segments.csv",
        "label": "用户分层数据",
        "aliases": ["segment", "user", "用户", "分层"],
        "requiredFields": {"segment_id", "expected_lifecycle_months"},
    },
    "orders": {
        "sampleFile": "orders.csv",
        "label": "订单数据",
        "aliases": ["order", "订单"],
        "requiredFields": {"order_id", "order_amount", "gross_margin"},
    },
    "benefitUsage": {
        "sampleFile": "benefit_usage.csv",
        "label": "权益核销数据",
        "aliases": ["benefit", "usage", "权益", "核销"],
        "requiredFields": {"benefit_type", "used_count", "unit_cost"},
    },
}


def load_csv(filename: str) -> list[dict[str, str]]:
    path = SAMPLES_DIR / filename
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(DictReader(file))


def load_all_samples() -> dict[str, list[dict[str, str]]]:
    return {
        key: load_csv(rule["sampleFile"]) for key, rule in DATASET_RULES.items()
    }


def load_samples_from_uploads(
    upload_payloads: list[dict[str, bytes]],
) -> tuple[dict[str, list[dict[str, str]]], list[dict]]:
    samples = load_all_samples()
    upload_summary = []

    for index, payload in enumerate(upload_payloads, start=1):
        rows = _read_uploaded_csv(payload["content"])
        matched_key = _match_dataset(payload.get("filename", ""), rows)
        if not matched_key:
            upload_summary.append(
                {
                    "sourceId": f"uploaded_file_{index}",
                    "dataset": "未匹配数据",
                    "rowCount": len(rows),
                    "status": "已忽略",
                }
            )
            continue

        samples[matched_key] = rows
        upload_summary.append(
            {
                "sourceId": f"uploaded_file_{index}",
                "dataset": DATASET_RULES[matched_key]["label"],
                "rowCount": len(rows),
                "status": "已接入上传数据",
            }
        )

    return samples, upload_summary


def scan_folder(folder_path: str) -> list[dict]:
    folder = Path(folder_path).expanduser()
    if not folder.exists() or not folder.is_dir():
        return []

    summary = []
    for index, path in enumerate(sorted(folder.rglob("*.csv")), start=1):
        rows = _read_csv_path(path)
        matched_key = _match_dataset(path.name, rows)
        summary.append(
            {
                "sourceId": f"folder_file_{index}",
                "dataset": DATASET_RULES[matched_key]["label"] if matched_key else "未匹配数据",
                "rowCount": len(rows),
                "status": "已匹配" if matched_key else "未使用",
            }
        )
    return summary


def load_samples_from_folder(
    folder_path: str,
) -> tuple[dict[str, list[dict[str, str]]], list[dict]]:
    samples = load_all_samples()
    folder = Path(folder_path).expanduser()
    folder_summary = []

    if not folder.exists() or not folder.is_dir():
        return samples, [
            {
                "sourceId": "folder_path",
                "dataset": "数据文件夹",
                "rowCount": 0,
                "status": "路径无效，已回退样例数据",
            }
        ]

    matched_keys = set()
    for index, path in enumerate(sorted(folder.rglob("*.csv")), start=1):
        rows = _read_csv_path(path)
        matched_key = _match_dataset(path.name, rows)
        if not matched_key:
            folder_summary.append(
                {
                    "sourceId": f"folder_file_{index}",
                    "dataset": "未匹配数据",
                    "rowCount": len(rows),
                    "status": "已忽略",
                }
            )
            continue

        if matched_key not in matched_keys:
            samples[matched_key] = rows
            matched_keys.add(matched_key)
            status = "已接入文件夹数据"
        else:
            status = "重复类型，已忽略"

        folder_summary.append(
            {
                "sourceId": f"folder_file_{index}",
                "dataset": DATASET_RULES[matched_key]["label"],
                "rowCount": len(rows),
                "status": status,
            }
        )

    for key, rule in DATASET_RULES.items():
        if key not in matched_keys:
            folder_summary.append(
                {
                    "sourceId": f"fallback_{key}",
                    "dataset": rule["label"],
                    "rowCount": len(samples[key]),
                    "status": "未匹配到文件，使用样例数据补齐",
                }
            )

    return samples, folder_summary


def _read_uploaded_csv(content: bytes) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = content.decode(encoding)
            return list(DictReader(StringIO(text)))
        except UnicodeDecodeError:
            continue
    return []


def _read_csv_path(path: Path) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as file:
                return list(DictReader(file))
        except UnicodeDecodeError:
            continue
    return []


def _match_dataset(filename: str, rows: list[dict[str, str]]) -> str | None:
    lowered_name = filename.lower()
    fields = set(rows[0].keys()) if rows else set()

    for key, rule in DATASET_RULES.items():
        if rule["requiredFields"].issubset(fields):
            return key

    for key, rule in DATASET_RULES.items():
        if any(alias.lower() in lowered_name for alias in rule["aliases"]):
            return key

    return None


def to_float(value: str, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def to_int(value: str, default: int = 0) -> int:
    if value is None or value == "":
        return default
    return int(float(value))
