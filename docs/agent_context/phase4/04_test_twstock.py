"""
Phase 4 - twstock SDK 測試腳本

功能:
  1. 安裝 twstock
  2. 測試基本功能 (股價抓取)
  3. 檢查 fetcher 內部使用的 API 端點
  4. 確認是否有分點資料相關功能
  5. 評估是否可取代 BrokerBreakdownSpider

用法:
  pip install twstock
  python docs/agent_context/phase4/04_test_twstock.py
"""
import sys
import os

# 加入專案根目錄
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def test_twstock_install():
    """確認 twstock 已安裝"""
    print("=== 1. 檢查 twstock 安裝 ===")
    try:
        import twstock
        print(f"✅ twstock 版本: {twstock.__version__ if hasattr(twstock, '__version__') else 'unknown'}")
        return twstock
    except ImportError:
        print("❌ twstock 未安裝，請執行: pip install twstock")
        return None


def test_stock_fetch(twstock):
    """測試基本股價抓取"""
    print("\n=== 2. 測試 Stock 抓取 ===")
    stock = twstock.Stock("2330")
    stock.fetch_31()
    print(f"✅ 2330 近 31 日資料: {len(stock.data)} 筆")
    if stock.data:
        print(f"   最新: {stock.data[-1]}")
    return stock


def test_fetcher_api(twstock, stock):
    """檢查 fetcher 內部使用哪個 API"""
    print("\n=== 3. 檢查 Fetcher API 端點 ===")
    fetcher = stock.fetcher
    print(f"Fetcher 類型: {type(fetcher).__name__}")
    
    # 檢查底層 URL (可能需要看原始碼)
    if hasattr(fetcher, 'TWSE_URL'):
        print(f"TWSE URL: {fetcher.TWSE_URL}")
    if hasattr(fetcher, 'url'):
        print(f"URL: {fetcher.url}")
    
    # 列出 fetcher 的所有方法
    methods = [m for m in dir(fetcher) if not m.startswith('_')]
    print(f"可用方法: {methods}")
    
    # 檢查是否有分點相關方法
    broker_methods = [m for m in methods if 'broker' in m.lower() or 'deal' in m.lower() or 'trader' in m.lower()]
    if broker_methods:
        print(f"✅ 分點相關方法: {broker_methods}")
    else:
        print("❌ 無分點相關方法")


def test_realtime(twstock):
    """測試即時報價"""
    print("\n=== 4. 測試即時報價 ===")
    try:
        data = twstock.realtime.get("2330")
        if data.get("success"):
            info = data.get("info", {})
            print(f"✅ {info.get('name')} ({info.get('code')}): {info.get('time')}")
            realtime = data.get("realtime", {})
            print(f"   最新成交: {realtime.get('latest_trade_price')}")
            print(f"   累積成交量: {realtime.get('accumulate_trade_volume')}")
        else:
            print(f"❌ 即時報價失敗: {data}")
    except Exception as e:
        print(f"❌ 即時報價錯誤: {e}")


def test_best_four_point(twstock):
    """測試四大買賣點分析"""
    print("\n=== 5. 測試 BestFourPoint ===")
    from twstock.analytics import BestFourPoint
    
    stock = twstock.Stock("2330")
    stock.fetch_31()
    
    bfp = BestFourPoint(stock)
    result = bfp.best_four_point()
    if result:
        print(f"✅ 買賣建議: {result}")
    else:
        print("ℹ️  無明確買賣點")


def main():
    print("=" * 60)
    print("Phase 4 - twstock SDK 測試")
    print("=" * 60)
    
    twstock = test_twstock_install()
    if not twstock:
        return
    
    stock = test_stock_fetch(twstock)
    test_fetcher_api(twstock, stock)
    test_realtime(twstock)
    test_best_four_point(twstock)
    
    print("\n" + "=" * 60)
    print("結論:")
    print("  twstock 主要提供: 歷史股價、即時報價、技術分析")
    print("  分點買賣超資料: 需要進一步確認原始碼")
    print("=" * 60)


if __name__ == "__main__":
    main()
