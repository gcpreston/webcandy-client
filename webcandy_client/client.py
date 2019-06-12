import sys
import os
import asyncio
import json
import requests
import signal
import logging
import argparse

from typing import List

from webcandy_client.controller import Controller
from webcandy_client.fcserver import FadecandyServer
from webcandy_client.definitions import OPCLIB_DIR


def _get_pattern_names() -> List[str]:
    """
    Get the names of available Fadecandy lighting patterns.
    :return: a list of names of existing patterns
    """
    ignore = {'__pycache__', '__init__.py', 'off.py', 'strobe.py'}
    return list(map(lambda e: e[:-3],
                    filter(lambda e: e not in ignore,
                           os.listdir(OPCLIB_DIR + '/patterns'))))


class WebcandyClientProtocol(asyncio.Protocol):
    """
    Protocol describing communication of a Webcandy client.
    """

    def __init__(self, access_token: str, client_id: str, control: Controller,
                 on_con_lost: asyncio.Future):
        self._token = access_token
        self._id = client_id
        self._control = control
        self._on_con_lost = on_con_lost

    def connection_made(self, transport: asyncio.Transport) -> None:
        """
        When a connection is made, the send the server JSON data describing the
        patterns it has available.
        """
        peername = transport.get_extra_info('peername')
        logging.info(f'Connected to server {":".join(map(str, peername))}')
        patterns = _get_pattern_names()
        data = json.dumps(
            {'token': self._token, 'client_id': self._id, 'patterns': patterns})
        transport.write(data.encode())
        logging.info(
            f'Sent token, client_id: {self._id!r}, and patterns: {patterns}')

    def data_received(self, data: bytes) -> None:
        """
        Received data is assumed to be JSON describing a lighting configuration.
        Upon receiving data, attempt to decode it as JSON, and if successful,
        pass the parsed data to a ``Controller`` to attempt to run the described
        lighting configuration.
        """
        try:
            parsed = json.loads(data.decode())
            logging.debug(f'Received JSON: {parsed}')
            self._control.run(**parsed)
        except json.decoder.JSONDecodeError:
            # TODO: Better formatting of messages sent from server
            logging.info(f'Received text: {data.decode()}')

    def connection_lost(self, exc) -> None:
        logging.info('The server closed the connection')
        self._on_con_lost.set_result(True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s: %(message)s')

    parser = argparse.ArgumentParser(
        description='Webcandy client to connect to a running Webcandy server.')
    parser.add_argument('username', help='the username to log in with')
    parser.add_argument('password', help='the password to log in with')
    parser.add_argument('client_id', help='the ID to assign this client')
    parser.add_argument('--host', metavar='ADDRESS',
                        help='the address of the server to connect to'
                             '(default: 127.0.0.1)')
    parser.add_argument('--port', metavar='PORT', type=int,
                        help='the port the proxy server is running on'
                             '(default: 6543)')
    parser.add_argument('--app-port', metavar='PORT', type=int,
                        help='the port the Webcandy app is running on')
    cmd_args = parser.parse_args()

    cmd_host = cmd_args.host or '127.0.0.1'
    cmd_port = cmd_args.port or 6543
    cmd_app_port = cmd_args.app_port or 5000

    # get access token from username and password
    try:
        response = requests.post(f'http://{cmd_host}:{cmd_app_port}/api/token',
                                 json={'username': cmd_args.username,
                                       'password': cmd_args.password})
    except requests.exceptions.ConnectionError:
        logging.error('Failed to reach the Webcandy API. Please check the '
                      '--host and --app-port options.')
        sys.exit(1)

    if response.status_code != 200:
        logging.error(f'Received status {response.status_code}: '
                      f'{response.content.decode("utf-8")}')
        sys.exit(1)

    token = response.json()['token']
    logging.debug(f'Using token {token}')

    # create and start Fadecandy server
    fc_server = FadecandyServer()
    fc_server.start()

    # set up WebcandyClientProtocol
    async def start_protocol():
        loop = asyncio.get_running_loop()
        on_con_lost = loop.create_future()

        try:
            transport, protocol = await loop.create_connection(
                lambda: WebcandyClientProtocol(token, cmd_args.client_id,
                                               Controller(), on_con_lost),
                cmd_host, cmd_port)
        except ConnectionRefusedError:
            logging.error('Failed to connected to the proxy server. Please '
                          'check that the proxy server is running on the port '
                          'specified in the --port option.')
            sys.exit(1)

        # wait until the protocol signals that the connection is lost, then
        # close the transport stop the Fadecandy server
        try:
            await on_con_lost
        finally:
            transport.close()
            fc_server.stop()


    signal.signal(signal.SIGINT, signal.SIG_DFL)  # allow keyboard interrupt
    asyncio.run(start_protocol())  # run the client