import socket
import sys
import argparse
import json
import os
import logging
import asyncio
from comet.api.token import TokenManager
from comet.api.notification_pusher import NotificationPusher
from comet import handlers


def get_heroic_config_path():
    if sys.platform == 'linux':
        os_path = os.path.normpath(
            f"{os.getenv('XDG_CONFIG_PATH', os.path.expandvars('$HOME/.config'))}/heroic/gog_store/auth.json")
        flatpak_path = os.path.expandvars(
            "$HOME/.var/app/com.heroicgameslauncher.hgl/config/heroic/gog_store/auth.json")

        if os.path.exists(flatpak_path):
            return flatpak_path
        return os_path
    elif sys.platform == 'win32':
        return os.path.expandvars("%APPDATA%/heroic/gog_store/auth.json")
    elif sys.platform == 'darwin':
        return os.path.expandvars("$HOME/.config/heroic/gog_store/auth.json")


def load_heroic_config():
    heroic_config_path = get_heroic_config_path()
    file = open(heroic_config_path, 'r')
    data = file.read()
    file.close()
    json_data = json.loads(data)
    return json_data["46899977096215655"]["access_token"], json_data["46899977096215655"]["refresh_token"], \
        json_data["46899977096215655"]["user_id"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", help="Access token of the user")
    parser.add_argument("--refresh-token", dest="refresh_token", help="Refresh token of the user")
    parser.add_argument("--user-id", dest="user_id", help="Id of a user")
    parser.add_argument("--from-heroic", dest="heroic", action="store_true")

    arguments, unknown_arguments = parser.parse_known_args()

    logging.basicConfig(format="%(levelname)s:%(name)s:%(message)s", level=logging.INFO)
    logger = logging.getLogger("comet_main")

    HOST = 'localhost'
    PORT = 9977

    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        soc.bind((HOST, PORT))
    except OSError:
        print(f'Unable to bind to {HOST}:{PORT}')
        raise

    if arguments.heroic:
        token, refresh_token, user_id = load_heroic_config()
    elif not arguments.token or not arguments.refresh_token or not arguments.user_id:
        logger.error("You are missing an argument use --help")
        sys.exit()
    else:
        token, refresh_token, user_id = arguments.token, arguments.refresh_token, arguments.user_id

    logger.info(f"started listening on port {PORT}")
    token_mgr = TokenManager(token, refresh_token, user_id)
    notification_pusher = NotificationPusher(token, user_id)

    soc.listen(5)
    while True:
        logger.info(f"waiting for connection")
        try:
            con, address = soc.accept()
        except KeyboardInterrupt:
            soc.close()
            sys.exit(1)

        print(address[1])
        if address[0] == '127.0.0.1':
            print("Accepting connection")
            con_handler = handlers.ConnectionHandler(con, address, token_mgr, notification_pusher)
            asyncio.run(con_handler.handle_connection())
        else:
            con.close()


if __name__ == "__main__":
    main()
