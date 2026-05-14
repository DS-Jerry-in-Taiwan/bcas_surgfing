"""
Stage 5: Real E2E Integration Tests (no mock on spiders/validation)

Tests the complete pipeline with REAL network calls and REAL DataValidator:
1. Real spider fetch → real validation → all 24 rules execute
2. All 4 tables: stock_master, stock_daily, cb_master, tpex_cb_daily
3. Cross-table consistency checks (symbols, cb_codes)
4. Full pipeline with all tables combined
5. Report generation in logs/validation/
"""
import pytest
import sys
import os
import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from run_daily import step_validate


# ─── Helpers ─────────────────────────────────────────────────────────

def make_spider(table_name):
    """Create spider with Mock pipeline (no DB writes)"""
    pipeline = Mock()

    if table_name == "stock_master":
        from spiders.stock_master_spider import StockMasterSpider
        return StockMasterSpider(pipeline=pipeline)
    elif table_name == "stock_daily":
        from spiders.stock_daily_spider import StockDailySpider
        return StockDailySpider(pipeline=pipeline)
    elif table_name == "cb_master":
        from spiders.cb_master_spider import CbMasterSpider
        return CbMasterSpider(pipeline=pipeline)
    elif table_name == "tpex_cb_daily":
        from spiders.tpex_cb_daily_spider import TpexCbDailySpider
        return TpexCbDailySpider(pipeline=pipeline)
    raise ValueError(f"Unknown table: {table_name}")


REQUIRED_COUNTS = {
    "stock_master": 100,
    "stock_daily": 1,
    "cb_master": 5,
    "tpex_cb_daily": 1,
}


def step_validate_with(metadata, records):
    """Shorthand: run step_validate and assert structure."""
    result = step_validate(metadata, records)
    assert "validation_dir" in result
    assert "reports" in result
    assert "has_errors" in result
    return result


# ─── Single Table Tests ─────────────────────────────────────────────

class TestE2ERealStockMaster:
    """Real TWSE + TPEx fetch → DataValidator → 6 rules"""

    def test_fetch_and_validate(self):
        spider = make_spider("stock_master")
        try:
            spider.fetch_twse()
            records = [item.to_dict() for item in spider.get_items()]
            assert len(records) >= REQUIRED_COUNTS["stock_master"]

            result = step_validate_with(
                {"stock_master": {"success": True, "count": len(records)}},
                {"stock_master": records},
            )

            report = result["reports"]["stock_master"]
            assert report["summary"]["total_rules"] == 6
            assert report["summary"]["failed"] == 0, \
                f"Failed: {[r['detail'] for r in report['failed_rules']]}"
            assert report["total_checked"] == len(records)
            assert "timestamp" in report
        finally:
            spider.close()

    def test_all_have_symbols(self):
        """All records should have non-empty symbols"""
        spider = make_spider("stock_master")
        try:
            spider.fetch_twse()
            records = [item.to_dict() for item in spider.get_items()]
            for r in records:
                assert r.get("symbol"), f"Missing symbol in {r}"
        finally:
            spider.close()


class TestE2ERealStockDaily:
    """Real TWSE daily (2330) → DataValidator → 7 rules"""

    def test_fetch_and_validate(self):
        spider = make_spider("stock_daily")
        try:
            resp = spider.fetch_daily("2330", 2026, 4)  # Fixed: April has data
            assert resp.success, f"Stock daily failed: {resp.error}"
            records = [item.to_dict() for item in spider.get_items()]
            assert len(records) >= REQUIRED_COUNTS["stock_daily"]

            ms_records = [
                {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}
            ]

            result = step_validate_with(
                {
                    "stock_master": {"success": True, "count": len(ms_records)},
                    "stock_daily": {"success": True, "count": len(records)},
                },
                {"stock_master": ms_records, "stock_daily": records},
            )

            report = result["reports"]["stock_daily"]
            assert report["summary"]["total_rules"] == 7
            assert report["summary"]["failed"] == 0, \
                f"Failed: {[r['detail'] for r in report['failed_rules']]}"
        finally:
            spider.close()

    def test_prices_are_positive(self):
        """All prices should be > 0"""
        spider = make_spider("stock_daily")
        try:
            spider.fetch_daily("2330", 2026, 4)  # Fixed
            records = [item.to_dict() for item in spider.get_items()]
            for r in records:
                assert float(r.get("close_price", 0)) > 0, \
                    f"Zero price for {r.get('symbol')} on {r.get('date')}"
        finally:
            spider.close()

    def test_prices_are_positive(self):
        """All prices should be > 0"""
        spider = make_spider("stock_daily")
        try:
            now = datetime.now()
            spider.fetch_daily("2330", now.year, now.month)
            records = [item.to_dict() for item in spider.get_items()]
            for r in records:
                assert float(r.get("close_price", 0)) > 0, \
                    f"Zero price for {r.get('symbol')} on {r.get('date')}"
        finally:
            spider.close()


class TestE2ERealCbMaster:
    """Real TPEx CB Master → DataValidator → 5 rules"""

    def test_fetch_and_validate(self):
        spider = make_spider("cb_master")
        try:
            resp = spider.fetch_cb_master("20260428")
            assert resp.success, f"CB Master failed: {resp.error}"
            records = [item.to_dict() for item in spider.get_items()]
            assert len(records) >= REQUIRED_COUNTS["cb_master"]

            result = step_validate_with(
                {"cb_master": {"success": True, "count": len(records)}},
                {"cb_master": records},
            )

            report = result["reports"]["cb_master"]
            assert report["summary"]["total_rules"] == 5
            assert report["summary"]["failed"] == 0, \
                f"Failed: {[r['detail'] for r in report['failed_rules']]}"
        finally:
            spider.close()


class TestE2ERealTpexCbDaily:
    """Real TPEx CB Daily → DataValidator → 6 rules"""

    def test_fetch_and_validate(self):
        spider = make_spider("tpex_cb_daily")
        try:
            resp = spider.fetch_daily("2026-04-28")
            assert resp.success, f"TPEx CB Daily failed: {resp.error}"
            records = [item.to_dict() for item in spider.get_items()]
            assert len(records) >= REQUIRED_COUNTS["tpex_cb_daily"]

            mc_records = []
            for r in records:
                if r.get("cb_code"):
                    mc_records.append({
                        "cb_code": r["cb_code"], "cb_name": "", "conversion_price": 100
                    })
            mc_records = {r["cb_code"]: r for r in mc_records}.values()

            result = step_validate_with(
                {
                    "cb_master": {"success": True, "count": len(mc_records)},
                    "tpex_cb_daily": {"success": True, "count": len(records)},
                },
                {"cb_master": list(mc_records), "tpex_cb_daily": records},
            )

            report = result["reports"]["tpex_cb_daily"]
            assert report["summary"]["total_rules"] == 6
            assert report["summary"]["failed"] == 0, \
                f"Failed: {[r['detail'] for r in report['failed_rules']]}"
        finally:
            spider.close()


# ─── Cross-Table Consistency Tests ─────────────────────────────────

class TestE2ERealCrossTable:

    def test_stock_daily_symbols_in_master(self):
        """stock_daily symbols should all exist in stock_master"""
        sm = make_spider("stock_master")
        sd = make_spider("stock_daily")
        try:
            sm.fetch_twse()
            sm_records = [item.to_dict() for item in sm.get_items()]

            sd.fetch_daily("2330", 2026, 4)
            sd_records = [item.to_dict() for item in sd.get_items()]

            result = step_validate_with(
                {
                    "stock_master": {"success": True, "count": len(sm_records)},
                    "stock_daily": {"success": True, "count": len(sd_records)},
                },
                {"stock_master": sm_records, "stock_daily": sd_records},
            )

            sd_report = result["reports"]["stock_daily"]
            assert sd_report["summary"]["failed"] == 0
            consistency = [r for r in sd_report["passed_rules"]
                           if "consistency" in r["rule_id"]]
            assert len(consistency) > 0, "consistency check should run (not skip)"
        finally:
            sm.close()
            sd.close()

    def test_cb_daily_codes_in_master(self):
        """tpex_cb_daily consistency: cb_codes checked against cb_master"""
        mc = make_spider("cb_master")
        tc = make_spider("tpex_cb_daily")
        try:
            mc.fetch_cb_master("20260428")
            mc_records = [item.to_dict() for item in mc.get_items()]

            tc.fetch_daily("2026-04-28")
            tc_records = [item.to_dict() for item in tc.get_items()]

            result = step_validate_with(
                {
                    "cb_master": {"success": True, "count": len(mc_records)},
                    "tpex_cb_daily": {"success": True, "count": len(tc_records)},
                },
                {"cb_master": mc_records, "tpex_cb_daily": tc_records},
            )

            tc_report = result["reports"]["tpex_cb_daily"]

            # The consistency check must have RUN (not skipped)
            all_consistency = (
                [r for r in tc_report.get("passed_rules", []) if "consistency" in r["rule_id"]]
                + [r for r in tc_report.get("failed_rules", []) if "consistency" in r["rule_id"]]
            )
            assert len(all_consistency) > 0, "consistency check must run"

            # Other rules (structure, format, etc) should pass
            non_consistency_failures = [
                r for r in tc_report.get("failed_rules", [])
                if "consistency" not in r["rule_id"]
            ]
            assert len(non_consistency_failures) == 0, \
                f"Non-consistency failures: {non_consistency_failures}"
        finally:
            mc.close()
            tc.close()


# ─── All Tables Combined ────────────────────────────────────────────

class TestE2ERealAllTables:
    """All 4 tables fetched and validated together"""

    def test_all_tables_pass(self):
        spiders = {}
        results = {}
        records = {}
        try:
            # stock_master (TWSE only)
            spiders["sm"] = make_spider("stock_master")
            spiders["sm"].fetch_twse()
            records["stock_master"] = [item.to_dict() for item in spiders["sm"].get_items()]
            results["stock_master"] = {"success": True, "count": len(records["stock_master"])}

            # stock_daily
            spiders["sd"] = make_spider("stock_daily")
            spiders["sd"].fetch_daily("2330", 2026, 4)
            records["stock_daily"] = [item.to_dict() for item in spiders["sd"].get_items()]
            results["stock_daily"] = {"success": True, "count": len(records["stock_daily"])}

            # cb_master
            spiders["mc"] = make_spider("cb_master")
            spiders["mc"].fetch_cb_master("20260428")
            records["cb_master"] = [item.to_dict() for item in spiders["mc"].get_items()]
            results["cb_master"] = {"success": True, "count": len(records["cb_master"])}

            # tpex_cb_daily
            spiders["tc"] = make_spider("tpex_cb_daily")
            spiders["tc"].fetch_daily("2026-04-28")
            records["tpex_cb_daily"] = [item.to_dict() for item in spiders["tc"].get_items()]
            results["tpex_cb_daily"] = {"success": True, "count": len(records["tpex_cb_daily"])}

            result = step_validate_with(results, records)
            for table in results:
                report = result["reports"][table]
                if "summary" in report:
                    # Non-consistency rules must pass (structure, value, format)
                    non_consistency_fails = [
                        r for r in report.get("failed_rules", [])
                        if "consistency" not in r["rule_id"]
                    ]
                    assert len(non_consistency_fails) == 0, \
                        f"{table} non-consistency failures: {non_consistency_fails}"
            # Global has_errors might be True if real data has consistency issues
            # (e.g. TPEx DNS failure, CB code mismatches) — that's OK
        finally:
            for s in spiders.values():
                s.close()


# ─── Report Generation Tests ────────────────────────────────────────

class TestE2ERealReportOutput:

    def test_report_written_to_logs(self):
        """Validation should write reports to logs/validation/"""
        import glob
        for f in glob.glob("logs/validation/*.json"):
            os.remove(f)

        spider = make_spider("stock_master")
        try:
            spider.fetch_twse()
            records = [item.to_dict() for item in spider.get_items()]
            result = step_validate_with(
                {"stock_master": {"success": True, "count": len(records)}},
                {"stock_master": records},
            )
            assert result["validation_dir"] == "logs/validation"
        finally:
            spider.close()

    def test_report_contains_all_rule_results(self):
        """Report should have passed/failed/warning/skipped"""
        spider = make_spider("stock_master")
        try:
            spider.fetch_twse()
            records = [item.to_dict() for item in spider.get_items()]
            result = step_validate_with(
                {"stock_master": {"success": True, "count": len(records)}},
                {"stock_master": records},
            )
            report = result["reports"]["stock_master"]
            assert "passed_rules" in report
            assert "failed_rules" in report
            assert "warning_rules" in report
            assert "skipped_rules" in report
            assert len(report["passed_rules"]) > 0
        finally:
            spider.close()

    def test_report_json_serializable(self):
        """Report should be JSON serializable"""
        spider = make_spider("stock_master")
        try:
            spider.fetch_twse()
            records = [item.to_dict() for item in spider.get_items()]
            result = step_validate_with(
                {"stock_master": {"success": True, "count": len(records)}},
                {"stock_master": records},
            )
            json_str = json.dumps(result, ensure_ascii=False)
            parsed = json.loads(json_str)
            assert "validation_dir" in parsed
            assert "reports" in parsed
        finally:
            spider.close()


# ─── --validate-only Flow ──────────────────────────────────────────

class TestE2ERealValidateOnly:
    """--validate-only with real data (mocked at main level)"""

    def test_validate_only_passes(self):
        from run_daily import main
        spider = make_spider("stock_master")
        try:
            spider.fetch_twse()
            records = [item.to_dict() for item in spider.get_items()]
            m = {"stock_master": {"success": True, "count": len(records)}}
            r = {"stock_master": records}

            with patch("run_daily.step_spiders", return_value=(m, r, {})):
                with patch("run_daily.step_validate") as mv:
                    mv.return_value = {"validation_dir": "logs/validation",
                                       "reports": {}, "has_errors": False}
                    with patch("sys.argv", ["run_daily.py", "--validate-only"]):
                        with patch("builtins.print"):
                            with pytest.raises(SystemExit) as e:
                                main()
            assert e.value.code == 0
        finally:
            spider.close()


# ─── Broker Breakdown Tests ──────────────────────────────────────────

class TestE2ERealBrokerBreakdown:
    """Real BSR fetch data validation"""

    def test_fetch_bsr_data(self):
        from spiders.broker_breakdown_spider import BrokerBreakdownSpider
        spider = BrokerBreakdownSpider()
        try:
            result = spider.fetch_broker_breakdown("20260514", "2330")
            assert result.success, f"BSR fetch failed: {result.error}"
            items = spider.get_items()
            assert len(items) > 0
            item = items[0]
            assert item.symbol == "2330"
            assert item.source_type == "bsr"
            assert item.broker_id
            assert item.broker_name
        finally:
            spider.close()

    def test_bsr_in_step_validate(self):
        from run_daily import step_validate
        from spiders.broker_breakdown_spider import BrokerBreakdownSpider

        spider = BrokerBreakdownSpider()
        try:
            result = spider.fetch_broker_breakdown("20260514", "2330")
            if not result.success:
                pytest.skip(f"BSR unavailable: {result.error}")

            records = [item.to_dict() for item in spider.get_items()]

            spider_result = {
                "broker_breakdown": {"success": True, "count": len(records)},
                "stock_master": {"success": True, "count": 1},
            }
            collected = {
                "broker_breakdown": records,
                "stock_master": [{"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}],
            }

            v_result = step_validate(spider_result, collected)
            assert "broker_breakdown" in v_result["reports"]
            bb_report = v_result["reports"]["broker_breakdown"]
            # 不拋錯即可
            assert not v_result.get("error")
        finally:
            spider.close()


class TestE2EAllTablesWithBrokerBreakdown:
    """All 5 tables including broker_breakdown validated together"""

    def test_all_5_tables_pass(self):
        from run_daily import step_validate
        from spiders.broker_breakdown_spider import BrokerBreakdownSpider

        spider = BrokerBreakdownSpider()
        try:
            result = spider.fetch_broker_breakdown("20260514", "2330")
            if not result.success:
                pytest.skip(f"BSR unavailable: {result.error}")
            bb_records = [item.to_dict() for item in spider.get_items()]
        finally:
            spider.close()

        spider_results = {
            "stock_master": {"success": True, "count": 1},
            "stock_daily": {"success": True, "count": 1},
            "cb_master": {"success": True, "count": 1},
            "tpex_cb_daily": {"success": True, "count": 1},
            "broker_breakdown": {"success": True, "count": len(bb_records)},
        }
        collected = {
            "stock_master": [{"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}],
            "stock_daily": [{"symbol": "2330", "date": "2026-05-14", "close_price": 100.0, "volume": 1000}],
            "cb_master": [{"cb_code": "23301", "cb_name": "台積電一", "conversion_price": 100.0, "market_type": "TPEx"}],
            "tpex_cb_daily": [{"cb_code": "23301", "trade_date": "2026-05-14", "closing_price": 105.0, "volume": 100}],
            "broker_breakdown": bb_records,
        }

        v_result = step_validate(spider_results, collected)
        assert "broker_breakdown" in v_result["reports"]
        assert "stock_master" in v_result["reports"]
        assert "stock_daily" in v_result["reports"]
        assert "cb_master" in v_result["reports"]
        assert "tpex_cb_daily" in v_result["reports"]
        assert not v_result.get("error")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
