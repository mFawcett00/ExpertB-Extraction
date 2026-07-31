from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import os
import re
import glob
import time
import getpass
import logging
from dotenv import load_dotenv
from src.Utils import send_email, limpiar_carpeta, login, descargar_reporte, run_with_retries, get_creds

# CONFIG AND DEFINE VARIABLES
windows_user = getpass.getuser()

load_dotenv()

URL = os.getenv("URL")
#USUARIO = os.getenv("USER")
#PASSWORD = os.getenv("PASSWORD")

DOWNLOAD_PATH = f"C:\\Users\\{windows_user}\\OneDrive - Inchcape\\Finance Transformation - Databricks\\" + os.getenv("download_path")
ARCHIVED_PATH = f"C:\\Users\\{windows_user}\\OneDrive - Inchcape\\Finance Transformation - Databricks\\" + os.getenv("ARCHIVED_PATH")
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
LOG_FOLDER = f"C:\\Users\\{windows_user}\\Downloads"

os.makedirs(DOWNLOAD_PATH, exist_ok=True)
os.makedirs(ARCHIVED_PATH, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

# LOGGING - console handler lives for the whole 24/7 process.
# The FileHandler is created fresh (with a new timestamp) each time main() runs,
# so a 24/7-running process gets a new log file per run instead of writing to
# (or deleting) a single file created once at startup.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()]  # console only at startup
)
logger = logging.getLogger(__name__)


def setup_daily_logger():
    """Attach a fresh FileHandler (new timestamp) for this run, removing any old one."""
    daily_stamp = datetime.now().strftime("%Y%m%d_%H%M")
    log_path = os.path.join(LOG_FOLDER, f"log_{daily_stamp}.log")

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root_logger.removeHandler(handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    root_logger.addHandler(file_handler)

    return log_path


# FILE FRESHNESS CHECK CONFIG
FILE_PATTERN = "Gestiones_Diarias_*.xlsx"
FILENAME_REGEX = re.compile(r"(\d{8})_(\d{4})")

# Daily cutoff time - after this time, run as soon as possible if not already run today
RUN_AFTER_HOUR = 11
RUN_AFTER_MINUTE = 0

# How old a report file can be before it's considered stale (triggers the catch-up safety net)
STALE_FILE_THRESHOLD_HOURS = 24


def get_file_datetime(filepath):
    """Extract the datetime embedded in the filename (YYYYMMDD_HHMM)."""
    filename = os.path.basename(filepath)
    match = FILENAME_REGEX.search(filename)
    if not match:
        logger.warning(f"Could not parse date/hour from filename: {filename}")
        return None

    date_str, time_str = match.groups()
    try:
        return datetime.strptime(date_str + time_str, "%Y%m%d%H%M")
    except ValueError:
        logger.warning(f"Invalid date/hour format in filename: {filename}")
        return None


def get_stale_files(folder_path=DOWNLOAD_PATH, pattern=FILE_PATTERN):
    """Return list of (filepath, age) for files whose embedded timestamp is older than STALE_FILE_THRESHOLD_HOURS."""
    now = datetime.now()
    stale_files = []

    for filepath in glob.glob(os.path.join(folder_path, pattern)):
        file_dt = get_file_datetime(filepath)
        if file_dt is None:
            continue

        age = now - file_dt
        if age > timedelta(hours=STALE_FILE_THRESHOLD_HOURS):
            stale_files.append((filepath, age))

    return stale_files


def has_todays_file(folder_path=DOWNLOAD_PATH, pattern=FILE_PATTERN):
    """Return True if a report file dated today (by its embedded timestamp) already exists.
    Used so a restart mid-day doesn't trigger a redundant re-download when today's
    report was already produced by an earlier process instance."""
    today_str = datetime.now().strftime("%Y%m%d")

    for filepath in glob.glob(os.path.join(folder_path, pattern)):
        file_dt = get_file_datetime(filepath)
        if file_dt and file_dt.strftime("%Y%m%d") == today_str:
            return True

    return False


# MAIN
def main():
    # Fresh log file + FileHandler for this run (fixes log file being deleted
    # / stale timestamp when the script stays alive across multiple days)
    log_path = setup_daily_logger()
    today = datetime.now().strftime("%Y%m%d_%H%M")

    attempts = 1
    last_error = None
    logger.info(f"Corriendo bot en el usuario {windows_user}")
    USUARIO, PASSWORD = get_creds(logger)

    while attempts < 4:
        try:
            logger.info(f"Intento #{attempts}")
            with sync_playwright() as p:
                logger.info(f"Playwright conectado")
                browser = p.chromium.launch(
                    executable_path=CHROME_PATH,
                    headless=False
                )
                logger.info(f"Chrome conectado")
                context = browser.new_context(
                    accept_downloads=True
                )
                page = context.new_page()
                logger.info(f"Site URL = {URL}")
                page.goto(URL)

                # LOGIN
                login(logger, page, USUARIO, PASSWORD)
                limpiar_carpeta(logger, DOWNLOAD_PATH, ARCHIVED_PATH)

                # Operaciones_Vigentes REPORT
                descargar_reporte(
                    logger,
                    page=page,
                    menu_selector="#ctl00_rpnMenuOptions_menMenu_DXI3_P",
                    submenu_selector="#ctl00_rpnMenuOptions_menMenu_DXI3i7_P",
                    nombre_reporte="Reporte Operaciones Vigentes",
                    nombre_archivo="Operaciones_Vigentes",
                    limpiar_filtros=True,
                    checkbox_selector="#ctl00_ctl00_cphBaseContainer_cphMasterPageMainContainer_chbReporteEspecial_S_D",
                    DOWNLOAD_PATH=DOWNLOAD_PATH,
                    today=today
                )

                # Gestiones_Diarias REPORT
                descargar_reporte(
                    logger,
                    page=page,
                    menu_selector="#ctl00_ctl00_rpnMenuOptions_menMenu_DXI3_P",
                    submenu_selector="#ctl00_ctl00_rpnMenuOptions_menMenu_DXI3i5_PImg",
                    nombre_reporte="Reporte de Gestiones Diarias",
                    nombre_archivo="Gestiones_Diarias",
                    DOWNLOAD_PATH=DOWNLOAD_PATH,
                    today=today
                )

                logger.info("Todos los reportes fueron descargados exitosamente")
                time.sleep(3)
                context.close()
                browser.close()

            last_error = None
            break

        except BaseException as ex:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
            attempts += 1
            logger.error(f"Ha habido una excepción: {type(ex)} - {str(ex)}")
            last_error = ex
            time.sleep(5)

    if last_error is None:
        send_email(logger, "Logs", log_path, "")
    else:
        send_email(logger, "Error", log_path, last_error)

    # Only remove THIS run's file handler + log file, never the console handler
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root_logger.removeHandler(handler)

    os.remove(log_path)


# How long to wait before retrying the catch-up safety net again,
# so a persistently-failing site doesn't get hammered every 30 seconds.
CATCHUP_COOLDOWN = timedelta(hours=2)


def get_today_cutoff(now):
    """Return today's cutoff datetime (e.g. today at 11:00)."""
    return now.replace(hour=RUN_AFTER_HOUR, minute=RUN_AFTER_MINUTE, second=0, microsecond=0)


logger.info("Starting the automatic workflow... (Ctrl+C to stop)")

last_run_date = None       # tracks the date (not datetime) the daily 11am run last happened
last_attempt_time = None   # tracks the datetime of the last main() call, for any reason (daily or catch-up)
last_heartbeat = datetime.now()

if has_todays_file():
    now = datetime.now()
    last_run_date = now.date()
    logger.info(f"Detected files from today's run. Last run: {last_run_date}.")

while True:
    try:
        now = datetime.now()
        cutoff = get_today_cutoff(now)

        # --- Primary trigger: always run once per day at/after 11:00, no freshness check ---
        if now >= cutoff and last_run_date != now.date():
            logger.info(f"Past {RUN_AFTER_HOUR:02d}:{RUN_AFTER_MINUTE:02d} and no run recorded today. Running download job...")
            main()
            last_run_date = now.date()
            last_attempt_time = now

        # --- Safety-net trigger: if the report file is STILL stale (>24h) after the daily run,
        # something went wrong (e.g. the site download failed silently). Retry regardless of the
        # 11am gate, but only every CATCHUP_COOLDOWN to avoid hammering the site if it keeps failing.
        else:
            stale_files = get_stale_files()
            if stale_files and (last_attempt_time is None or (now - last_attempt_time) >= CATCHUP_COOLDOWN):
                logger.warning(f"Report file(s) still older than {STALE_FILE_THRESHOLD_HOURS} hours - retrying as a catch-up run:")
                for filepath, age in stale_files:
                    logger.warning(f"  {filepath} (age: {age})")
                main()
                last_attempt_time = now

        # Heartbeat every 10 minutes so it's visible the loop is still alive
        if (now - last_heartbeat) >= timedelta(minutes=10):
            logger.info(f"Loop alive. Waiting for next run (last run: {last_run_date}).")
            last_heartbeat = now

        time.sleep(30)

    except Exception as e:
        print("Error in the main loop:", e)