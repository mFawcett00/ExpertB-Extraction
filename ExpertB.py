from playwright.sync_api import sync_playwright
from datetime import datetime
import os
import time
import getpass

# =====================================================
# CONFIGURACIÓN
# =====================================================

URL = "https://cosmosarriendaexpress.com/"

USUARIO = "MEVANGELISTA"
PASSWORD = "Inchcape2026!"

usuario_windows = getpass.getuser()

DOWNLOAD_PATH = f"C:\\Users\\{usuario_windows}\\OneDrive - Inchcape\\Finance Transformation - Databricks\\Expert-B"

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

os.makedirs(DOWNLOAD_PATH, exist_ok=True)

fecha = datetime.now().strftime("%Y%m%d_%H%M")

# =====================================================
# FUNCIONES
# =====================================================

def login(page):

    frame = page.frame_locator("iframe")

    frame.get_by_role(
        "textbox",
        name="Ingrese su usuario"
    ).fill(USUARIO)

    frame.get_by_role(
        "textbox",
        name="*********"
    ).fill(PASSWORD)

    frame.get_by_role(
        "link",
        name="Iniciar Sesión"
    ).click()

    page.wait_for_timeout(3000)

    # Popup "Aceptar"
    try:
        frame.locator("span").filter(has_text="Aceptar").click()
    except:
        pass

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

    except:
        pass

    print("✅ Login exitoso")


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

    reporte_page = popup_info.value

    # Descargar Excel
    with reporte_page.expect_download() as download_info:

        with reporte_page.expect_popup() as export_popup:

            reporte_page.get_by_role(
                "button",
                name="Exportar como archivo de Excel"
            ).click()

    download = download_info.value

    archivo = os.path.join(
        DOWNLOAD_PATH,
        f"{nombre_archivo}_{fecha}.xlsx"
    )

    download.save_as(archivo)

    print(f"✅ Descargado: {archivo}")

    # Cerrar popup exportación
    export_popup.value.close()

    # Popup error opcional
    try:

        frame.locator(
            "#ctl00_ctl00_cphBaseUsercontrols_cphMasterPageMainUsercontrols_popUpErrores_TPCFm1_btnCerrar_CD span"
        ).click()

    except:
        pass


# =====================================================
# MAIN
# =====================================================

with sync_playwright() as p:

    browser = p.chromium.launch(
        executable_path=CHROME_PATH,
        headless=False
    )

    context = browser.new_context(
        accept_downloads=True
    )

    page = context.new_page()

    page.goto(URL)

    # LOGIN
    login(page)

    # =================================================
    # REPORTE 1
    # =================================================

    descargar_reporte(
        page=page,

        menu_selector="#ctl00_rpnMenuOptions_menMenu_DXI3_P",

        submenu_selector="#ctl00_rpnMenuOptions_menMenu_DXI3i7_P",

        nombre_reporte="Reporte Operaciones Vigentes",

        nombre_archivo="Operaciones_Vigentes",

        limpiar_filtros=True,

        checkbox_selector="#ctl00_ctl00_cphBaseContainer_cphMasterPageMainContainer_chbReporteEspecial_S_D"
    )

    # =================================================
    # REPORTE 2
    # =================================================

    descargar_reporte(
        page=page,

        menu_selector="#ctl00_ctl00_rpnMenuOptions_menMenu_DXI3_P",

        submenu_selector="#ctl00_ctl00_rpnMenuOptions_menMenu_DXI3i5_PImg",

        nombre_reporte="Reporte de Gestiones Diarias",

        nombre_archivo="Gestiones_Diarias"
    )

    print("🎉 TODOS LOS REPORTES DESCARGADOS")

    time.sleep(3)

    context.close()
    browser.close()