import os
import shutil
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from azure.identity import AzureCliCredential
from azure.keyvault.secrets import SecretClient
from azure.core.settings import settings


# GET USER AND PASSWORD FROM AZURE KEY VAULT
def get_creds(logger):
    load_dotenv()

    client = SecretClient(
        vault_url=os.getenv("VAULT_URL"),
        credential=AzureCliCredential()
    )

    settings.tracing_enabled = False

    try:
        user = client.get_secret(
            os.getenv("KV_USER")
        ).value

        logger.info(f"Usuario: {user}")

    except Exception as ex:
        logger.error(
            f"Se detectó un error al solicitar el secreto del usuario: {ex}"
        )

        raise ValueError(
            "Error al solicitar secreto: "
            "no fue posible traer el valor del usuario"
        ) from ex

    try:
        password = client.get_secret(
            os.getenv("KV_PASSWORD"),
            tracing_options={"enabled": False}
        ).value

        logger.info("Se obtuvo la contraseña exitosamente")

    except Exception as ex:
        logger.error(
            f"Se detectó un error al solicitar el secreto "
            f"de la contraseña: {ex}"
        )

        raise ValueError(
            "Error al solicitar secreto: "
            "no fue posible traer el valor de la contraseña"
        ) from ex

    return user, password


# MOVE FILES FROM INPUT FOLDER TO ARCHIVED FOLDER
def limpiar_carpeta(logger, carpeta_origen, carpeta_destino):
    origen = Path(carpeta_origen)
    destino = Path(carpeta_destino)

    if not origen.exists():
        logger.info(f"La carpeta origen no existe: {origen}")
        return []

    destino.mkdir(
        parents=True,
        exist_ok=True
    )

    archivos = [
        archivo
        for archivo in origen.iterdir()
        if archivo.is_file()
    ]

    if not archivos:
        logger.info("No hay archivos en la carpeta origen.")
        return []

    movidos = []

    for archivo in archivos:
        destino_archivo = destino / archivo.name

        shutil.move(
            str(archivo),
            str(destino_archivo)
        )

        movidos.append(archivo.name)
        logger.info(f"Movido: {archivo.name}")

    return movidos


# LOGIN TO EXPERT-B PORTAL
def login(logger, page, USUARIO, PASSWORD):
    logger.info("Starting login function")

    frame = page.frame_locator("iframe")

    frame.get_by_role(
        "textbox",
        name="Ingrese su usuario"
    ).fill(USUARIO)

    logger.info("Escribiendo USUARIO")

    frame.get_by_role(
        "textbox",
        name="*********"
    ).fill(PASSWORD)

    logger.info("Escribiendo PASSWORD")

    frame.get_by_role(
        "link",
        name="Iniciar Sesión"
    ).click()

    logger.info("Click en Iniciar Sesión")

    page.wait_for_timeout(3000)

    # Popup de sesión activa
    try:
        frame.locator(
            "span"
        ).filter(
            has_text="Sí"
        ).click(
            timeout=5000
        )

        logger.info(
            "Había una sesión activa para este usuario. Cerrando..."
        )

    except Exception:
        logger.info(
            "No se detectó una sesión activa anterior."
        )

    time.sleep(3)

    element = frame.locator(
        "#ctl00_cphBaseContainer_lblNombreCompletoUsuario"
    )

    if element.count() > 0:
        logger.info(
            f"Login exitoso con el usuario {USUARIO}"
        )

    else:
        logger.error(
            "Se detectó un error de credenciales "
            "no válidas en la página"
        )

        raise ValueError(
            "Error al iniciar sesión: "
            "nombre de usuario o contraseña incorrectos"
        )


# DOWNLOAD BOTH REPORT TYPES, ONE AT A TIME
def descargar_reporte(
    logger,
    page,
    menu_selector,
    submenu_selector,
    nombre_reporte,
    nombre_archivo,
    DOWNLOAD_PATH,
    today,
    limpiar_filtros=False,
    checkbox_selector=None,
):
    logger.info(
        f"Empezando descargar_reporte para {nombre_reporte}"
    )

    frame = page.frame_locator("iframe")
    reporte_page = None

    try:
        # Abrir menú
        frame.locator(
            menu_selector
        ).click(
            timeout=30000
        )

        page.wait_for_timeout(1000)

        # Abrir submenú
        frame.locator(
            submenu_selector
        ).click(
            timeout=30000
        )

        page.wait_for_timeout(2000)

        # Abrir reporte
        frame.get_by_role(
            "link",
            name=nombre_reporte
        ).click(
            timeout=30000
        )

        logger.info("Reporte seleccionado")

        page.wait_for_timeout(3000)

        # Checkbox opcional
        if checkbox_selector:
            frame.locator(
                checkbox_selector
            ).click(
                timeout=30000
            )

            logger.info(
                "Checkbox opcional seleccionado"
            )

        # Limpiar filtros opcional
        if limpiar_filtros:
            frame.get_by_role(
                "button",
                name="Limpiar filtros"
            ).click(
                timeout=30000
            )

            logger.info("Filtros limpiados")

        # Abrir popup del reporte
        with page.expect_popup(
            timeout=60000
        ) as popup_info:

            frame.get_by_role(
                "button",
                name="Imprimir reporte"
            ).click(
                timeout=30000
            )

            logger.info("Click en Imprimir reporte")

        reporte_page = popup_info.value

        logger.info(
            f"Ventana del reporte abierta: {reporte_page.url}"
        )

        reporte_page.wait_for_load_state(
            "domcontentloaded",
            timeout=60000
        )

        # Descargar Excel
        logger.info("Waiting for Excel download...")

        with reporte_page.expect_download(
            timeout=120000
        ) as download_info:

            reporte_page.get_by_role(
                "button",
                name="Exportar como archivo de Excel"
            ).click(
                timeout=30000
            )

            logger.info(
                "Export button clicked. "
                "Waiting up to 120 seconds..."
            )

        logger.info(
            "Download event received."
        )

        download = download_info.value

        logger.info(
            f"Download detected: "
            f"{download.suggested_filename}"
        )

        archivo = os.path.join(
            DOWNLOAD_PATH,
            f"{nombre_archivo}_{today}.xlsx"
        )

        logger.info(
            f"Saving downloaded file to: {archivo}"
        )

        download.save_as(archivo)

        if not os.path.exists(archivo):
            raise FileNotFoundError(
                f"El archivo no fue encontrado después de guardar: "
                f"{archivo}"
            )

        file_size = os.path.getsize(archivo)

        if file_size == 0:
            raise ValueError(
                f"El archivo descargado está vacío: {archivo}"
            )

        logger.info(
            f"Archivo descargado: {archivo} "
            f"({file_size:,} bytes)"
        )

        # Cerrar popup de Información haciendo click en Aceptar
        try:
            frame.locator(
                "#ctl00_ctl00_cphBaseUsercontrols_"
                "cphMasterPageMainUsercontrols_"
                "popUpErrores_TPCFm1_btnCerrar_CD"
            ).click(
                timeout=5000
            )

            logger.info(
                "Information popup detected. "
                "Clicked Aceptar."
            )

        except Exception:
            logger.info(
                "No information popup detected."
            )

        logger.info(
            f"Reporte completado correctamente: "
            f"{nombre_reporte}"
        )

        return archivo

    except Exception as ex:
        logger.error(
            f"Error descargando el reporte "
            f"{nombre_reporte}: "
            f"{type(ex).__name__} - {ex}"
        )

        raise

    finally:
        if reporte_page:
            try:
                if not reporte_page.is_closed():
                    reporte_page.close()

                    logger.info(
                        "Ventana del reporte cerrada."
                    )

            except Exception as close_error:
                logger.warning(
                    f"No fue posible cerrar la ventana "
                    f"del reporte: {close_error}"
                )


# SEND EMAILS FUNCTION FOR LOGS AND ERROR
def send_email(tracer_logger, type, path, errormessage):
    filename = os.path.basename(path)

    with open(path, "rb") as file:
        file_bytes = file.read()
        file_bytes_str = file_bytes.decode("latin-1")

    url = os.getenv("EMAIL_ATTACHMENT_API_URL")

    if type == "Logs":
        payload = {
            "key": os.getenv("EMAIL_KEY"),
            "color": "green",
            "attachment": file_bytes_str,
            "filename": filename,
            "from": os.getenv("EMAIL_FROM"),
            "to": os.getenv("EMAIL_TO_LOG").split(","),
            "cc": os.getenv("EMAIL_CC_LOG").split(","),
            "title": "Expert-B Extraction - Success Run",
            "subject": "Expert-B Extraction - Success Run",
            "message": (
                "Hi team, <br><br> "
                "This is the logs file for the "
                "<b>Expert-B Extraction</b> bot. "
                "Please review it if needed."
            )
        }

    elif type == "Error":
        payload = {
            "key": os.getenv("EMAIL_KEY"),
            "color": "red",
            "attachment": file_bytes_str,
            "filename": filename,
            "from": os.getenv("EMAIL_FROM"),
            "to": os.getenv("EMAIL_TO_LOG").split(","),
            "cc": os.getenv("EMAIL_CC_LOG").split(","),
            "title": "Expert-B Extraction - Logs",
            "subject": "Expert-B Extraction - Error Notification",
            "message": (
                "Hi team, <br><br> "
                "We got an error in the "
                "<b>Expert-B Extraction</b> bot: "
                f"<br><br>{str(errormessage)} "
                "Please review it if needed."
            )
        }

    else:
        raise ValueError(
            f"Invalid email type: {type}"
        )

    response = requests.post(
        url,
        json=payload,
        timeout=120
    )

    if response.status_code == 200:
        tracer_logger.info(
            f"{type} email sent"
        )

    else:
        tracer_logger.error(
            f"Error sending email: {response.text}"
        )

        raise Exception(
            f"Error sending email: {response.text}"
        )


def run_with_retries(
    logger,
    func,
    max_attempts=3,
    delay=1
):
    logger.info(
        f"Starting retry flow. "
        f"Maximum attempts: {max_attempts}"
    )

    last_error = None

    for attempt in range(
        1,
        max_attempts + 1
    ):
        try:
            logger.info(
                f"Retry flow attempt {attempt}"
            )

            return func()

        except Exception as ex:
            last_error = ex

            logger.error(
                f"Flow failed on attempt "
                f"{attempt}: {ex}"
            )

            if attempt < max_attempts:
                logger.info(
                    f"Waiting {delay} second(s) "
                    f"before retry..."
                )

                time.sleep(delay)

    raise RuntimeError(
        f"Flow failed after "
        f"{max_attempts} attempts"
    ) from last_error
