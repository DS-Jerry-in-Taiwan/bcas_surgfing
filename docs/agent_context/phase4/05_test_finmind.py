"""
Phase 4 - FinMind API 測試腳本

功能:
  1. 測試 FinMind TaiwanStockBrokerBuysell 端點
  2. 確認回傳資料格式
  3. 評估是否可取代 TWSE MI_20S

用法:
  # 先在 https://finmindtrade.com 註冊取得 Token
  export FINMIND_TOKEN="your_token_here"
  python docs/agent_context/phase4/05_test_finmind.py
"""
import os
import sys
import json
import requests

API_BASE = "https://finmindtrade.com/api/v4/data"


def test_connection():
    """測試 API 連線"""
    print("=== 1. 測試 API 連線 ===")
    token = os.getenv("FINMIND_TOKEN")
    if not token:
        print("⚠️  FINMIND_TOKEN 未設定")
        print("   請先註冊 https://finmindtrade.com 取得 Token")
        print("   設定: export FINMIND_TOKEN='your_token'")
        return None
    print(f"✅ Token 已設定: {token[:8]}...")
    return token


def test_broker_buysell(token):
    """測試券商買賣超端點"""
    print("\n=== 2. 測試 TaiwanStockBrokerBuysell ===")
    
    params = {
        "dataset": "TaiwanStockBrokerBuysell",
        "data_id": "2330",
        "start_date": "2026-05-01",
        "end_date": "2026-05-13",
        "token": token,
    }
    
    try:
        resp = requests.get(API_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status") == "success" or data.get("data"):
            records = data.get("data", [])
            print(f"✅ 取得成功: {len(records)} 筆")
            if records:
                print(f"   第一筆: {json.dumps(records[0], ensure_ascii=False, indent=2)}")
            return records
        else:
            print(f"❌ API 回傳錯誤: {data}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 請求失敗: {e}")
        return None


def test_other_datasets(token):
    """測試其他相關資料集"""
    print("\n=== 3. 測試其他相關資料集 ===")
    
    datasets = [
        "TaiwanStockInfo",
        "TaiwanStockPrice",
    ]
    
    for ds in datasets:
        params = {
            "dataset": ds,
            "data_id": "2330",
            "start_date": "2026-05-01",
            "end_date": "2026-05-13",
            "token": token,
        }
        try:
            resp = requests.get(API_BASE, params=params, timeout=15)
            data = resp.json()
            records = data.get("data", [])
            print(f"  {ds}: {len(records)} 筆 {'✅' if records else '⚠️ 空'}")
        except Exception as e:
            print(f"  {ds}: ❌ {e}")


def compare_with_broker_breakdown_item(records):
    """比對回傳格式與 BrokerBreakdownItem 的相容性"""
    print("\n=== 4. 資料格式相容性檢查 ===")
    
    if not records:
        print("❌ 無資料可比對")
        return
    
    # BrokerBreakdownItem 欄位
    required_fields = ["date", "symbol", "broker_id", "broker_name", 
                       "buy_volume", "sell_volume", "net_volume"]
    
    sample = records[0]
    print(f"FinMind 回傳欄位: {list(sample.keys())}")
    
    mapping = {
        "date": ["date", "Date", "trade_date", "TradeDate"],
        "symbol": ["stock_id", "StockID", "symbol", "Symbol", "data_id"],
        "broker_id": ["broker_id", "BrokerID"],
        "broker_name": ["broker_name", "BrokerName"],
        "buy_volume": ["buy_volume", "BuyVolume"],
        "sell_volume": ["sell_volume", "SellVolume"],
        "net_volume": ["net_volume", "NetVolume"],
    }
    
    print("\n欄位對應:")
    for target, candidates in mapping.items():
        found = None
        for c in candidates:
            if c in sample:
                found = c
                break
        status = f"✅ {found}" if found else "❌ 無對應"
        print(f"  {target:15s} → {status}")


def main():
    print("=" * 60)
    print("Phase 4 - FinMind API 測試")
    print("=" * 60)
    
    token = test_connection()
    if not token:
        return
    
    records = test_broker_buysell(token)
    test_other_datasets(token)
    
    if records:
        compare_with_broker_breakdown_item(records)
    
    print("\n" + "=" * 60)
    print("結論:")
    if records:
        print("  ✅ FinMind 有提供分點買賣超資料")
        print("  下一步: 確認免費方案限制與整合進 BrokerBreakdownSpider")
    else:
        print("  ❌ 需確認 API Token 或資料集名稱是否正確")
    print("=" * 60)


if __name__ == "__main__":
    main()
