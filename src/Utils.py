import os
import shutil
from pathlib import Path
import requests
import time
from dotenv import load_dotenv
from azure.identity import AzureCliCredential
from azure.keyvault.secrets import SecretClient
from azure.core.settings import settings

# GET USER AND PASSWORD FROM AZURE KEY VAULT
def get_creds(logger):
    load_dotenv()

    client = SecretClient(vault_url=os.getenv("VAULT_URL"), credential=AzureCliCredential())
    settings.tracing_enabled = False

    try:
        user = client.get_secret(os.getenv("KV_USER")).value
        logger.info(f"Usuario: {user}")
    except:
        logger.error("Se detectó un error de al solicitar el secreto del usuario")
        raise ValueError("Error al solicitar secreto: no fue posible traer el valor del usuario")

    try:
        password = client.get_secret(os.getenv("KV_PASSWORD"),tracing_options={"enabled": False}).value
        logger.info(f"Se obtuvo la contraseña exitosamente")
    except:
        logger.error("Se detectó un error de al solicitar el secreto del contraseña")
        raise ValueError("Error al solicitar secreto: no fue posible traer el valor del contraseña")

    return user, password


# MOVE FILES FROM INPUT FOLDER TO ARCHIVED FOLDER
def limpiar_carpeta(logger, carpeta_origen, carpeta_destino):
    origen = Path(carpeta_origen)
    destino = Path(carpeta_destino)

    if not origen.exists():
        logger.info(f"La carpeta origen no existe: {origen}")
        return []

    # Crea la carpeta destino si no existe
    destino.mkdir(parents=True, exist_ok=True)

    # Solo archivos, no subcarpetas
    archivos = [f for f in origen.iterdir() if f.is_file()]

    if not archivos:
        logger.info("No hay archivos en la carpeta origen.")
        return []

    movidos = []
    for archivo in archivos:
        destino_archivo = destino / archivo.name
        shutil.move(str(archivo), str(destino_archivo))
        movidos.append(archivo.name)
        logger.info(f"Movido: {archivo.name}")


# LOGIN TO EXPERT-B PORTAL
def login(logger, page,USUARIO,PASSWORD):
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

    # Popup "Aceptar"
    try:
        frame.locator("span").filter(has_text="Sí").click()
        logger.info("Había una sesión activa para este usuario. Cerrando...")
    except:
        pass

    time.sleep(3)

    element = frame.locator("#ctl00_cphBaseContainer_lblNombreCompletoUsuario")
    justtest=element.count()

    if element.count() > 0:
        logger.info(f"Login exitoso con el usuario {USUARIO}")
    else:
        logger.error("Se detectó un error de credenciales no válidas en la página")
        raise ValueError("Error al iniciar sesión: nombre de usuario o contraseña incorrectos")



   # try:
   #     frame.locator("span").filter(has_text="Aceptar").click()
   #     logger.info("Click en Aceptar button...")
   # except:
   #     pass

    # Reintento login si aparece

   # try:
   #     logger.info("Reintento login")
   #     frame.get_by_role(
   #         "textbox",
   #         name="*********"
   #     ).fill(PASSWORD)
   #     logger.info("Escribiendo PASSWORD")

   #     frame.get_by_role(
   #         "link",
   #         name="Iniciar Sesión"
   #     ).click()
   #     logger.info("Click en Iniciar Sesión")

   #     frame.locator("span").filter(has_text="Sí").click()

   # except:
   #     pass




# DOWNLOAD BOTH REPORT TYPES, ONE AT THE TIME
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
    logger.info(f"Empezando descargar_reporte para {nombre_reporte}")

    frame = page.frame_locator("iframe")

    # Abrir menú
    frame.locator(menu_selector).click()

    page.wait_for_timeout(1000)

    # Submenú
    frame.locator(submenu_selector).click()

    page.wait_for_timeout(2000)

    # Abrir reporte
    frame.get_by_role(
        "link",
        name=nombre_reporte
    ).click()
    logger.info("Reporte seleccionado")

    page.wait_for_timeout(3000)

    # Checkbox opcional
    if checkbox_selector:

        frame.locator(
            checkbox_selector
        ).click()

    # Limpiar filtros opcional
    if limpiar_filtros:

        frame.get_by_role(
            "button",
            name="Limpiar filtros"
        ).click()

    # Popup reporte
    with page.expect_popup() as popup_info:

        frame.get_by_role(
            "button",
            name="Imprimir reporte"
        ).click()
        logger.info(f"Click en Imprimir reporte")

    reporte_page = popup_info.value

    # Descargar Excel
    downloads = []
    reporte_page.context.on("download", lambda d: downloads.append(d))

    with reporte_page.expect_popup() as export_popup:
        reporte_page.get_by_role(
            "button",
            name="Exportar como archivo de Excel"
        ).click()
        logger.info("Exportando archivo en excel...")

    # Give the download time to actually fire, on whichever page it lands
    reporte_page.wait_for_timeout(5000)

    if not downloads:
        # last resort: wait a bit longer explicitly
        reporte_page.context.wait_for_event("download", timeout=30000)

    download = downloads[0] if downloads else None
    if download is None:
        reporte_page.screenshot(path=f"debug_no_download_{today}.png")
        raise Exception("No se detectó ninguna descarga")

    respuesta = download.headers
    logger.info(respuesta)

    archivo = os.path.join(DOWNLOAD_PATH, f"{nombre_archivo}_{today}.xlsx")
    download.save_as(archivo)
    logger.info(f"Archivo descargado: {archivo}")

    # Descargar Excel
    #with reporte_page.expect_download(timeout=180_000) as download_info:

        #with reporte_page.expect_popup() as export_popup:

    #        reporte_page.get_by_role(
    #            "button",
    #            name="Exportar como archivo de Excel"
    #        ).click()
    #        logger.info("Exportando archivo en excel...")
    #        logger.info(str(download_info.response()))
    #        logger.info("after excel log")

            #respuesta = await download.response()
            #print(respuesta.headers())

    #download = download_info.value

    #archivo = os.path.join(
    #    DOWNLOAD_PATH,
    #    f"{nombre_archivo}_{today}.xlsx"
    #)

    #try:
        #os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        #download.save_as(archivo)
        #logger.info(f"Archivo descargado: {archivo}")
    #except:
        #pass

        #download.save_as(archivo)

        #logger.info(f"Archivo descargado: {archivo}")

    # Cerrar popup exportación
    #export_popup.value.close()

    # Popup error opcional
    try:

        frame.locator(
            "#ctl00_ctl00_cphBaseUsercontrols_cphMasterPageMainUsercontrols_popUpErrores_TPCFm1_btnCerrar_CD span"
        ).click()

    except:
        pass




# SEND EMAILS FUNCTION FOR LOGS AND ERROR
def send_email (tracer_logger, type, path, errormessage):

    filename = os.path.basename(path)

    with open(path, "rb") as f:
        file_bytes = f.read()
        file_bytes_str = file_bytes.decode("latin-1")

    url = os.getenv('EMAIL_ATTACHMENT_API_URL')

    if (type == "Logs"):
        payload = {
            "key": os.getenv('EMAIL_KEY'),
            "color": "green",
            "attachment": file_bytes_str,
            "filename" : filename,
            "from": os.getenv('EMAIL_FROM'),
            "to": os.getenv('EMAIL_TO_LOG').split(','),
            "cc": os.getenv('EMAIL_CC_LOG').split(','),
            "title": "Expert-B Extraction - Success Run",
            "subject": "Expert-B Extraction - Success Run",
            "message": f"Hi team, <br><br> This is the logs file for the <b>Expert-B Extraction</b> bot. Please review it if needed."
        }
    elif (type == "Error"):
        payload = {
            "key": os.getenv('EMAIL_KEY'),
            "color": "red",
            "attachment": file_bytes_str,
            "filename": filename,
            "from": os.getenv('EMAIL_FROM'),
            "to": os.getenv('EMAIL_TO_LOG').split(','),
            "cc": os.getenv('EMAIL_CC_LOG').split(','),
            "title": "Expert-B Extraction - Logs",
            "subject": "Expert-B Extraction - Error Notification",
            "message": f"Hi team, <br><br> We got an error in the <b>Expert-B Extraction</b> bot: <br> <br> {str(errormessage)} Please review it if needed."
        }


    response = requests.post(url, json=payload)

    if response.status_code == 200:
        tracer_logger.info(f"{type} email sent")
    else:
        tracer_logger.error(f"Error sending email: {response.text}")
        raise Exception(f"Error sending email: {response.text}")


def run_with_retries(logger, func, max_attempts=3, delay=1):
    print("hi from run_with_retries ")
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            last_error = e
            logger.info (f"Flow failed on attempt {attempt}: {e}")
            if attempt < max_attempts:
                time.sleep(delay)

    raise RuntimeError(f"Flow failed after {max_attempts} attempts") from last_error