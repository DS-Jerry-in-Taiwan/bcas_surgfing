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
            gpu: 是否啟用 GPU 加速 (目前 ddddocr 自動偵測，此參數保留相容性)
        """
        self._ocr = ddddocr.DdddOcr()
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
