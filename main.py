from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import os
import time
import getpass
import schedule
import logging
from dotenv import load_dotenv

from src.Utils import send_email, limpiar_carpeta, login, descargar_reporte, run_with_retries, get_creds

# CONFIG AND DEFINE VARIABLES
windows_user = getpass.getuser()
today = (datetime.now() - timedelta(hours=5)).strftime("%Y%m%d_%H%M")

load_dotenv()

URL = os.getenv("URL")

#USUARIO = os.getenv("USER")
#PASSWORD = os.getenv("PASSWORD")

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



# MAIN
def main():
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
        send_email(logger,"Logs",LOG_PATH, "")
    else:
        send_email(logger,"Error",LOG_PATH, last_error)

    for lg in [logger, logging.getLogger()]:  # named logger + root logger
        for handler in lg.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                lg.removeHandler(handler)

    os.remove(LOG_PATH)

schedule.every().day.at("11:00").do(main)
schedule.every().day.at("18:53").do(main)

logger.info("Starting the automatic workflow... (Ctrl+C to stop)")

while True:
    try:
        schedule.run_pending()  # Check if there are any pending tasks
        time.sleep(30)
    except Exception as e:
        print("Error in the main loop:", e)