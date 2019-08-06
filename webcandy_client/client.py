import sys
import signal
import inspect
import asyncio
import json
import logging
import argparse

import requests
import websockets
import opclib.patterns

from typing import Type, List, Dict

from opclib import pattern_names, FadecandyServer
from opclib.interface import LightConfig, StaticLightConfig, DynamicLightConfig
from webcandy_client.controller import Controller

logger = logging.getLogger('wc-client')
logger.setLevel(logging.INFO)


def process_config(pattern: Type[LightConfig]) -> Dict:
    """
    Put necessary information about a `LightConfig` subclass into a dictionary.
    """
    if issubclass(pattern, StaticLightConfig):
        config_type = 'static'
    elif issubclass(pattern, DynamicLightConfig):
        config_type = 'dynamic'
    else:
        config_type = 'unknown'

    args = inspect.getfullargspec(pattern).args
    takes = None
    if 'color' in args:
        takes = 'color'
    elif 'color_list' in args:
        takes = 'color_list'

    return {
        'name': pattern.__name__,
        'type': config_type,
        'takes': takes
    }


def gen_patterns(patterns: List[str]) -> List[Dict]:
    """
    Generate the value to go in the "patterns" field of the data to send the
    server.

    :param patterns: names of available patterns
    :return: the list of patterns reformatted according to `process_config`
    """
    return [process_config(getattr(opclib.patterns, p)) for p in patterns]


async def start_client(
        host: str,
        port: int,
        token: str,
        client_name: str,
        patterns: List[Dict]) -> None:
    """
    Initiate the client connection.
    """
    ws_addr = f'ws://{host}'
    if port != 80:
        ws_addr += f':{port}'

    logger.info(f'Connecting to {ws_addr}...')
    async with websockets.connect(ws_addr) as websocket:
        logger.info(f'Connected to server')

        data = json.dumps(
            {'token': token, 'client_name': client_name,
             'patterns': patterns})
        logger.debug(f'Sending {data}')
        await websocket.send(data)

        logger.info(f'Sent token, client_name: {client_name!r}, '
                    f'and patterns: {patterns}')

        controller = Controller()

        try:
            async for message in websocket:
                try:
                    parsed = json.loads(message)
                    logger.debug(f'Received JSON: {parsed}')
                    controller.run(host, port, **parsed)
                except json.decoder.JSONDecodeError:
                    # TODO: Better formatting of messages sent from server
                    # don't show data format message to end user
                    if not message.startswith('[Webcandy]'):
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
    p.add_argument('client_name', help='the name to assign this client')
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

    host = args.host or 'webcandy.io'
    proxy_port = args.proxy_port or 80
    client_name = args.client_name
    app_port = args.app_port or 443
    unsecure = args.unsecure

    # get access token from username and password
    if app_port == 443:
        addr = f'https://{host}/api/token'
    else:
        addr = f'https://{host}:{app_port}/api/token'

    logger.info(f'Getting access token from {addr}...')
    try:
        response = requests.post(addr,
                                 json={'username': args.username,
                                       'password': args.password},
                                 verify=not unsecure)
        logger.info(f'Access token received')
    except requests.exceptions.ConnectionError:
        logger.error(f'Failed to reach the Webcandy API ({addr}). Please make '
                     'sure the site is online, or check the --host and '
                     '--app-port options.')
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
        start_client(host, proxy_port, access_token, client_name,
                     gen_patterns(pattern_names)))

    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)
