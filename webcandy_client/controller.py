import multiprocessing
import json
import logging
import argparse

from opclib.interface import LightConfig
from webcandy_client.fcserver import FadecandyServer


def _execute(**kwargs) -> None:
    """
    Run the specified lighting configuration.

    :param kwargs: keyword arguments to pass to ``LightConfig`` factory
    :raises ValueError: if the specified configuration was not given properly
        formatted data
    """
    LightConfig.factory(**kwargs).run()


class Controller:
    """
    Controls for lighting configuration.
    """

    _current_proc: multiprocessing.Process = None

    def run(self, **kwargs) -> None:
        """
        Run a lighting configuration . Requires a Fadecandy
        server to be started.

        :param kwargs: arguments to pass to the specified light config
        """
        logging.info(f'Attempting to run configuration: {kwargs}')
        self._set_current_proc(target=_execute, kwargs=kwargs)

    def run_json(self, fp: str) -> None:
        """
        Run a lighting configuration specified in a JSON file.
        :param fp: path to the configuration file
        """
        with open(fp) as file:
            config = json.load(file)

        logging.info(f'Attempting to run configuration: {config}')
        self._set_current_proc(target=_execute, kwargs=config)

    def _set_current_proc(self, **kwargs) -> None:
        """
        Terminate the current process and start a new one. ``kwargs`` are passed
        to ``multiprocessing.Process``.
        :param kwargs: keyword arguments to specify the new process
        """
        self._terminate_current_proc()
        self._current_proc = multiprocessing.Process(**kwargs)
        self._current_proc.start()

    def _terminate_current_proc(self) -> bool:
        """
        Terminate the current running light configuration process, if one is
        running.

        :return: ``True`` if a process was terminated; ``False`` otherwise
        """
        if self._current_proc and self._current_proc.is_alive():
            logging.debug(f'Terminating {self._current_proc}')
            self._current_proc.terminate()
            return True
        return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s] %(levelname)s: %(message)s')

    # Allow the direct, local running of lighting configurations
    parser = argparse.ArgumentParser(
        description='Offline controller for Fadecandy server.')
    parser.add_argument('-f', '--file', metavar='PATH',
                        help='path of JSON file specifying light configuration')
    cmd_args = parser.parse_args()

    if cmd_args.file:
        server = FadecandyServer()
        server.start()  # start Fadecandy server if not already running

        control = Controller()
        control.run_json(cmd_args.file)
        # TODO: Fix conflict when mixing dynamic configs across a separate
        #     client and controller processes
    else:
        parser.print_help()
