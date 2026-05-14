"""
BSR Captcha OCR 測試腳本
獨立測試 ddddocr 對 BSR 驗證碼的辨識率
"""
import sys
sys.path.insert(0, 'src')

import os
import time
import requests
from pathlib import Path
import re


class BsrCaptchaTester:
    """BSR 驗證碼 OCR 測試器"""

    def __init__(self, output_dir="data/tmp/captcha_test"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.results = []

    def get_captcha(self):
        """
        從 BSR 取得驗證碼圖片

        流程:
        1. GET bsMenu.aspx → 取得 __VIEWSTATE + 新的 captcha GUID
        2. GET CaptchaImage.aspx?guid=XXX → 下載圖片

        Returns:
            (image_bytes, guid) or (None, None) on failure
        """
        # Step 1: 先訪問 bsMenu.aspx 取得 session + captcha guid
        resp = self.session.get("https://bsr.twse.com.tw/bshtm/bsMenu.aspx")
        # 從 HTML 中找出 captcha 圖片的 URL
        match = re.search(r'CaptchaImage\.aspx\?guid=([^"\'&]+)', resp.text)
        if not match:
            print("⚠️ 找不到驗證碼圖片 URL")
            return None, None

        guid = match.group(1)

        # Step 2: 下載驗證碼圖片
        captcha_url = f"https://bsr.twse.com.tw/bshtm/CaptchaImage.aspx?guid={guid}"
        img_resp = self.session.get(captcha_url)

        if img_resp.status_code != 200 or len(img_resp.content) < 100:
            print(f"⚠️ 下載驗證碼失敗: HTTP {img_resp.status_code}, size={len(img_resp.content)}")
            return None, None

        return img_resp.content, guid

    def test_single(self, ocr, index: int):
        """測試單次 captcha 辨識"""
        img_bytes, guid = self.get_captcha()
        if img_bytes is None:
            return None

        # 儲存圖片
        img_path = self.output_dir / f"captcha_{index:03d}_{guid[:8]}.png"
        with open(img_path, 'wb') as f:
            f.write(img_bytes)

        # OCR 辨識
        start = time.time()
        try:
            result = ocr.classification(img_bytes)
            elapsed = time.time() - start
            return {
                "index": index,
                "guid": guid,
                "result": result,
                "time_ms": round(elapsed * 1000, 1),
                "image_path": str(img_path),
            }
        except Exception as e:
            return {
                "index": index,
                "guid": guid,
                "error": str(e),
                "image_path": str(img_path),
            }

    def batch_test(self, count: int = 30):
        """批次測試"""
        import ddddocr
        ocr = ddddocr.DdddOcr()

        print(f"\n=== BSR Captcha OCR 測試 ({count} 次) ===\n")

        for i in range(count):
            result = self.test_single(ocr, i + 1)
            if result:
                self.results.append(result)
                if 'result' in result:
                    status = f"✅ {result['result']}"
                else:
                    status = f"❌ {result.get('error', '')}"
                print(f"  [{i+1}/{count}] {status} ({result.get('time_ms', 0)}ms)")
            time.sleep(0.5)  # 避免被 ban

        self._print_summary()

    def _print_summary(self):
        """列印統計摘要"""
        total = len(self.results)
        success = [r for r in self.results if 'result' in r]
        failed = [r for r in self.results if 'error' in r]

        print(f"\n{'='*60}")
        print(f"  測試結果統計")
        print(f"{'='*60}")
        print(f"  總次數: {total}")
        print(f"  成功: {len(success)}")
        print(f"  失敗: {len(failed)}")
        if total > 0:
            print(f"  成功率: {len(success)/total*100:.1f}%")
        else:
            print(f"  成功率: N/A")

        if success:
            avg_time = sum(r['time_ms'] for r in success) / len(success)
            print(f"  平均辨識時間: {avg_time:.1f}ms")
            print(f"\n  辨識結果樣本 (前10筆):")
            for r in success[:10]:
                print(f"    {r['index']:3d}. {r['result']} ({r['time_ms']}ms)")

        if failed:
            print(f"\n  錯誤樣本:")
            for r in failed[:5]:
                print(f"    {r['index']:3d}. {r.get('error', '')}")
        print(f"{'='*60}")
        print(f"\n圖片已儲存至: {self.output_dir.resolve()}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BSR Captcha OCR 測試")
    parser.add_argument("--count", type=int, default=30, help="測試次數")
    args = parser.parse_args()

    tester = BsrCaptchaTester()
    tester.batch_test(count=args.count)
