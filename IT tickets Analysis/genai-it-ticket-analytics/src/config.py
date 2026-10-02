import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")

OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
FIGURES_DIR = os.path.join(OUTPUT_DIR, "figures")
REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")
GENAI_RESULTS_DIR = os.path.join(OUTPUT_DIR, "genai_results")

SQL_DIR = os.path.join(BASE_DIR, "sql")
NOTEBOOKS_DIR = os.path.join(BASE_DIR, "notebooks")
POWERBI_DIR = os.path.join(BASE_DIR, "powerbi")
TESTS_DIR = os.path.join(BASE_DIR, "tests")

for _d in [
    DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR,
    OUTPUT_DIR, FIGURES_DIR, REPORTS_DIR, GENAI_RESULTS_DIR,
    SQL_DIR, NOTEBOOKS_DIR, POWERBI_DIR, TESTS_DIR,
]:
    os.makedirs(_d, exist_ok=True)

RAW_DATA_FILE = os.path.join(RAW_DATA_DIR, "customer_support_tickets.csv")
PROCESSED_DATA_FILE = os.path.join(PROCESSED_DATA_DIR, "cleaned_tickets.csv")
DATA_QUALITY_REPORT = os.path.join(REPORTS_DIR, "data_quality_report.txt")
BUSINESS_INSIGHTS_REPORT = os.path.join(REPORTS_DIR, "business_insights.txt")
FINAL_REPORT = os.path.join(REPORTS_DIR, "final_project_report.txt")
GENAI_OUTPUT_FILE = os.path.join(GENAI_RESULTS_DIR, "genai_ticket_analysis.csv")

GENAI_API_KEY = os.getenv("GENAI_API_KEY", "")
GENAI_MODEL = os.getenv("GENAI_MODEL", "gpt-3.5-turbo")
MAX_TICKETS_FOR_GENAI = int(os.getenv("MAX_TICKETS_FOR_GENAI", "50"))

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "it_tickets_db")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(OUTPUT_DIR, "it_tickets.db"))

RANDOM_STATE = 42
