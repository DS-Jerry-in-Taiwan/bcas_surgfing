.PHONY: all crawl clean import test fulltest

all: fulltest

crawl:
	.venv/bin/python src/main_crawler.py  --task daily --date 2025-12-02

clean:
	.venv/bin/python src/etl/cleaner.py

import:
	.venv/bin/python src/importer.py

test:
	docker exec timescaledb psql -U postgres -d cbas -c "SELECT COUNT(*) FROM cb_daily;"
	docker exec timescaledb psql -U postgres -d cbas -c "SELECT date, symbol, close, volume FROM cb_daily ORDER BY date DESC, symbol LIMIT 10;"

fulltest: crawl clean import test