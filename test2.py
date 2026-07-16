import getpass
import logging
import os


usuario_windows = getpass.getuser()
fecha = "07-08-2026"

LOG_PATH = os.path.join(
    f"C:\\Users\\{usuario_windows}\\Downloads",
    f"log_{fecha}.log"
)

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



logger.info(f"💻 Ejecutado por el usuario de Windows: {usuario_windows}")