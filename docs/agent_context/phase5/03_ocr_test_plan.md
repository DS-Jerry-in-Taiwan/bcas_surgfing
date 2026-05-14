# Phase 5 — ddddocr 辨識率測試計畫

---

## 1. 測試目標

| 目標 | 說明 |
|------|------|
| T1 | 確認 ddddocr 可成功安裝並執行推論 |
| T2 | 驗證 BSR Captcha 的下載流程 (ASP.NET Session) |
| T3 | 統計 ddddocr 對 BSR Captcha 的辨識成功率 |
| T4 | 測試重試機制對累計成功率的提升效果 |
| T5 | 測量端到端耗時 (從 GET page 到 OCR 完成) |

---

## 2. BSR Captcha 特徵

| 屬性 | 值 |
|------|-----|
| 來源 | `https://bsr.twse.com.tw/bshtm/CaptchaImage.aspx?guid={UUID}` |
| 圖片尺寸 | 200 × 60 px |
| 格式 | PNG |
| 字元長度 | 5 碼 |
| 字元集 | 大寫字母 A-Z + 數字 0-9 (推測排除 O/0, I/1 等易混淆) |
| 干擾 | 背景噪點、線條干擾、字元扭曲 (ASP.NET 典型 Captcha) |
| GUID 更新 | 每次 GET bsMenu.aspx 產生新的 GUID |

**BSR 驗證碼範例結構** (由 HTML 擷取):
```html
<img src='CaptchaImage.aspx?guid=70edbdfe-7f8d-4bc5-a922-a1e4dc44cd47'
     border='0' width=200 height=60>
```

---

## 3. 測試腳本設計

### 3.1 腳本位置

```
research/backtests/ocr_test/
├── test_bsr_captcha.py    # 主測試腳本
├── analyze_results.py      # 結果分析腳本
├── samples/                # 下載的 captcha 圖片 (gitignored)
│   ├── 0001.png
│   ├── 0002.png
│   └── ...
└── results.csv             # 辨識結果統計
```

### 3.2 test_bsr_captcha.py 詳細設計

```python
#!/usr/bin/env python3
"""
BSR Captcha 辨識率測試腳本

流程:
1. 建立 requests.Session
2. GET bsMenu.aspx → 解析 VIEWSTATE + captcha GUID
3. GET CaptchaImage.aspx?guid=XXX → 下載 PNG
4. ddddocr 辨識 → 記錄結果
5. 重複 100+ 次

用法:
    python research/backtests/ocr_test/test_bsr_captcha.py --count 100 --delay 3
"""

import argparse
import csv
import hashlib
import os
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# 加入專案根目錄
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
))


def download_captcha(session: requests.Session) -> tuple:
    """
    下載一張 BSR Captcha 圖片
    
    Returns:
        (image_bytes: bytes, guid: str, viewstate: str, html: str)
        若失敗任一環節則回傳 None
    """
    BASE = "https://bsr.twse.com.tw/bshtm/"
    
    # Step 1: GET bsMenu.aspx
    resp = session.get(BASE + "bsMenu.aspx", timeout=15)
    resp.raise_for_status()
    html = resp.text
    
    # Step 2: 解析 VIEWSTATE
    soup = BeautifulSoup(html, "lxml")
    viewstate = soup.find("input", {"name": "__VIEWSTATE"})
    if not viewstate:
        return None
    viewstate = viewstate.get("value", "")
    
    # Step 3: 提取 Captcha GUID
    img_tag = soup.find("img", {"src": lambda x: x and "CaptchaImage.aspx" in x})
    if not img_tag:
        return None
    src = img_tag.get("src", "")
    guid = src.split("guid=")[-1] if "guid=" in src else None
    if not guid:
        return None
    
    # Step 4: 下載 Captcha 圖片
    img_resp = session.get(BASE + src, timeout=15)
    img_resp.raise_for_status()
    image_bytes = img_resp.content
    
    return (image_bytes, guid, viewstate, html)


def save_sample(image_bytes: bytes, index: int, samples_dir: Path) -> str:
    """儲存 captcha 圖片到 samples 目錄"""
    samples_dir.mkdir(parents=True, exist_ok=True)
    # 使用 hash 避免重複儲存
    img_hash = hashlib.md5(image_bytes).hexdigest()[:8]
    filename = f"{index:04d}_{img_hash}.png"
    filepath = samples_dir / filename
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    return str(filepath)


def main():
    parser = argparse.ArgumentParser(description="BSR Captcha OCR 測試")
    parser.add_argument("--count", type=int, default=100,
                       help="測試次數 (預設: 100)")
    parser.add_argument("--delay", type=float, default=3.0,
                       help="每次請求間隔秒數 (預設: 3s)")
    parser.add_argument("--output", type=str, default="results.csv",
                       help="結果 CSV 路徑 (預設: results.csv)")
    args = parser.parse_args()
    
    # 初始化
    from src.spiders.ocr_solver import OcrSolver
    ocr = OcrSolver()
    
    samples_dir = Path(__file__).parent / "samples"
    results_path = Path(__file__).parent / args.output
    
    # 結果列表
    results = []
    
    print(f"BSR Captcha OCR 測試")
    print(f"  總次數: {args.count}")
    print(f"  間隔: {args.delay}s")
    print(f"  輸出: {results_path}")
    print(f"  樣本: {samples_dir}")
    print()
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
    })
    
    success_count = 0
    total_time = 0.0
    
    for i in range(1, args.count + 1):
        start_time = time.time()
        
        try:
            # 下載 Captcha
            captcha_data = download_captcha(session)
            
            if captcha_data is None:
                print(f"  [{i:3d}/{args.count}] ❌ 下載失敗 (無法解析頁面)")
                results.append({
                    "index": i,
                    "success": False,
                    "error": "download_failed",
                    "ocr_result": "",
                    "duration_ms": 0,
                    "filepath": "",
                })
                continue
            
            image_bytes, guid, viewstate, html = captcha_data
            
            # OCR 辨識
            ocr_result = ocr.solve(image_bytes)
            duration_ms = (time.time() - start_time) * 1000
            
            # 儲存樣本
            filepath = save_sample(image_bytes, i, samples_dir)
            
            # 基本驗證: 結果應為 5 碼字母數字
            is_valid = (
                len(ocr_result) == 5
                and ocr_result.isalnum()
            )
            
            if is_valid:
                success_count += 1
                total_time += duration_ms
                status = "✅"
            else:
                status = "⚠️"
            
            print(f"  [{i:3d}/{args.count}] {status} OCR={ocr_result:5s} "
                  f"({duration_ms:.0f}ms) len={len(ocr_result)}")
            
            results.append({
                "index": i,
                "success": is_valid,
                "error": "" if is_valid else f"invalid_length_{len(ocr_result)}",
                "ocr_result": ocr_result,
                "duration_ms": round(duration_ms, 1),
                "filepath": filepath,
                "guid": guid,
            })
            
        except requests.exceptions.RequestException as e:
            print(f"  [{i:3d}/{args.count}] ❌ 網路錯誤: {e}")
            results.append({
                "index": i,
                "success": False,
                "error": f"network_error: {e}",
                "ocr_result": "",
                "duration_ms": 0,
                "filepath": "",
            })
        except Exception as e:
            print(f"  [{i:3d}/{args.count}] ❌ 未知錯誤: {e}")
            results.append({
                "index": i,
                "success": False,
                "error": f"unknown: {e}",
                "ocr_result": "",
                "duration_ms": 0,
                "filepath": "",
            })
        
        # 請求間隔
        if i < args.count:
            time.sleep(args.delay)
    
    # 寫入 CSV
    with open(results_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["index", "success", "error", "ocr_result",
                     "duration_ms", "filepath", "guid"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    # 顯示統計
    rate = success_count / args.count * 100
    avg_time = total_time / success_count if success_count > 0 else 0
    
    print()
    print("=" * 60)
    print("測試結果摘要")
    print("=" * 60)
    print(f"  總次數:        {args.count}")
    print(f"  ✅ 成功 (5碼):  {success_count} ({rate:.1f}%)")
    print(f"  ❌ 失敗:        {args.count - success_count} ({100-rate:.1f}%)")
    if success_count > 0:
        print(f"  平均 OCR 耗時: {avg_time:.0f}ms")
    print(f"  結果已儲存至:  {results_path}")
    print(f"  樣本已儲存至:  {samples_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

### 3.3 analyze_results.py 設計

```python
#!/usr/bin/env python3
"""
分析 OCR 測試結果

功能:
- 載入 results.csv
- 統計各項指標
- 分析錯誤類型
- 生成簡易報表
"""
import csv
import sys
from pathlib import Path
from collections import Counter


def analyze(csv_path: str, samples_dir: str):
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    total = len(rows)
    successes = [r for r in rows if r["success"] == "True"]
    failures = [r for r in rows if r["success"] != "True"]
    
    # 錯誤類型統計
    error_types = Counter(r.get("error", "unknown") for r in failures)
    
    # OCR 結果長度統計
    length_dist = Counter(len(r["ocr_result"]) for r in rows if r["ocr_result"])
    
    # 耗時統計
    durations = [float(r["duration_ms"]) for r in successes if r["duration_ms"]]
    
    print("=" * 60)
    print("OCR 測試分析報告")
    print("=" * 60)
    print(f"  總樣本數:      {total}")
    print(f"  ✅ 正確:       {len(successes)} ({len(successes)/total*100:.1f}%)")
    print(f"  ❌ 錯誤:       {len(failures)} ({len(failures)/total*100:.1f}%)")
    print()
    
    if durations:
        print(f"  平均耗時:      {sum(durations)/len(durations):.0f}ms")
        print(f"  最慢:          {max(durations):.0f}ms")
        print(f"  最快:          {min(durations):.0f}ms")
        print(f"  P95:           {sorted(durations)[int(len(durations)*0.95)]:.0f}ms")
    print()
    
    print("錯誤類型分布:")
    for err, count in error_types.most_common():
        print(f"  {err}: {count} ({count/total*100:.1f}%)")
    print()
    
    print("辨識結果長度分布:")
    for length, count in sorted(length_dist.items()):
        bar = "#" * count
        print(f"  {length} 碼: {count} ({count/total*100:.1f}%) {bar}")
```

---

## 4. 測試執行計畫

### 4.1 預備步驟

```bash
# 1. 安裝相依套件
pip install ddddocr Pillow requests beautifulsoup4 lxml

# 2. 建立測試目錄
mkdir -p research/backtests/ocr_test/samples

# 3. 確認 BSR 網站可連線
curl -I https://bsr.twse.com.tw/bshtm/bsMenu.aspx
```

### 4.2 執行測試

```bash
# 第一次測試: 100 次，間隔 3 秒
python research/backtests/ocr_test/test_bsr_captcha.py \
    --count 100 --delay 3

# 分析結果
python research/backtests/ocr_test/analyze_results.py
```

### 4.3 人工驗證

1. 從 `samples/` 目錄隨機選取 20 張圖片
2. 人工辨識每張圖片的驗證碼
3. 與 `results.csv` 中的 `ocr_result` 比對
4. 計算人工驗證正確率

---

## 5. 成功標準

### 5.1 初次辨識 (1st-attempt)

| 指標 | 目標 | 說明 |
|------|------|------|
| 基本格式正確率 | ≥ 90% | OCR 輸出為 5 碼字母數字 |
| 字元正確率 | ≥ 80% | 人工驗證中整串完全正確的比例 |
| 平均辨識耗時 | < 500ms | 包含 ddddocr 推論時間 |

### 5.2 重試後累計成功率

| 重試次數 | 預期累計成功率 | 計算方式 |
|---------|---------------|---------|
| 1 次 (無重試) | 80% | 基礎辨識率 |
| 2 次 (1 次重試) | 96% | 1 - (0.2)² |
| 3 次 (2 次重試) | 99.2% | 1 - (0.2)³ |
| 5 次 (4 次重試) | 99.97% | 1 - (0.2)⁵ |

> 假設 base rate = 80% 且每次嘗試獨立 (實際上 BSR captcha 每次不同)

---

## 6. 決策閘 (Decision Gate)

在完成階段 1 後，根據以下結果決定路徑：

| 辨識率 | 行動方案 |
|--------|---------|
| ≥ 85% | 📗 **綠燈**: 標準方案。3 次重試可達 > 99.7% 成功率 |
| 70% ~ 85% | 📙 **黃燈**: 增加重試至 5 次。加入 response time 監控 |
| 50% ~ 70% | 📕 **橙燈**: 需要預處理 (去噪、二值化) + 至少 5 次重試 |
| < 50% | 🚫 **紅燈**: ddddocr 不適用。需評估其他方案 |

### 降級方案

若辨識率不足，考慮以下改善措施：

| 方案 | 預期改善 | 實作成本 |
|------|---------|---------|
| A. 圖片預處理 (去噪/二值化/銳化) | +5~15% | 低 (OpenCV) |
| B. ddddocr 參數調整 (ONNX 模型選擇) | +5~10% | 低 |
| C. 多模型投票 (ddddocr × 2~3 次 OCR) | +2~5% | 中 |
| D. 訓練自定義模型 | +20~50% | 高 (需要大量標註資料) |
| E. 人工驗證碼隊列 | 100% | 高 (需要 UI 介面) |

---

## 7. 附錄: BSR 驗證碼範例圖片

(此區域將在實際測試後填入樣本截圖)

```
測試日期: 2026-05-13
樣本數量: 100
首次辨識率: ___%
平均耗時: ___ms
最終結論: ✅ / ⚠️ / ❌
```
