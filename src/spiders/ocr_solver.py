"""
ddddocr 封裝模組，提供統一的 captcha 解碼介面
"""
from __future__ import annotations

import logging
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
