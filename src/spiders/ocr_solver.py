"""
ddddocr 封裝模組，提供統一的 captcha 解碼介面
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional

from PIL import Image

import ddddocr

logger = logging.getLogger(__name__)


class OcrSolver:
    """
    ddddocr 封裝，提供 captcha 圖片解碼功能

    Attributes:
        _ocr: ddddocr.DdddOcr 實例
    """

    def __init__(self, gpu: bool = False) -> None:
        """
        初始化 OcrSolver

        Args:
            gpu: 是否啟用 GPU 加速 (傳入 ddddocr 的 use_gpu 參數)
        """
        self._ocr = ddddocr.DdddOcr(use_gpu=gpu)
        logger.info("OcrSolver initialized (gpu=%s)", gpu)

    def solve(self, image_bytes: bytes) -> str:
        """
        直接對圖片 bytes 執行 OCR 辨識

        Args:
            image_bytes: PNG/JPEG 圖片 bytes

        Returns:
            辨識出的文字字串
        """
        result = self._ocr.classification(image_bytes)
        logger.debug("OCR solve result: %s", result)
        return result

    def solve_with_preprocess(self, image_bytes: bytes, threshold: int = 128) -> str:
        """
        先對圖片進行灰階 + 二值化預處理，再執行 OCR

        Args:
            image_bytes: PNG/JPEG 圖片 bytes
            threshold: 二值化門檻值 (0-255)，預設 128

        Returns:
            辨識出的文字字串
        """
        from io import BytesIO

        img = Image.open(BytesIO(image_bytes)).convert("L")
        img = img.point(lambda x: 255 if x > threshold else 0, mode="1")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        processed_bytes = buf.getvalue()

        result = self._ocr.classification(processed_bytes)
        logger.debug("OCR solve_with_preprocess result: %s", result)
        return result

    def solve_with_confidence(
        self, image_bytes: bytes, png_fix: bool = True
    ) -> tuple[str, float]:
        """
        OCR 辨識 + 信心度萃取

        ddddocr 的 classification() 在 probability=True 時回傳 dict:
            {"text": "...", "probabilities": [[[c0_p, c1_p, ...]], ...]}

        Args:
            image_bytes: PNG/JPEG 圖片 bytes
            png_fix: 是否啟用 ddddocr PNG 透明背景修復

        Returns:
            (text, confidence)
            - text: 辨識文字
            - confidence: 0.0~1.0，取所有字元信心度最小值
        """
        raw = self._ocr.classification(image_bytes, probability=True, png_fix=png_fix)

        if not isinstance(raw, dict):
            logger.warning(
                "OCR did not return dict with probability=True (got %s), "
                "falling back to plain classification", type(raw).__name__
            )
            return str(raw), 0.0

        text = raw.get("text", "")
        probs = raw.get("probabilities", [])

        if not text or not probs:
            logger.debug("OCR returned empty text or no probabilities")
            return text, 0.0

        # probabilities 結構: [[[c0, c1, ...]], [[c0, c1, ...]], ...]
        # 每個字元取 max(該位置類別機率)，全字元取 min
        char_confs: list[float] = []
        for cp in probs:
            if cp and isinstance(cp, list) and len(cp) > 0 and cp[0]:
                char_confs.append(max(cp[0]))

        if not char_confs:
            return text, 0.0

        confidence = min(char_confs)
        logger.debug("OCR solve_with_confidence: text=%s, confidence=%.4f", text, confidence)
        return text, confidence

    def solve_with_voting(
        self,
        image_bytes: bytes,
        thresholds: Optional[list[int]] = None,
        use_original: bool = True,
        png_fix: bool = True,
        min_votes: int = 2,
    ) -> tuple[str, float, dict]:
        """
        多 threshold 投票機制，對同一 captcha 以多種二值化門檻值分別 OCR，
        透過投票選出最可靠的結果。

        Args:
            image_bytes: PNG/JPEG 圖片 bytes
            thresholds: 二值化門檻值列表，預設 [100, 128, 150, 180]
            use_original: 是否加入原始圖的 OCR 結果
            png_fix: 是否啟用 ddddocr PNG 透明背景修復
            min_votes: 勝出者最低票數，低於此值則 fallback 到最高信心度結果

        Returns:
            (winner_text, winner_avg_confidence, voting_detail)
            - winner_text: 勝出文字
            - winner_avg_confidence: 勝出組的平均信心度
            - voting_detail: 投票詳細資訊 dict
        """
        from io import BytesIO

        if thresholds is None:
            thresholds = [100, 128, 150, 180]

        results: list[tuple[str, float, object]] = []

        # 1. 原始圖 OCR
        if use_original:
            text, conf = self.solve_with_confidence(image_bytes, png_fix=png_fix)
            results.append((text, conf, "original"))

        # 2. 各 threshold 前處理 + OCR
        for threshold in thresholds:
            img = Image.open(BytesIO(image_bytes)).convert("L")
            img = img.point(lambda x: 255 if x > threshold else 0, mode="1")
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            processed_bytes = buf.getvalue()

            raw = self._ocr.classification(
                processed_bytes, probability=True, png_fix=png_fix
            )

            if isinstance(raw, dict):
                text = raw.get("text", "")
                probs = raw.get("probabilities", [])
                if text and probs:
                    char_confs: list[float] = []
                    for cp in probs:
                        if cp and isinstance(cp, list) and len(cp) > 0 and cp[0]:
                            char_confs.append(max(cp[0]))
                    conf = min(char_confs) if char_confs else 0.0
                else:
                    conf = 0.0
            else:
                text = str(raw)
                conf = 0.0

            results.append((text, conf, threshold))

        # 3. 投票
        if not results:
            detail: dict = {
                "votes": {},
                "results": [],
                "agreement": 0.0,
                "winner_text": "",
                "winner_avg_conf": 0.0,
            }
            return "", 0.0, detail

        votes: dict[str, list[tuple[float, object]]] = defaultdict(list)
        for text, conf, source in results:
            votes[text].append((conf, source))

        # 找出最高票（平手時取平均信心度較高者）
        def _vote_key(text: str) -> tuple[int, float]:
            entries = votes[text]
            avg_conf = sum(e[0] for e in entries) / len(entries)
            return (len(entries), avg_conf)

        winner_text = max(votes, key=_vote_key)
        winner_entries = votes[winner_text]
        max_votes = len(winner_entries)
        winner_avg_conf = sum(e[0] for e in winner_entries) / max_votes

        # 若勝出者票數 < min_votes，fallback 到最高信心度單一結果
        if max_votes < min_votes:
            best = max(results, key=lambda r: r[1])
            winner_text = best[0]
            winner_avg_conf = best[1]

        agreement = max_votes / len(results)

        voting_detail: dict = {
            "votes": {text: len(entries) for text, entries in votes.items()},
            "results": [(text, conf, src) for text, conf, src in results],
            "agreement": agreement,
            "winner_text": winner_text,
            "winner_avg_conf": winner_avg_conf,
        }

        logger.debug(
            "OCR solve_with_voting: winner=%s, conf=%.4f, agreement=%.2f",
            winner_text, winner_avg_conf, agreement,
        )
        return winner_text, winner_avg_conf, voting_detail
