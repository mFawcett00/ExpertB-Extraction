import getpass
from playwright.sync_api import sync_playwright
from datetime import datetime
import os
import time
import logging


# =====================================================
# CONFIGURACIÓN
# =====================================================

usuario_windows = getpass.getuser()

URL = "https://cosmosarriendaexpress.com/"

USUARIO = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")

DOWNLOAD_PATH = f"C:\\Users\\{usuario_windows}\\OneDrive - Inchcape\\Finance Transformation - Databricks\\Expert-B"

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

os.makedirs(DOWNLOAD_PATH, exist_ok=True)

fecha = datetime.now().strftime("%Y%m%d_%H%M")

# =====================================================
# LOGGING
# =====================================================

LOG_PATH = os.path.join(f"C:\\Users\\{usuario_windows}\\Downloads", f"log_{fecha}.log")

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

# =====================================================
# REINTENTOS
# =====================================================

MAX_INTENTOS = 3  # 1 intento inicial + 2 reintentos
ESPERA_ENTRE_REINTENTOS = 5  # segundos


def con_reintentos(func, *args, nombre_paso="operación", **kwargs):
    """
    Ejecuta func(*args, **kwargs). Si lanza una excepción, reintenta
    hasta MAX_INTENTOS veces en total, esperando un poco entre cada intento.
    Si todos los intentos fallan, vuelve a lanzar la última excepción.
    """

    ultimo_error = None

    for intento in range(1, MAX_INTENTOS + 1):
        try:
            if intento > 1:
                logger.info(f"🔁 Reintento {intento - 1}/{MAX_INTENTOS - 1} para: {nombre_paso}")

            return func(*args, **kwargs)

        except Exception as e:
            ultimo_error = e
            logger.warning(
                f"⚠️ Intento {intento}/{MAX_INTENTOS} fallido para '{nombre_paso}': {e}"
            )

            if intento < MAX_INTENTOS:
                time.sleep(ESPERA_ENTRE_REINTENTOS)
            else:
                logger.error(
                    f"❌ '{nombre_paso}' falló después de {MAX_INTENTOS} intentos"
                )

    raise ultimo_error


# =====================================================
# FUNCIONES
# =====================================================

def login(page):

    logger.info("Iniciando proceso de login...")

    frame = page.frame_locator("iframe")

    try:
        frame.get_by_role(
            "textbox",
            name="Ingrese su usuario"
        ).fill(USUARIO)
        logger.info("Usuario ingresado")

        frame.get_by_role(
            "textbox",
            name="*********"
        ).fill(PASSWORD)
        logger.info("Password ingresado")

        frame.get_by_role(
            "link",
            name="Iniciar Sesión"
        ).click()
        logger.info("Click en 'Iniciar Sesión'")

    except Exception as e:
        logger.error(f"Error durante el ingreso de credenciales: {e}")
        raise  # si esto falla, no tiene sentido seguir

    page.wait_for_timeout(3000)

    # Popup "Aceptar"
    try:
        frame.locator("span").filter(has_text="Aceptar").click()
        logger.info("Popup 'Aceptar' cerrado")
    except Exception:
        logger.debug("No apareció popup 'Aceptar' (esperado en algunos casos)")

    # Reintento login si aparece
    try:

        frame.get_by_role(
            "textbox",
            name="*********"
        ).fill(PASSWORD)

        frame.get_by_role(
            "link",
            name="Iniciar Sesión"
        ).click()

        frame.locator("span").filter(has_text="Sí").click()

        logger.info("Se ejecutó reintento de login (confirmación 'Sí')")

    except Exception:
        logger.debug("No fue necesario reintentar login")

    logger.info("✅ Login exitoso")


# =====================================================

def descargar_reporte(
    page,
    menu_selector,
    submenu_selector,
    nombre_reporte,
    nombre_archivo,
    limpiar_filtros=False,
    checkbox_selector=None
):

    logger.info(f"--- Iniciando descarga de reporte: {nombre_reporte} ---")

    frame = page.frame_locator("iframe")

    try:
        # Abrir menú
        frame.locator(menu_selector).click()
        logger.info(f"Menú abierto ({menu_selector})")

        page.wait_for_timeout(1000)

        # Submenú
        frame.locator(submenu_selector).click()
        logger.info(f"Submenú seleccionado ({submenu_selector})")

        page.wait_for_timeout(2000)

        # Abrir reporte
        frame.get_by_role(
            "link",
            name=nombre_reporte
        ).click()
        logger.info(f"Reporte '{nombre_reporte}' abierto")

        page.wait_for_timeout(3000)

    except Exception as e:
        logger.error(f"Error al navegar hacia el reporte '{nombre_reporte}': {e}")
        raise

    # Checkbox opcional
    if checkbox_selector:
        try:
            frame.locator(
                checkbox_selector
            ).click()
            logger.info("Checkbox opcional marcado")
        except Exception as e:
            logger.warning(f"No se pudo marcar el checkbox opcional: {e}")

    # Limpiar filtros opcional
    if limpiar_filtros:
        try:
            frame.get_by_role(
                "button",
                name="Limpiar filtros"
            ).click()
            logger.info("Filtros limpiados")
        except Exception as e:
            logger.warning(f"No se pudieron limpiar los filtros: {e}")

    # Popup reporte
    try:
        with page.expect_popup() as popup_info:

            frame.get_by_role(
                "button",
                name="Imprimir reporte"
            ).click()

        reporte_page = popup_info.value
        logger.info("Popup de reporte abierto correctamente")

    except Exception as e:
        logger.error(f"Error al abrir el popup del reporte '{nombre_reporte}': {e}")
        raise

    # Descargar Excel
    try:
        with reporte_page.expect_download() as download_info:

            with reporte_page.expect_popup() as export_popup:

                reporte_page.get_by_role(
                    "button",
                    name="Exportar como archivo de Excel"
                ).click()

        download = download_info.value
        logger.info("Descarga de Excel iniciada")

    except Exception as e:
        logger.error(f"Error al exportar/descargar Excel para '{nombre_reporte}': {e}")
        raise

    archivo = os.path.join(
        DOWNLOAD_PATH,
        f"{nombre_archivo}_{fecha}.xlsx"
    )

    download.save_as(archivo)

    logger.info(f"✅ Descargado: {archivo}")

    # Cerrar popup exportación
    try:
        export_popup.value.close()
        logger.debug("Popup de exportación cerrado")
    except Exception as e:
        logger.warning(f"No se pudo cerrar el popup de exportación: {e}")

    # Popup error opcional
    try:
        frame.locator(
            "#ctl00_ctl00_cphBaseUsercontrols_cphMasterPageMainUsercontrols_popUpErrores_TPCFm1_btnCerrar_CD span"
        ).click()
        logger.info("Popup de error cerrado (apareció inesperadamente)")
    except Exception:
        logger.debug("No apareció popup de error (esperado en la mayoría de casos)")

    logger.info(f"--- Finalizada descarga de reporte: {nombre_reporte} ---")


# =====================================================
# MAIN
# =====================================================

logger.info("=" * 60)
logger.info("INICIO DE EJECUCIÓN DEL SCRIPT")
logger.info(f"Archivo de log: {LOG_PATH}")
logger.info("=" * 60)

logger.info(f"💻 Ejecutado por el usuario de Windows: {usuario_windows}")

try:
    with sync_playwright() as p:

        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=False
        )
        logger.info("Navegador Chrome lanzado")

        context = browser.new_context(
            accept_downloads=True
        )

        page = context.new_page()

        page.goto(URL)
        logger.info(f"Navegado a {URL}")

        # LOGIN
        con_reintentos(login, page, nombre_paso="Login")

        # =================================================
        # REPORTE 1
        # =================================================

        con_reintentos(
            descargar_reporte,
            page=page,
            menu_selector="#ctl00_rpnMenuOptions_menMenu_DXI3_P",
            submenu_selector="#ctl00_rpnMenuOptions_menMenu_DXI3i7_P",
            nombre_reporte="Reporte Operaciones Vigentes",
            nombre_archivo="Operaciones_Vigentes",
            limpiar_filtros=True,
            checkbox_selector="#ctl00_ctl00_cphBaseContainer_cphMasterPageMainContainer_chbReporteEspecial_S_D",
            nombre_paso="Descarga: Reporte Operaciones Vigentes"
        )

        # =================================================
        # REPORTE 2
        # =================================================

        con_reintentos(
            descargar_reporte,
            page=page,
            menu_selector="#ctl00_ctl00_rpnMenuOptions_menMenu_DXI3_P",
            submenu_selector="#ctl00_ctl00_rpnMenuOptions_menMenu_DXI3i5_PImg",
            nombre_reporte="Reporte de Gestiones Diarias",
            nombre_archivo="Gestiones_Diarias",
            nombre_paso="Descarga: Reporte de Gestiones Diarias"
        )

        logger.info("🎉 TODOS LOS REPORTES DESCARGADOS")

        time.sleep(3)

        context.close()
        browser.close()
        logger.info("Navegador cerrado. Ejecución finalizada correctamente.")

except Exception as e:
    logger.exception(f"❌ Ejecución interrumpida por un error: {e}")
    raise