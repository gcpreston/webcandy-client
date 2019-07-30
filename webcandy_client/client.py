import sys
import asyncio
import json
import signal
import logging
import argparse
import requests
import websockets

from typing import List

from opclib import pattern_names, FadecandyServer
from webcandy_client.controller import Controller

logger = logging.getLogger('wc-client')
logger.setLevel(logging.INFO)


async def start_client(
        host: str,
        port: int,
        token: str,
        client_id: str,
        patterns: List[str]) -> None:
    """
    Initiate the client connection.
    """
    ws_addr = f'ws://{host}'
    if port != 80:
        ws_addr += f':{port}'

    logger.info(f'Connecting to {ws_addr}...')
    async with websockets.connect(ws_addr) as websocket:
        logger.info(f'Connected to server {ws_addr}')

        data = json.dumps(
            {'token': token, 'client_id': client_id,
             'patterns': patterns})
        await websocket.send(data)

        logger.info(
            f'Sent token, client_id: {client_id!r}, and patterns: {patterns}')

        controller = Controller()

        try:
            async for message in websocket:
                try:
                    parsed = json.loads(message)
                    logger.debug(f'Received JSON: {parsed}')
                    controller.run(host, port, **parsed)
                except json.decoder.JSONDecodeError:
                    # TODO: Better formatting of messages sent from server
                    logger.info(f'Received text: {message}')
        except websockets.ConnectionClosed as err:
            message = (
                f'Server closed connection, code: {err.code}, '
                f'reason: {err.reason or "no reason given"}'
            )
            if err.code in {1000, 1001}:
                logger.info(message)
            else:
                logger.error(message)


def get_argument_parser() -> argparse.ArgumentParser:
    """
    Generate the command-line argument parser.
    """
    p = argparse.ArgumentParser(
        description='Webcandy client to connect to a running Webcandy server.')
    p.add_argument('username', help='the username to log in with')
    p.add_argument('password', help='the password to log in with')
    p.add_argument('client_id', help='the ID to assign this client')
    p.add_argument('--host', metavar='ADDRESS',
                   help='the address of the server to connect to'
                        '(default: webcandy.io)')
    p.add_argument('--proxy-port', metavar='PORT', type=int,
                   help='the port the Webcandy proxy server is running on'
                        '(default: 80)')
    p.add_argument('--app-port', metavar='PORT', type=int,
                   help='the port the Webcandy app is running on '
                        '(default: 443)')
    p.add_argument('--unsecure', action='store_true',
                   help='skip SSL verification; necessary when accessing '
                        'development site with self-signed certificate')
    return p


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] (%(name)s) %(levelname)s: %(message)s')

    parser = get_argument_parser()
    args = parser.parse_args()

    host = args.host or 'proxy.webcandy.io'
    proxy_port = args.proxy_port or 80
    client_id = args.client_id
    app_port = args.app_port or 443
    unsecure = args.unsecure

    # get access token from username and password
    try:
        response = requests.post(f'https://{host}:{app_port}/api/token',
                                 json={'username': args.username,
                                       'password': args.password},
                                 verify=not unsecure)
    except requests.exceptions.ConnectionError:
        logger.error('Failed to reach the Webcandy API. Please check the '
                     '--host and --app-port options.')
        return 1

    if response.status_code != 200:
        logger.error(f'Received status {response.status_code}: '
                     f'{response.content.decode("utf-8")}')
        return 1

    access_token = response.json()['token']
    logger.debug(f'Using token {access_token}')

    fc_server = FadecandyServer()
    fc_server.start()  # won't start if another instance is already running

    signal.signal(signal.SIGINT, signal.SIG_DFL)  # allow keyboard interrupt

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        start_client(host, proxy_port, access_token, client_id, pattern_names))

    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)
