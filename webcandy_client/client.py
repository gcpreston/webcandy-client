import sys
import os
import asyncio
import json
import requests
import signal
import logging
import argparse
import websockets

from typing import List

from webcandy_client.controller import Controller
from webcandy_client.fcserver import FadecandyServer
from webcandy_client.definitions import OPCLIB_DIR


def get_pattern_names() -> List[str]:
    """
    Get the names of available Fadecandy lighting patterns.
    :return: a list of names of existing patterns
    """
    ignore = {'__pycache__', '__init__.py', 'off.py', 'strobe.py'}
    return list(map(lambda e: e[:-3],
                    filter(lambda e: e not in ignore,
                           os.listdir(OPCLIB_DIR + '/patterns'))))


async def start_client(
        host: str,
        port: int,
        token: str,
        client_id: str,
        patterns: List[str]) -> None:
    """
    Initiate the client connection.
    """
    ws_addr = f'ws://{host}:{port}'

    async with websockets.connect(ws_addr) as websocket:
        logging.info(f'Connected to server {ws_addr}')

        data = json.dumps(
            {'token': token, 'client_id': client_id,
             'patterns': patterns})
        await websocket.send(data)

        logging.info(
            f'Sent token, client_id: {client_id!r}, and patterns: {patterns}')

        controller = Controller()

        try:
            async for message in websocket:
                try:
                    parsed = json.loads(message)
                    logging.debug(f'Received JSON: {parsed}')
                    controller.run(**parsed)
                except json.decoder.JSONDecodeError:
                    # TODO: Better formatting of messages sent from server
                    logging.info(f'Received text: {message}')
        except websockets.ConnectionClosed as err:
            message = (
                f'Server closed connection, code: {err.code}, '
                f'reason: {err.reason or "no reason given"}'
            )
            if err.code in {1000, 1001}:
                logging.info(message)
            else:
                logging.error(message)


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
                        '(dev default: 127.0.0.1)')
    p.add_argument('--port', metavar='PORT', type=int,
                   help='the port the Webcandy proxy server is running on'
                        '(default: 6543)')
    p.add_argument('--app-port', metavar='PORT', type=int,
                   help='the port the Webcandy app is running on '
                        '(dev default: 5000)')
    return p


def main():
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s: %(message)s')

    parser = get_argument_parser()
    args = parser.parse_args()

    host = args.host or '127.0.0.1'
    port = args.port or 6543
    client_id = args.client_id
    app_port = args.app_port or 5000

    # get access token from username and password
    try:
        response = requests.post(f'http://{host}:{app_port}/api/token',
                                 json={'username': args.username,
                                       'password': args.password})
    except requests.exceptions.ConnectionError:
        logging.error('Failed to reach the Webcandy API. Please check the '
                      '--host and --app-port options.')
        sys.exit(1)

    if response.status_code != 200:
        logging.error(f'Received status {response.status_code}: '
                      f'{response.content.decode("utf-8")}')
        sys.exit(1)

    access_token = response.json()['token']
    logging.debug(f'Using token {access_token}')

    fc_server = FadecandyServer()
    fc_server.start()  # won't start if another instance is already running

    signal.signal(signal.SIGINT, signal.SIG_DFL)  # allow keyboard interrupt

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        start_client(host, port, access_token, client_id,
                     get_pattern_names()))


if __name__ == '__main__':
    main()
