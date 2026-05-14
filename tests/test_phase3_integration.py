"""Phase 3.0 整合測試"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestRunDailyIntegration:
    """測試 run_daily.py 整合"""

    def test_broker_breakdown_imported(self):
        """step_spiders 匯入 BrokerBreakdownSpider"""
        with open("src/run_daily.py") as f:
            content = f.read()
        assert "BrokerBreakdownSpider" in content

    def test_broker_breakdown_in_step_spiders(self):
        """step_spiders 有 broker_breakdown block"""
        with open("src/run_daily.py") as f:
            content = f.read()
        assert 'table_name="broker_breakdown"' in content
        assert "pipeline=p" in content
        assert "fetch_broker_breakdown" in content

    def test_collect_only_used(self):
        """broker_breakdown block 使用 collect_only"""
        with open("src/run_daily.py") as f:
            content = f.read()
        assert "collect_only" in content

    def test_try_except_pattern(self):
        """broker_breakdown block 使用 try/except 模式"""
        with open("src/run_daily.py") as f:
            content = f.read()
        # 確認 broker_breakdown 區塊有 try/except
        # 找到 Broker Breakdown 區塊
        lines = content.split('\n')
        broker_block_start = None
        for i, line in enumerate(lines):
            if 'Broker Breakdown' in line or 'broker_breakdown' in line and 'import' not in line:
                # Find the block that has table_name="broker_breakdown"
                if 'table_name="broker_breakdown"' in line or i > 0 and 'table_name="broker_breakdown"' in lines[i-1] or i > 0 and 'table_name="broker_breakdown"' in lines[i]:
                    broker_block_start = i
                    break

        # If not found by comment, search for the table assignment
        if broker_block_start is None:
            for i, line in enumerate(lines):
                if 'table_name="broker_breakdown"' in line:
                    broker_block_start = i
                    break

        assert broker_block_start is not None, "Could not find broker_breakdown block"

        # Look for try/except after this point
        block_snippet = '\n'.join(lines[broker_block_start:broker_block_start + 30])
        assert 'try:' in block_snippet, f"broker_breakdown block missing try:\n{block_snippet}"
        assert 'except:' in block_snippet or 'except ' in block_snippet, \
            f"broker_breakdown block missing except:\n{block_snippet}"

    def test_pipeline_imported(self):
        """step_spiders 匯入 PostgresPipeline"""
        with open("src/run_daily.py") as f:
            content = f.read()
        assert "PostgresPipeline" in content

    def test_broker_breakdown_try_except_same_as_others(self):
        """broker_breakdown block 的 try/except 模式與其他 block 一致"""
        with open("src/run_daily.py") as f:
            content = f.read()

        # There should be at least 5 spider blocks (4 existing + 1 new)
        try_blocks = content.count("try:")
        assert try_blocks >= 5, f"Expected at least 5 try blocks, found {try_blocks}"

        # Each spider block has a close() call in its except (except stock_daily)
        close_calls = content.count("s.close()")
        assert close_calls >= 4, f"Expected at least 4 close() calls, found {close_calls}"

        # Verify broker_breakdown specifically has close() in its except block
        # Find the broker_breakdown block and check for s.close() within the next
        # 1000 characters (the except block is ~800 chars after the table name)
        broker_section_start = content.find('table_name="broker_breakdown"')
        assert broker_section_start >= 0, "Could not find broker_breakdown in code"
        broker_section = content[broker_section_start:broker_section_start + 1000]
        assert "s.close()" in broker_section, "broker_breakdown block missing s.close()"
        assert "except:" in broker_section, "broker_breakdown block missing except:"


class TestDbDDLSyntax:
    """測試 SQL DDL 語法"""

    DDL_PATH = "src/db/init_eod_tables.sql"

    def test_has_4_tables(self):
        """DDL 有 4 張表 (不含 security_profile)"""
        with open(self.DDL_PATH) as f:
            content = f.read()
        count = content.count("CREATE TABLE IF NOT EXISTS")
        assert count == 4, f"預期 4 張表，實際 {count}"

    def test_no_security_profile(self):
        """DDL 不含 security_profile"""
        with open(self.DDL_PATH) as f:
            content = f.read()
        assert "security_profile" not in content

    def test_all_tables_have_primary_key(self):
        """每個表都有 PRIMARY KEY"""
        with open(self.DDL_PATH) as f:
            content = f.read()
        tables = content.split("CREATE TABLE")
        for table in tables[1:]:  # 跳過註解
            assert "PRIMARY KEY" in table, f"缺少 PK: {table[:80]}"

    def test_has_indexes(self):
        """DDL 包含 INDEX"""
        with open(self.DDL_PATH) as f:
            content = f.read()
        assert "CREATE INDEX" in content

    def test_broker_blacklist_seed_exists(self):
        """種子 SQL 存在"""
        assert os.path.exists("src/db/seed_broker_blacklist.sql")

    def test_broker_breakdown_table_pk(self):
        """broker_breakdown 表 PK 為 (date, symbol, broker_id)"""
        with open(self.DDL_PATH) as f:
            content = f.read()
        assert "PRIMARY KEY (date, symbol, broker_id)" in content

    def test_daily_analysis_results_table_pk(self):
        """daily_analysis_results 表 PK 為 (date, symbol)"""
        with open(self.DDL_PATH) as f:
            content = f.read()
        assert "PRIMARY KEY (date, symbol)" in content

    def test_trading_signals_table_pk(self):
        """trading_signals 表 PK 為 (date, symbol, signal_type)"""
        with open(self.DDL_PATH) as f:
            content = f.read()
        assert "PRIMARY KEY (date, symbol, signal_type)" in content

    def test_broker_blacklist_table_pk(self):
        """broker_blacklist 表 PK 為 (broker_id)"""
        with open(self.DDL_PATH) as f:
            content = f.read()
        assert "broker_id VARCHAR(16) PRIMARY KEY" in content or \
               "PRIMARY KEY (broker_id)" in content

    def test_has_all_four_tables(self):
        """DDL 包含所有 4 張預期表"""
        with open(self.DDL_PATH) as f:
            content = f.read()
        assert "broker_breakdown" in content
        assert "daily_analysis_results" in content
        assert "trading_signals" in content
        assert "broker_blacklist" in content


class TestBrokerBlacklistSeed:
    """測試 seed_broker_blacklist.sql"""

    def test_seed_has_10_entries(self):
        """種子資料至少有 10 筆"""
        with open("src/db/seed_broker_blacklist.sql") as f:
            content = f.read()
        # Count INSERT INTO VALUES rows
        # The INSERT INTO ... VALUES (...) syntax has entries separated by commas
        # Count the number of parentheses groups with quoted values
        insert_lines = content.strip().split('\n')
        value_entries = [line for line in insert_lines if line.strip().startswith("('")]
        assert len(value_entries) >= 10, f"預期至少 10 筆種子資料，實際 {len(value_entries)}"

    def test_seed_has_on_conflict(self):
        """種子 SQL 使用 ON CONFLICT 處理重複"""
        with open("src/db/seed_broker_blacklist.sql") as f:
            content = f.read()
        assert "ON CONFLICT" in content

    def test_seed_has_categories(self):
        """種子資料包含 DAY_TRADER, SUSPECTED, FLAGGED 分類"""
        with open("src/db/seed_broker_blacklist.sql") as f:
            content = f.read()
        assert "DAY_TRADER" in content
        assert "SUSPECTED" in content
        assert "FLAGGED" in content
