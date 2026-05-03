"""
BCAS Quant Pipeline - Version Information

This module provides version information and release details.
"""

__title__ = "BCAS Quant Data Pipeline"
__description__ = "Comprehensive quantitative data pipeline with spiders, validation, scheduling, and storage"
__version__ = "3.0.0"
__version_info__ = (3, 0, 0)
__status__ = "Production Ready (with operational improvements recommended)"
__author__ = "BCAS Quant Team"
__license__ = "MIT"

# Build metadata
__build_date__ = "2026-05-03"
__git_commit__ = "28d5e4e"
__git_branch__ = "main"

# Components versions
COMPONENT_VERSIONS = {
    "scheduler": "1.0.0",      # Go async scheduler
    "validators": "2.0.0",     # 24 validation rules
    "spiders": "2.0.0",        # 4 Feapder spiders
    "cleaner": "1.0.0",        # Trading calendar & dedup
}

# Production readiness
PRODUCTION_READINESS = {
    "score": 6.25,
    "max_score": 10.0,
    "aspects": {
        "development": {"status": "✅ Complete", "score": 10},
        "testing": {"status": "✅ Comprehensive", "score": 9},
        "deployment": {"status": "✅ Ready", "score": 9},
        "monitoring": {"status": "⚠️  Basic", "score": 5},
        "fault_recovery": {"status": "⚠️  Minimal", "score": 3},
        "security": {"status": "⚠️  Basic", "score": 5},
    }
}

# Release notes
RELEASE_NOTES = {
    "3.0.0": {
        "date": "2026-05-03",
        "status": "Production",
        "highlights": [
            "✅ Complete system architecture documentation (970 lines)",
            "✅ Architecture summary quick reference (320 lines)",
            "✅ Go async non-blocking scheduler (Cron + Webhook + Channel)",
            "✅ Collect-only spider mode (prevents data pollution)",
            "✅ 24 validation rules across 5 dimensions",
            "✅ TradingCalendar for trading day enrichment",
            "✅ 127 unit tests (92% coverage)",
            "✅ Docker Compose deployment (3 services)",
            "✅ Comprehensive troubleshooting guides",
        ],
        "production_readiness": 6.25,
        "suitable_for": ["Development", "Testing", "Staging", "Non-Critical Production"],
        "known_limitations": [
            "In-memory queue (buffer=1) - no persistence",
            "No automatic fault recovery",
            "Basic monitoring (logs only)",
            "No Kubernetes support yet",
        ],
    },
    "2.0.0": {
        "date": "2026-04-27",
        "status": "Stable",
        "highlights": [
            "Feapder framework migration",
            "4 complete spiders (master + daily)",
            "E2E integration tests (13 test cases)",
            "15 real API test cases",
        ],
    },
    "1.3.0": {
        "date": "2026-04-13",
        "status": "Stable",
        "highlights": [
            "Convertible bond master file pipeline",
            "ETL processing logic",
            "Anti-crawler techniques documentation",
        ],
    },
}

# System requirements
REQUIREMENTS = {
    "python": "3.10+",
    "postgresql": "14+",
    "docker": "20.10+ (optional)",
    "go": "1.21+ (for building scheduler)",
    "memory": "500MB minimum (200-500MB typical)",
    "cpu": "1 core minimum (20-40% typical usage)",
    "disk": "10GB minimum (depends on data volume)",
}

# Architecture metrics
ARCHITECTURE_METRICS = {
    "layers": 3,  # Scheduler -> Pipeline -> Storage
    "spiders": 4,
    "validation_rules": 24,
    "validation_dimensions": 5,
    "storage_tables": 4,
    "code_lines": {
        "python": 8000,
        "go": 400,
        "sql": 500,
        "documentation": 4700,
        "total": 13600,
    },
    "tests": {
        "unit": 127,
        "e2e": 13,
        "coverage": 92,  # percentage
    },
    "performance": {
        "crawler_throughput": "~1000 records/min",
        "validator_throughput": "~1000 records/sec",
        "end_to_end_time": "15-20 minutes",
        "http_latency": "~1ms (non-blocking)",
        "pipeline_startup_latency": "<100ms",
        "docker_image_size": "41.7MB (scheduler)",
    },
}

# CLI modes
CLI_MODES = {
    "normal": {
        "command": "python src/run_daily.py",
        "steps": ["crawl", "validate", "write", "clean"],
        "description": "Full pipeline execution",
    },
    "validate_only": {
        "command": "python src/run_daily.py --validate-only",
        "steps": ["crawl", "validate"],
        "description": "Test data quality without writing to DB",
    },
    "skip_clean": {
        "command": "python src/run_daily.py --skip-clean",
        "steps": ["crawl", "validate", "write"],
        "description": "Skip cleaning step",
    },
    "force_validation": {
        "command": "python src/run_daily.py --force-validation",
        "steps": ["crawl", "validate", "write", "clean"],
        "description": "Write to DB even if validation has errors",
    },
}

def get_version():
    """Get version string."""
    return __version__

def get_version_info():
    """Get version info tuple."""
    return __version_info__

def get_status():
    """Get production readiness status."""
    return __status__

def print_banner():
    """Print version banner."""
    banner = f"""
╔═══════════════════════════════════════════════════════════════╗
║  {__title__:<57} ║
║  Version {__version__:<51} ║
║  Status: {__status__:<46} ║
║  Built: {__build_date__:<52} ║
║  Commit: {__git_commit__:<50} ║
╚═══════════════════════════════════════════════════════════════╝

📊 Production Readiness: {PRODUCTION_READINESS['score']:.2f}/{PRODUCTION_READINESS['max_score']}
   Development:   {PRODUCTION_READINESS['aspects']['development']['status']}
   Testing:       {PRODUCTION_READINESS['aspects']['testing']['status']}
   Deployment:    {PRODUCTION_READINESS['aspects']['deployment']['status']}
   Monitoring:    {PRODUCTION_READINESS['aspects']['monitoring']['status']}
   Fault Recovery: {PRODUCTION_READINESS['aspects']['fault_recovery']['status']}
   Security:      {PRODUCTION_READINESS['aspects']['security']['status']}

📈 System Stats:
   Spiders:       {ARCHITECTURE_METRICS['spiders']}
   Validation Rules: {ARCHITECTURE_METRICS['validation_rules']} ({ARCHITECTURE_METRICS['validation_dimensions']} dimensions)
   Storage Tables: {ARCHITECTURE_METRICS['storage_tables']}
   Unit Tests:    {ARCHITECTURE_METRICS['tests']['unit']} (Coverage: {ARCHITECTURE_METRICS['tests']['coverage']}%)
   Code Lines:    {ARCHITECTURE_METRICS['code_lines']['total']:,}

🚀 Quick Start:
   Development:   pip install -r requirements.txt && python src/run_daily.py
   Docker:        docker-compose up -d
   Health Check:  curl http://localhost:8080/health

📚 Documentation:
   Architecture:  docs/agent_context/phase2_raw_data_validation/SYSTEM_ARCHITECTURE.md
   Summary:       SYSTEM_ARCHITECTURE_SUMMARY.md
   README:        README.md

🔗 See README.md for complete documentation.
"""
    return banner

if __name__ == "__main__":
    print(print_banner())
    print(f"\nVersion: {get_version()}")
    print(f"Status: {get_status()}")
