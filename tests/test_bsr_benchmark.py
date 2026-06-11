"""
BSR Captcha Benchmark — 使用 ground truth 量化 OCR 正確率
檔案位置: tests/test_bsr_benchmark.py

用法:
    pytest tests/test_bsr_benchmark.py -v
"""
import csv
from pathlib import Path

import pytest

from src.spiders.ocr_solver import OcrSolver


LABELS_FILE = Path("data/tmp/captcha_test/labels_bsr.csv")
SAMPLES_DIR = Path("data/tmp/captcha_test")


def _load_labels() -> list[tuple[str, str]]:
    """讀取標註好的 ground truth labels"""
    pairs = []
    with open(LABELS_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            fname = row["filename"].strip()
            gt = row["ground_truth"].strip()
            if gt and fname.startswith("captcha_"):
                pairs.append((fname, gt))
    return pairs


class TestBsrcaptchaBenchmark:
    """BSR captcha 正確率 benchmark"""

    @pytest.fixture(scope="class")
    def labels(self):
        return _load_labels()

    @pytest.fixture(scope="class")
    def solver(self):
        return OcrSolver()

    def test_raw_ocr_accuracy(self, solver, labels):
        """Baseline: 原始 ddddocr 正確率（case insensitive）"""
        total = len(labels)
        correct = 0
        for fname, gt in labels:
            path = SAMPLES_DIR / fname
            with open(path, "rb") as f:
                pred = solver.solve(f.read()).strip().upper()
            if pred == gt:
                correct += 1
        acc = correct / total * 100
        print(f"\n  Raw OCR (UPPER): {correct}/{total} = {acc:.1f}%")
        # 至少有 30% 才算合理
        assert acc > 30, f"Raw OCR accuracy too low: {acc:.1f}%"

    def test_voting_accuracy(self, solver, labels):
        """Voting 模式正確率"""
        total = len(labels)
        correct = 0
        for fname, gt in labels:
            path = SAMPLES_DIR / fname
            with open(path, "rb") as f:
                pred, _, _ = solver.solve_with_voting(f.read())
            if pred.strip().upper() == gt:
                correct += 1
        acc = correct / total * 100
        print(f"\n  Voting (UPPER): {correct}/{total} = {acc:.1f}%")
        assert acc > 30, f"Voting accuracy too low: {acc:.1f}%"

    def test_confidence_method_accuracy(self, solver, labels):
        """solve_with_confidence 正確率"""
        total = len(labels)
        correct = 0
        for fname, gt in labels:
            path = SAMPLES_DIR / fname
            with open(path, "rb") as f:
                pred, _ = solver.solve_with_confidence(f.read())
            if pred.strip().upper() == gt:
                correct += 1
        acc = correct / total * 100
        print(f"\n  Confidence (UPPER): {correct}/{total} = {acc:.1f}%")
        assert acc > 30, f"Confidence accuracy too low: {acc:.1f}%"
