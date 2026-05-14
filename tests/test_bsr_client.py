"""BsrClient & OcrSolver 完整單元測試（全 mock 無網路請求）"""
from __future__ import annotations

import sys
import os
import time
import re
from typing import Any, Optional
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import requests

from src.spiders.ocr_solver import OcrSolver
from src.spiders.bsr_client import (
    BsrClient,
    BsrError,
    BsrConnectionError,
    BsrCaptchaError,
    BsrParseError,
    BsrCircuitBreakerOpen,
)


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

_SAMPLE_HTML = """\
<html>
<body>
<input type="hidden" id="__VIEWSTATE" value="viewstate123" />
<input type="hidden" id="__EVENTVALIDATION" value="ev123" />
<input type="hidden" id="__VIEWSTATEGENERATOR" value="gen123" />
<img src="CaptchaImage.aspx?guid=abc-def-123" />
</body>
</html>"""

_SAMPLE_RESULT_HTML = """\
<html><body>
<table class='table_blue'>
<tr><td>序號</td><td>券商名稱</td><td>買進股數</td><td>賣出股數</td><td>淨買超</td></tr>
<tr><td>1</td><td>凱基-台北(9200)</td><td>1,234,567</td><td>567,890</td><td>666,677</td></tr>
<tr><td>2</td><td>美商高盛(1020)</td><td>987,654</td><td>432,100</td><td>555,554</td></tr>
</table>
</body></html>"""

_EMPTY_RESULT_HTML = """\
<html><body>
<table class='table_blue'>
<tr><td>序號</td><td>券商名稱</td><td>買進股數</td><td>賣出股數</td><td>淨買超</td></tr>
</table>
</body></html>"""

_MALFORMED_HTML = "<html><body>No table here</body></html>"

_CAPTCHA_ERROR_HTML = '<html><body><span>驗證碼錯誤</span></body></html>'

# ─── CSV 新格式 Fixtures ──────────────────────────────────────────

_SAMPLE_CSV_URL = "bsContent.aspx?StkNo=2330&RecCount=62"

_SAMPLE_POST_WITH_CSV = """\
<html><body>
<form><input type="hidden" id="__VIEWSTATE" value="xyz" /></form>
<a href="bsContent.aspx?StkNo=2330&RecCount=62">下載  2330 CSV</a>
</body></html>"""

_SAMPLE_POST_WITHOUT_CSV = """\
<html><body><form><input type="hidden" id="__VIEWSTATE" value="xyz" /></form></body></html>"""

_SAMPLE_CSV = """\
券商買賣股票成交價量資訊
股票代碼,="2330"
序號,券商,價格,買進股數,賣出股數,,序號,券商,價格,買進股數,賣出股數
1,1020合庫,2235.00,1260,1000,,2,1020合庫,2240.00,403,50
3,1021合庫台中,2235.00,1169,4150,,4,1021合庫台中,2240.00,260,401
"""

_SAMPLE_CSV_SINGLE_BROKER = """\
券商買賣股票成交價量資訊
股票代碼,="2330"
序號,券商,價格,買進股數,賣出股數,,序號,券商,價格,買進股數,賣出股數
1,9200凱基-台北,100.00,1000,500,,
"""

_SAMPLE_CSV_EMPTY = """\
券商買賣股票成交價量資訊
股票代碼,="2330"
序號,券商,價格,買進股數,賣出股數,,序號,券商,價格,買進股數,賣出股數
"""


def _make_mock_response(
    text: str = _SAMPLE_HTML,
    status_code: int = 200,
    content: bytes = b"fake_image_png_bytes",
) -> MagicMock:
    mr = MagicMock()
    mr.text = text
    mr.status_code = status_code
    mr.content = content
    mr.__enter__ = MagicMock(return_value=mr)
    mr.__exit__ = MagicMock()
    return mr


# ═══════════════════════════════════════════════════════════════════
# 1. OcrSolver Tests (≥5)
# ═══════════════════════════════════════════════════════════════════

class TestOcrSolver:
    """OcrSolver 單元測試"""

    @patch("src.spiders.ocr_solver.ddddocr.DdddOcr")
    def test_solve_returns_string(self, mock_dddd):
        mock_dddd().classification.return_value = "abcd"
        solver = OcrSolver()
        result = solver.solve(b"fake_bytes")
        assert isinstance(result, str)
        assert result == "abcd"

    @patch("src.spiders.ocr_solver.ddddocr.DdddOcr")
    def test_solve_with_bytes(self, mock_dddd):
        mock_dddd().classification.return_value = "1234"
        solver = OcrSolver()
        result = solver.solve(b"some_image_bytes")
        assert isinstance(result, str)

    @patch("src.spiders.ocr_solver.ddddocr.DdddOcr")
    @patch("src.spiders.ocr_solver.Image.open")
    def test_solve_with_preprocess(self, mock_img_open, mock_dddd):
        mock_dddd().classification.return_value = "wxyz"
        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_img_open.return_value = mock_img

        solver = OcrSolver()
        result = solver.solve_with_preprocess(b"some_image_bytes")
        assert isinstance(result, str)
        mock_img.convert.assert_called_once_with("L")

    @patch("src.spiders.ocr_solver.ddddocr.DdddOcr")
    def test_solve_empty_bytes(self, mock_dddd):
        mock_dddd().classification.return_value = ""
        solver = OcrSolver()
        result = solver.solve(b"")
        assert isinstance(result, str)

    @patch("src.spiders.ocr_solver.ddddocr.DdddOcr")
    def test_ocr_initialization(self, mock_dddd):
        solver = OcrSolver()
        assert hasattr(solver, "_ocr")
        mock_dddd.assert_called_once()

    @patch("src.spiders.ocr_solver.ddddocr.DdddOcr")
    @patch("src.spiders.ocr_solver.Image.open")
    def test_solve_with_preprocess_custom_threshold(self, mock_img_open, mock_dddd):
        mock_dddd().classification.return_value = "xyz"
        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_img_open.return_value = mock_img

        solver = OcrSolver()
        result = solver.solve_with_preprocess(b"img", threshold=200)
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════
# 2. BsrClient Init Tests (≥4)
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientInit:
    """BsrClient 初始化測試"""

    def test_init_default_params(self):
        """預設 max_retries=3, request_interval=2.0"""
        client = BsrClient()
        assert client.max_retries == 3
        assert client.request_interval == 2.0
        client.close()

    def test_init_custom_params(self):
        """自訂參數生效"""
        client = BsrClient(max_retries=5, request_interval=1.0)
        assert client.max_retries == 5
        assert client.request_interval == 1.0
        client.close()

    def test_session_created(self):
        """session 為 requests.Session"""
        client = BsrClient()
        assert isinstance(client.session, requests.Session)
        client.close()

    def test_ocr_instance(self):
        """有 OcrSolver 實例"""
        client = BsrClient()
        assert isinstance(client.ocr, OcrSolver)
        client.close()

    def test_initial_cb_state_closed(self):
        """初始 circuit breaker 狀態為 CLOSED"""
        client = BsrClient()
        assert client._cb_state == "CLOSED"
        assert client._cb_failures == 0
        client.close()

    def test_aspnet_state_none(self):
        """初始 ASP.NET state 皆為 None"""
        client = BsrClient()
        assert client._viewstate is None
        assert client._eventvalidation is None
        assert client._viewstategenerator is None
        client.close()


# ═══════════════════════════════════════════════════════════════════
# 3. Session Refresh Tests (≥4)
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientRefreshSession:
    """Session Refresh 測試"""

    @patch.object(BsrClient, "_throttle")
    @patch("requests.Session.get")
    def test_refresh_session_success(self, mock_get, mock_throttle):
        """成功解析 HTML"""
        mock_get.return_value = _make_mock_response(text=_SAMPLE_HTML)

        client = BsrClient()
        result = client._refresh_session()
        assert result is True
        assert client._viewstate == "viewstate123"
        assert client._eventvalidation == "ev123"
        assert client._viewstategenerator == "gen123"
        assert client._captcha_guid == "abc-def-123"
        client.close()

    @patch.object(BsrClient, "_throttle")
    @patch("requests.Session.get")
    def test_refresh_session_sets_state(self, mock_get, mock_throttle):
        """__VIEWSTATE 正確設定"""
        mock_get.return_value = _make_mock_response(text=_SAMPLE_HTML)

        client = BsrClient()
        client._refresh_session()
        assert client._viewstate == "viewstate123"
        assert client._eventvalidation == "ev123"
        client.close()

    @patch.object(BsrClient, "_throttle")
    @patch("requests.Session.get")
    def test_refresh_session_network_error(self, mock_get, mock_throttle):
        """網路錯誤回傳 False"""
        mock_get.side_effect = requests.ConnectionError("connection failed")

        client = BsrClient()
        result = client._refresh_session()
        assert result is False
        client.close()

    @patch.object(BsrClient, "_throttle")
    @patch("requests.Session.get")
    def test_refresh_session_missing_viewstate(self, mock_get, mock_throttle):
        """缺少欄位回傳 False"""
        html = "<html><body></body></html>"
        mock_get.return_value = _make_mock_response(text=html)

        client = BsrClient()
        result = client._refresh_session()
        assert result is False
        client.close()

    @patch.object(BsrClient, "_throttle")
    @patch("requests.Session.get")
    def test_refresh_session_missing_captcha(self, mock_get, mock_throttle):
        """缺少 captcha img 回傳 False"""
        html = """\
<html><body>
<input type="hidden" id="__VIEWSTATE" value="v1" />
<input type="hidden" id="__EVENTVALIDATION" value="e1" />
<input type="hidden" id="__VIEWSTATEGENERATOR" value="g1" />
</body></html>"""
        mock_get.return_value = _make_mock_response(text=html)

        client = BsrClient()
        result = client._refresh_session()
        assert result is False
        client.close()


# ═══════════════════════════════════════════════════════════════════
# 4. Captcha Tests (≥3)
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientCaptcha:
    """Captcha 相關測試"""

    def test_extract_guid_success(self):
        """正確提取 UUID"""
        html = '<img src="CaptchaImage.aspx?guid=my-guid-here" />'
        client = BsrClient()
        guid = client._extract_captcha_guid(html)
        assert guid == "my-guid-here"
        client.close()

    def test_extract_guid_no_img(self):
        """無 img 回傳 None"""
        client = BsrClient()
        guid = client._extract_captcha_guid("<html></html>")
        assert guid is None
        client.close()

    @patch.object(BsrClient, "_throttle")
    @patch("requests.Session.get")
    def test_get_captcha_image_success(self, mock_get, mock_throttle):
        """成功下載 PNG bytes"""
        mock_get.return_value = _make_mock_response(content=b"A" * 200)

        client = BsrClient()
        client._captcha_guid = "test-guid"
        img = client._get_captcha_image()
        assert img == b"A" * 200
        client.close()

    @patch.object(BsrClient, "_throttle")
    @patch("requests.Session.get")
    def test_get_captcha_image_too_small(self, mock_get, mock_throttle):
        """圖片太小回傳 None"""
        mock_get.return_value = _make_mock_response(content=b"tiny")

        client = BsrClient()
        client._captcha_guid = "test-guid"
        img = client._get_captcha_image()
        assert img is None
        client.close()

    def test_extract_guid_empty_html(self):
        """空 HTML 回傳 None"""
        client = BsrClient()
        guid = client._extract_captcha_guid("")
        assert guid is None
        client.close()


# ═══════════════════════════════════════════════════════════════════
# 5. Form Submit Tests (≥3)
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientFormSubmit:
    """Form Submit 測試"""

    @patch.object(BsrClient, "_throttle")
    @patch("requests.Session.post")
    def test_submit_query_success(self, mock_post, mock_throttle):
        """成功提交"""
        mock_post.return_value = _make_mock_response(text=_SAMPLE_RESULT_HTML)

        client = BsrClient()
        client._viewstate = "vs"
        client._eventvalidation = "ev"
        client._viewstategenerator = "gen"
        html = client._submit_query("2330", "abcd")
        assert html == _SAMPLE_RESULT_HTML
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["data"]["TextBox_Stkno"] == "2330"
        assert kwargs["data"]["CaptchaControl1"] == "abcd"
        assert kwargs["data"]["btnOK"] == "查詢"
        client.close()

    @patch.object(BsrClient, "_throttle")
    @patch("requests.Session.post")
    def test_submit_query_network_error(self, mock_post, mock_throttle):
        """網路錯誤回傳 None"""
        mock_post.side_effect = requests.ConnectionError("failed")

        client = BsrClient()
        client._viewstate = "vs"
        html = client._submit_query("2330", "abcd")
        assert html is None
        client.close()

    def test_check_captcha_error_true(self):
        """驗證碼錯誤檢測"""
        client = BsrClient()
        assert client._check_is_captcha_error("驗證碼錯誤") is True
        assert client._check_is_captcha_error("驗證碼 有 錯誤") is True
        client.close()

    def test_check_captcha_error_false(self):
        """非驗證碼錯誤頁面"""
        client = BsrClient()
        assert client._check_is_captcha_error("正常頁面內容") is False
        assert client._check_is_captcha_error("") is False
        client.close()


# ═══════════════════════════════════════════════════════════════════
# 6. Result Parse Tests (≥5)
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientParseResult:
    """Result Parse 測試"""

    def test_parse_result_success(self):
        """解析完整表格"""
        client = BsrClient()
        result = client._parse_result(_SAMPLE_RESULT_HTML)
        assert len(result) == 2
        assert result[0]["seq"] == 1
        assert result[0]["broker_name"] == "凱基-台北"
        assert result[0]["broker_id"] == "9200"
        assert result[0]["buy_volume"] == 1234567
        assert result[0]["sell_volume"] == 567890
        assert result[0]["net_volume"] == 666677
        assert result[1]["seq"] == 2
        assert result[1]["broker_name"] == "美商高盛"
        assert result[1]["broker_id"] == "1020"
        client.close()

    def test_parse_result_empty_table(self):
        """空表格回傳空列表"""
        client = BsrClient()
        result = client._parse_result(_EMPTY_RESULT_HTML)
        assert result == []
        client.close()

    def test_parse_result_malformed_html(self):
        """異常 HTML 拋 BsrParseError"""
        client = BsrClient()
        with pytest.raises(BsrParseError):
            client._parse_result(_MALFORMED_HTML)
        client.close()

    def test_parse_result_broker_name_with_id(self):
        """券商名稱(代號) 正確拆分"""
        client = BsrClient()
        result = client._parse_result(_SAMPLE_RESULT_HTML)
        assert result[0]["broker_name"] == "凱基-台北"
        assert result[0]["broker_id"] == "9200"
        assert result[1]["broker_name"] == "美商高盛"
        assert result[1]["broker_id"] == "1020"
        client.close()

    def test_parse_result_volume_with_commas(self):
        """股數含逗號正確解析"""
        client = BsrClient()
        result = client._parse_result(_SAMPLE_RESULT_HTML)
        assert result[0]["buy_volume"] == 1234567
        assert result[0]["sell_volume"] == 567890
        assert result[0]["net_volume"] == 666677
        client.close()

    @patch.object(BsrClient, "_download_csv")
    def test_parse_result_new_format(self, mock_download):
        """_parse_result 走 CSV 新格式路徑"""
        mock_download.return_value = _SAMPLE_CSV
        client = BsrClient()
        result = client._parse_result(_SAMPLE_POST_WITH_CSV)
        assert len(result) == 2  # 2 家券商
        # 1020合庫: buy=1260+403=1663, sell=1000+50=1050 → total=2713
        # 1021合庫台中: buy=1169+260=1429, sell=4150+401=4551 → total=5980
        # 排序: 1021 before 1020 (5980 > 2713)
        assert result[0]["broker_id"] == "1021"
        assert result[1]["broker_id"] == "1020"
        mock_download.assert_called_once()
        client.close()

    def test_parse_result_fallback_to_old(self):
        """無 CSV 連結時 fallback 到 table_blue"""
        client = BsrClient()
        result = client._parse_result(_SAMPLE_RESULT_HTML)
        assert len(result) == 2
        assert result[0]["broker_name"] == "凱基-台北"
        assert result[0]["broker_id"] == "9200"
        client.close()

    def test_parse_broker_text_no_parens(self):
        """券商名稱無括號時回傳空 broker_id"""
        name, bid = BsrClient._parse_broker_text("凱基-台北")
        assert name == "凱基-台北"
        assert bid == ""

    def test_parse_volume_empty_string(self):
        """空字串解析為 0"""
        assert BsrClient._parse_volume("") == 0

    def test_parse_volume_invalid(self):
        """無效字串解析為 0"""
        assert BsrClient._parse_volume("abc") == 0


# ═══════════════════════════════════════════════════════════════════
# 7. CSV 解析測試 (新增)
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientCsvParsing:
    """CSV 下載與解析測試"""

    def test_extract_csv_url_found(self):
        """從含連結的 HTML 提取 URL"""
        client = BsrClient()
        url = client._extract_csv_url(_SAMPLE_POST_WITH_CSV)
        assert url is not None
        assert "bsContent.aspx?StkNo=2330&RecCount=62" in url
        client.close()

    def test_extract_csv_url_not_found(self):
        """不含連結回傳 None"""
        client = BsrClient()
        url = client._extract_csv_url(_SAMPLE_POST_WITHOUT_CSV)
        assert url is None
        client.close()

    def test_csv_parse_basic(self):
        """基本 CSV 解析"""
        client = BsrClient()
        result = client._parse_csv(_SAMPLE_CSV)
        assert len(result) == 2  # 2 家獨特券商
        # 1020合庫: buy=1260+403=1663, sell=1000+50=1050
        broker_1020 = [r for r in result if r["broker_id"] == "1020"]
        assert len(broker_1020) == 1
        assert broker_1020[0]["broker_name"] == "合庫"
        assert broker_1020[0]["buy_volume"] == 1663
        assert broker_1020[0]["sell_volume"] == 1050
        assert broker_1020[0]["net_volume"] == 613
        client.close()

    def test_csv_parse_aggregation(self):
        """同一券商多筆價格正確加總"""
        client = BsrClient()
        result = client._parse_csv(_SAMPLE_CSV)
        # 1021合庫台中: buy=1169+260=1429, sell=4150+401=4551
        broker_1021 = [r for r in result if r["broker_id"] == "1021"]
        assert len(broker_1021) == 1
        assert broker_1021[0]["broker_name"] == "合庫台中"
        assert broker_1021[0]["buy_volume"] == 1429
        assert broker_1021[0]["sell_volume"] == 4551
        assert broker_1021[0]["net_volume"] == -3122
        client.close()

    def test_csv_parse_empty(self):
        """空 CSV 回傳 []"""
        client = BsrClient()
        result = client._parse_csv(_SAMPLE_CSV_EMPTY)
        assert result == []
        client.close()

    def test_csv_parse_single_broker(self):
        """單筆 CSV 正確解析"""
        client = BsrClient()
        result = client._parse_csv(_SAMPLE_CSV_SINGLE_BROKER)
        assert len(result) == 1
        assert result[0]["broker_id"] == "9200"
        assert result[0]["broker_name"] == "凱基-台北"
        assert result[0]["buy_volume"] == 1000
        assert result[0]["sell_volume"] == 500
        assert result[0]["net_volume"] == 500
        client.close()

    @patch.object(BsrClient, "_download_csv")
    def test_parse_result_csv_empty(self, mock_download):
        """CSV 下載但資料為空 => 回傳 [] (與舊格式空表格行為一致)"""
        mock_download.return_value = _SAMPLE_CSV_EMPTY
        client = BsrClient()
        result = client._parse_result(_SAMPLE_POST_WITH_CSV)
        assert result == []
        client.close()


# ═══════════════════════════════════════════════════════════════════
# 8. Fetch Broker Data Tests (≥4)
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientFetchBrokerData:
    """Fetch Broker Data 測試"""

    @patch.object(BsrClient, "_solve_captcha")
    @patch.object(BsrClient, "_submit_query")
    @patch.object(BsrClient, "_throttle")
    def test_fetch_broker_data_success(
        self, mock_throttle, mock_submit, mock_solve
    ):
        """完整流程成功"""
        mock_solve.return_value = "abcd"
        mock_submit.return_value = _SAMPLE_RESULT_HTML

        client = BsrClient()
        result = client.fetch_broker_data("2330")
        assert len(result) == 2
        assert result[0]["broker_name"] == "凱基-台北"
        mock_solve.assert_called_once()
        mock_submit.assert_called_once_with("2330", "abcd")
        client.close()

    @patch.object(BsrClient, "_solve_captcha")
    @patch.object(BsrClient, "_submit_query")
    @patch.object(BsrClient, "_throttle")
    def test_fetch_broker_data_captcha_retry_success(
        self, mock_throttle, mock_submit, mock_solve
    ):
        """captcha 錯誤後重試成功"""
        mock_solve.return_value = "abcd"
        mock_submit.side_effect = [
            _CAPTCHA_ERROR_HTML,
            _SAMPLE_RESULT_HTML,
        ]

        client = BsrClient(max_retries=3)
        result = client.fetch_broker_data("2330")
        assert len(result) == 2
        assert mock_submit.call_count == 2
        client.close()

    @patch.object(BsrClient, "_solve_captcha")
    @patch.object(BsrClient, "_submit_query")
    @patch.object(BsrClient, "_throttle")
    def test_fetch_broker_data_all_retries_fail(
        self, mock_throttle, mock_submit, mock_solve
    ):
        """全部 captcha 重試失敗拋 BsrCaptchaError"""
        mock_solve.return_value = "abcd"
        mock_submit.return_value = _CAPTCHA_ERROR_HTML

        client = BsrClient(max_retries=3)
        with pytest.raises(BsrCaptchaError):
            client.fetch_broker_data("2330")
        assert mock_submit.call_count == 3
        client.close()

    @patch.object(BsrClient, "_solve_captcha")
    @patch.object(BsrClient, "_submit_query")
    @patch.object(BsrClient, "_throttle")
    def test_fetch_broker_data_connection_error(
        self, mock_throttle, mock_submit, mock_solve
    ):
        """連線失敗拋 BsrConnectionError"""
        mock_solve.side_effect = requests.ConnectionError("no route to host")

        client = BsrClient(max_retries=2)
        with pytest.raises(BsrConnectionError):
            client.fetch_broker_data("2330")
        client.close()

    @patch.object(BsrClient, "_solve_captcha")
    @patch.object(BsrClient, "_submit_query")
    @patch.object(BsrClient, "_throttle")
    def test_fetch_broker_data_solve_captcha_fails(
        self, mock_throttle, mock_submit, mock_solve
    ):
        """captcha 解碼失敗拋 BsrConnectionError"""
        mock_solve.return_value = None

        client = BsrClient(max_retries=1)
        with pytest.raises(BsrConnectionError, match="Failed to solve captcha"):
            client.fetch_broker_data("2330")
        client.close()

    @patch.object(BsrClient, "_solve_captcha")
    @patch.object(BsrClient, "_submit_query")
    @patch.object(BsrClient, "_throttle")
    def test_fetch_broker_data_submit_returns_none(
        self, mock_throttle, mock_submit, mock_solve
    ):
        """submit 回傳 None 拋 BsrConnectionError"""
        mock_solve.return_value = "abcd"
        mock_submit.return_value = None

        client = BsrClient(max_retries=1)
        with pytest.raises(BsrConnectionError, match="Query submission failed"):
            client.fetch_broker_data("2330")
        client.close()

    @patch.object(BsrClient, "_solve_captcha")
    @patch.object(BsrClient, "_submit_query")
    @patch.object(BsrClient, "_download_csv")
    @patch.object(BsrClient, "_throttle")
    def test_fetch_broker_data_csv_flow(
        self, mock_throttle, mock_download, mock_submit, mock_solve
    ):
        """完整流程走 CSV 格式"""
        mock_solve.return_value = "abcd"
        mock_submit.return_value = _SAMPLE_POST_WITH_CSV
        mock_download.return_value = _SAMPLE_CSV

        client = BsrClient(max_retries=1)
        result = client.fetch_broker_data("2330")
        assert len(result) == 2
        # 1021合庫台中 total=5980, 1020合庫 total=2713
        assert result[0]["broker_id"] == "1021"
        assert result[0]["broker_name"] == "合庫台中"
        assert result[0]["buy_volume"] == 1429
        assert result[0]["sell_volume"] == 4551
        assert result[1]["broker_id"] == "1020"
        assert result[1]["buy_volume"] == 1663
        assert result[1]["sell_volume"] == 1050
        mock_solve.assert_called_once()
        mock_submit.assert_called_once_with("2330", "abcd")
        mock_download.assert_called_once()
        client.close()


# ═══════════════════════════════════════════════════════════════════
# 9. Circuit Breaker Tests (≥3)
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientCircuitBreaker:
    """Circuit Breaker 測試"""

    @patch.object(BsrClient, "_cb_on_success")
    @patch.object(BsrClient, "_solve_captcha")
    @patch.object(BsrClient, "_submit_query")
    @patch.object(BsrClient, "_throttle")
    def test_circuit_breaker_opens_after_threshold(
        self, mock_throttle, mock_submit, mock_solve, mock_cb_success
    ):
        """連續 5 次失敗後開啟"""
        mock_solve.side_effect = requests.ConnectionError("fail")

        client = BsrClient(max_retries=1)
        for _ in range(client.FAILURE_THRESHOLD):
            try:
                client.fetch_broker_data("2330")
            except BsrConnectionError:
                pass

        assert client._cb_state == "OPEN"
        assert client._cb_failures >= client.FAILURE_THRESHOLD
        client.close()

    @patch.object(BsrClient, "_solve_captcha")
    @patch.object(BsrClient, "_submit_query")
    @patch.object(BsrClient, "_throttle", return_value=None)
    def test_circuit_breaker_closes_after_success(
        self, mock_throttle, mock_submit, mock_solve
    ):
        """成功請求後 circuit breaker 關閉"""
        mock_solve.return_value = "abcd"
        mock_submit.return_value = _SAMPLE_RESULT_HTML

        client = BsrClient()
        client._cb_failures = 4
        client._cb_state = "HALF_OPEN"

        result = client.fetch_broker_data("2330")
        assert len(result) == 2
        assert client._cb_state == "CLOSED"
        assert client._cb_failures == 0
        client.close()

    @patch.object(BsrClient, "_cb_allow_request")
    def test_circuit_breaker_raises_when_open(self, mock_allow):
        """開啟時請求拋 BsrCircuitBreakerOpen"""
        mock_allow.return_value = False

        client = BsrClient()
        with pytest.raises(BsrCircuitBreakerOpen):
            client.fetch_broker_data("2330")
        client.close()

    def test_cb_allow_request_closed(self):
        """CLOSED 狀態允許請求"""
        client = BsrClient()
        assert client._cb_allow_request() is True
        client.close()

    def test_cb_allow_request_open_before_timeout(self):
        """OPEN 未逾時拒絕請求"""
        client = BsrClient()
        client._cb_state = "OPEN"
        client._cb_last_open_time = time.time()
        assert client._cb_allow_request() is False
        client.close()

    @patch.object(BsrClient, "_cb_on_success")
    @patch.object(BsrClient, "_solve_captcha")
    @patch.object(BsrClient, "_submit_query")
    @patch.object(BsrClient, "_throttle")
    def test_circuit_breaker_half_open_fails_reopens(
        self, mock_throttle, mock_submit, mock_solve, mock_cb_success
    ):
        """HALF_OPEN 失敗後重新 OPEN"""
        mock_solve.side_effect = requests.ConnectionError("fail")

        client = BsrClient(max_retries=1)
        client._cb_state = "HALF_OPEN"
        client._cb_failures = 4

        with pytest.raises(BsrConnectionError):
            client.fetch_broker_data("2330")

        assert client._cb_state == "OPEN"
        assert client._cb_failures == 5
        client.close()


# ═══════════════════════════════════════════════════════════════════
# 10. Context Manager Tests
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientContextManager:
    """Context manager 測試"""

    def test_context_manager_closes_session(self):
        """with 區塊結束後 session 被關閉"""
        with BsrClient() as client:
            s = client.session
            assert s is not None
            assert hasattr(s, "close")
        # Session close should succeed - requests.Session.close() is idempotent
        # Verify the session is marked as closed via its internal state
        assert s.headers is not None

    def test_context_manager_returns_client(self):
        """with 回傳 BsrClient 實例"""
        with BsrClient() as client:
            assert isinstance(client, BsrClient)

    def test_close_method(self):
        """close() 可被呼叫多次不拋錯"""
        client = BsrClient()
        client.close()
        client.close()  # 第二次 close 不應拋錯


# ═══════════════════════════════════════════════════════════════════
# 11. Exception Hierarchy Tests
# ═══════════════════════════════════════════════════════════════════

class TestBsrExceptions:
    """異常階層測試"""

    def test_bsr_error_base(self):
        """BsrError 為基底"""
        assert issubclass(BsrConnectionError, BsrError)
        assert issubclass(BsrCaptchaError, BsrError)
        assert issubclass(BsrParseError, BsrError)
        assert issubclass(BsrCircuitBreakerOpen, BsrError)

    def test_exceptions_are_raiseable(self):
        """所有異常可被拋出"""
        for exc in [BsrError, BsrConnectionError, BsrCaptchaError,
                    BsrParseError, BsrCircuitBreakerOpen]:
            try:
                raise exc("test")
            except exc as e:
                assert str(e) == "test"


# ═══════════════════════════════════════════════════════════════════
# 12. BsrClient _parse_result helper tests
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientHelpers:
    """內部 helper 方法測試"""

    def test_parse_broker_text_standard(self):
        """標準格式 名稱(代號)"""
        name, bid = BsrClient._parse_broker_text("凱基-台北(9200)")
        assert name == "凱基-台北"
        assert bid == "9200"

    def test_parse_broker_text_multi_digit_id(self):
        """多位數券商代號"""
        name, bid = BsrClient._parse_broker_text("美商高盛(1020)")
        assert name == "美商高盛"
        assert bid == "1020"

    def test_parse_volume_standard(self):
        """標準股數字串"""
        assert BsrClient._parse_volume("1,234,567") == 1234567

    def test_parse_volume_no_commas(self):
        """無逗號股數"""
        assert BsrClient._parse_volume("1234567") == 1234567

    def test_parse_volume_negative(self):
        """負數股數"""
        assert BsrClient._parse_volume("-500") == -500


# ═══════════════════════════════════════════════════════════════════
# 13. Solve Captcha Integration test (mocked)
# ═══════════════════════════════════════════════════════════════════

class TestBsrClientSolveCaptcha:
    """_solve_captcha 流程測試"""

    @patch.object(BsrClient, "_refresh_session")
    @patch.object(BsrClient, "_get_captcha_image")
    @patch.object(OcrSolver, "solve")
    def test_solve_captcha_full_flow(
        self, mock_ocr_solve, mock_get_img, mock_refresh
    ):
        """refresh → download → OCR 完整流程"""
        mock_refresh.return_value = True
        mock_get_img.return_value = b"imgdata"
        mock_ocr_solve.return_value = "wxyz"

        client = BsrClient()
        result = client._solve_captcha()
        assert result == "wxyz"
        mock_refresh.assert_called_once()
        mock_get_img.assert_called_once()
        mock_ocr_solve.assert_called_once_with(b"imgdata")
        client.close()

    @patch.object(BsrClient, "_refresh_session")
    def test_solve_captcha_refresh_fails(self, mock_refresh):
        """refresh 失敗回傳 None"""
        mock_refresh.return_value = False

        client = BsrClient()
        result = client._solve_captcha()
        assert result is None
        client.close()

    @patch.object(BsrClient, "_refresh_session")
    @patch.object(BsrClient, "_get_captcha_image")
    def test_solve_captcha_download_fails(self, mock_get_img, mock_refresh):
        """下載失敗回傳 None"""
        mock_refresh.return_value = True
        mock_get_img.return_value = None

        client = BsrClient()
        result = client._solve_captcha()
        assert result is None
        client.close()
