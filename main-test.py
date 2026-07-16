from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import os
import time
import getpass
import logging
from dotenv import load_dotenv

from src.Utils import send_email, limpiar_carpeta, login, descargar_reporte,run_with_retries

# CONFIG AND DEFINE VARIABLES
windows_user = getpass.getuser()
today = (datetime.now() - timedelta(hours=5)).strftime("%Y%m%d_%H%M")

load_dotenv()

URL = os.getenv("URL")

USUARIO = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")

DOWNLOAD_PATH = f"C:\\Users\\{windows_user}\\OneDrive - Inchcape\\Finance Transformation - Databricks\\" + os.getenv("download_path")
ARCHIVED_PATH = f"C:\\Users\\{windows_user}\\OneDrive - Inchcape\\Finance Transformation - Databricks\\" + os.getenv("ARCHIVED_PATH")
LOG_PATH = os.path.join(f"C:\\Users\\{windows_user}\\Downloads", f"log_{today}.log")
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

os.makedirs(DOWNLOAD_PATH, exist_ok=True)
os.makedirs(ARCHIVED_PATH, exist_ok=True)


# LOGGING

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),  # guarda en archivo
        logging.StreamHandler()                            # también muestra en consola
    ]
)

logger = logging.getLogger(__name__)


#  RUN FLOW
def run_flow(logger):
    print("hi")

# MAIN
attempts = 1
last_error = None

run_flow(logger)

logger.info(f"Corriendo bot en el usuario {windows_user}")

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
        #context.close()
        #browser.close()
        attempts += attempts
        logger.error(f"Ha habido una excepción: {type(ex)} - {str(ex)}")
        last_error = ex


if last_error is None:
    send_email(logger,"Logs",LOG_PATH, "")
else:
    send_email(logger,"Error",LOG_PATH, last_error)

for lg in [logger, logging.getLogger()]:  # named logger + root logger
    for handler in lg.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            lg.removeHandler(handler)

os.remove(LOG_PATH)