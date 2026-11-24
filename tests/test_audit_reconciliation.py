"""Exercise the CI reconciliation command using only synthetic data."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "audit_reconciliation.py"
MONTH = "209912"
PAYMENT_PERIOD = f"{MONTH}27"
PRIVATE_VALUE = "SYNTHETIC_PRIVATE_FIELD"


def run_audit(tmp_path, usage, payment):
    paths = (tmp_path / "usage.json", tmp_path / "payment.json")
    for path, payload in zip(paths, (usage, payment), strict=True):
        path.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--usage", str(paths[0]), "--payment", str(paths[1])],
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=10,
        check=False,
    )


@pytest.fixture
def matching_records():
    return (
        [{"ysny": MONTH, "sybs": 1100, "bybs": 1117, "sl": 17, "hjfy": 123.75}],
        [
            {"xzyf": PAYMENT_PERIOD, "scye": 201.5, "bcye": 77.75, "jfje": 0},
            {"xzyf": PAYMENT_PERIOD, "scye": 11.25, "bcye": 88.25, "jfje": 77},
        ],
    )


def assert_summary(result, *, passed, failed):
    assert result.returncode == int(failed > 0)
    status = "PASS" if failed == 0 else "FAIL"
    assert result.stdout.splitlines() == [f"结果: {status}（通过 {passed} 条，失败 {failed} 条）"]
    assert not result.stderr


def test_ci_pass_prints_only_counts(tmp_path, matching_records):
    result = run_audit(tmp_path, *matching_records)
    assert_summary(result, passed=3, failed=0)


@pytest.mark.parametrize(
    ("dataset", "index", "key", "replacement", "failed"),
    [
        (0, 0, "sl", 18, 1),  # A: meter difference does not match usage
        (1, 0, "bcye", 76.75, 1),  # B: automatic debit does not match invoice
        (1, 0, "xzyf", "20991127", 1),  # B: no invoice for the month
        (1, 1, "jfje", 78, 1),  # C: manual payment does not match balance change
        (0, 0, "sl", PRIVATE_VALUE, 2),  # A conversion failure also leaves B without an invoice
        (1, 1, "scye", PRIVATE_VALUE, 1),  # C: numeric conversion error
    ],
)
def test_ci_failure_does_not_print_record_details(tmp_path, matching_records, dataset, index, key, replacement, failed):
    matching_records[dataset][index][key] = replacement
    result = run_audit(tmp_path, *matching_records)
    assert_summary(result, passed=3 - failed, failed=failed)


@pytest.mark.parametrize("usage", [{"payload": PRIVATE_VALUE}, [PRIVATE_VALUE]])
def test_ci_bad_input_does_not_echo_payload_or_path(tmp_path, usage):
    result = run_audit(tmp_path, usage, [])
    assert result.returncode == 2
    assert not result.stdout
    assert result.stderr.splitlines() == ["输入错误：用水和缴费样本必须是可读取的 JSON 记录数组。"]
