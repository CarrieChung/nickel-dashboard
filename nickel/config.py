import os

METALS_DEV_API_URL = "https://api.metals.dev/v1/latest"

CURRENCY = "USD"
UNIT = "mt"
CACHE_TTL_SECONDS = 300
DB_PATH = os.environ.get("NICKEL_DB_PATH", "nickel.db")
STORE_PATH = os.environ.get("NICKEL_STORE_PATH", "nickel-store.json")
PREDICT_DAYS = 30

SHEET_ID = "1yebIFXkp7VdLkMstmtlY5hKTOqeWxs50RuU8yJ2yMdw"
SHEET_TAB = "1"
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1yebIFXkp7VdLkMstmtlY5hKTOqeWxs50RuU8yJ2yMdw/export?format=csv"
SHEET_PROXY = "https://opensheet.elk.sh"
NEWS_QUERY = "nickel price LME"
NEWS_MAX = 6
NEWS_CACHE_SECONDS = 1800

FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
FRED_SERIES_ANNUAL = "PNICKUSDA"
FRED_SERIES_MONTHLY = "PNICKUSDM"
FRED_CACHE_SECONDS = 86400
FRED_RECENT_MONTHS = 14
