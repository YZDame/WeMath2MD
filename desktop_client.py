"""WeMath2MD desktop client launcher.

Starts the local Flask service and opens the UI in the default browser.
This file is used as the entrypoint for desktop packaging (MSI/DMG).
"""

from __future__ import annotations

import atexit
import os
import signal
import socket
import threading
import time
import webbrowser

from werkzeug.serving import make_server

from config import logging as log_cfg, web as web_cfg
from logger import setup_logger, get_logger
from web_app import app


def _find_free_port(preferred_port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", preferred_port)) != 0:
            return preferred_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class ServerThread(threading.Thread):
    def __init__(self, host: str, port: int) -> None:
        super().__init__(daemon=True)
        self.server = make_server(host, port, app)

    def run(self) -> None:
        self.server.serve_forever()

    def shutdown(self) -> None:
        self.server.shutdown()


def main() -> None:
    os.makedirs("templates", exist_ok=True)
    setup_logger(level=log_cfg.level, log_file="desktop_client.log")
    logger = get_logger("wemath2md.desktop")

    host = "127.0.0.1"
    port = _find_free_port(web_cfg.port)

    thread = ServerThread(host, port)

    def _cleanup(*_: object) -> None:
        logger.info("desktop client shutting down")
        thread.shutdown()

    atexit.register(_cleanup)
    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    thread.start()
    url = f"http://{host}:{port}"
    logger.info("desktop client started at %s", url)

    time.sleep(0.5)
    webbrowser.open(url)

    while thread.is_alive():
        time.sleep(0.5)


if __name__ == "__main__":
    main()
