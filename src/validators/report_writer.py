import json
import os
from datetime import datetime
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class ReportWriter:
    """報告寫入器"""
    
    @staticmethod
    def save_report(report, output_dir: str = "logs/validation/") -> str:
        """
        儲存單份報告到 JSON 檔案
        
        Args:
            report: ValidationReport 物件
            output_dir: 輸出目錄
        
        Returns:
            檔案路徑
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"{timestamp}_{report.table_name}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report saved: {filepath}")
        return filepath
    
    @staticmethod
    def save_summary(reports: Dict, output_dir: str = "logs/validation/") -> str:
        """
        儲存彙整報告
        
        Args:
            reports: {table_name: ValidationReport}
            output_dir: 輸出目錄
        
        Returns:
            檔案路徑
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        
        summary = {
            "timestamp": timestamp,
            "tables": {
                table: {
                    "total_rules": report.summary["total_rules"],
                    "passed": report.summary["passed"],
                    "failed": report.summary["failed"],
                    "warnings": report.summary["warnings"],
                    "skipped": report.summary["skipped"],
                    "total_checked": report.summary["total_checked"],
                }
                for table, report in reports.items()
            },
            "overall_pass": all(not r.has_errors() for r in reports.values()),
        }
        
        filepath = os.path.join(output_dir, f"{timestamp}_summary.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Summary saved: {filepath}")
        return filepath
