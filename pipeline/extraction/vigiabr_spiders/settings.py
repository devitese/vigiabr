"""Scrapy settings for VigiaBR spiders."""

BOT_NAME = "vigiabr_spiders"
SPIDER_MODULES = ["vigiabr_spiders.spiders"]
NEWSPIDER_MODULE = "vigiabr_spiders.spiders"

# Respect robots.txt
ROBOTSTXT_OBEY = True

# Identify ourselves
USER_AGENT = "VigiaBR/0.1 (+https://github.com/guidevit-dealsmartai/vigiabr)"

# Conservative concurrency — public APIs, be polite
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1.0

# Retry with exponential backoff
RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

# AutoThrottle — adaptive rate limiting
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 30.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Default request headers — most APIs need Accept: application/json
DEFAULT_REQUEST_HEADERS = {
    "Accept": "application/json",
}

# Timeouts
DOWNLOAD_TIMEOUT = 60

# Feed export disabled — we use our own JSONL pipeline
FEEDS = {}

# Item pipelines
ITEM_PIPELINES = {
    "vigiabr_spiders.pipelines.JsonlWriterPipeline": 300,
}

# Downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    "vigiabr_spiders.middlewares.ApiKeyMiddleware": 543,
    "vigiabr_spiders.middlewares.ExponentialBackoffMiddleware": 544,
}

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

# Request fingerprinting
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# ----- API Keys (loaded from environment) -----
# Portal Transparencia: TRANSPARENCIA_API_KEY
# CNJ DataJud: CNJ_DATAJUD_API_KEY
# These are injected by ApiKeyMiddleware from os.environ

# Output base directory (relative to project root)
RAW_OUTPUT_DIR = "../../data/raw"
