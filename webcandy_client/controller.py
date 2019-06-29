import json
import multiprocessing
import logging
import argparse

from opclib.interface import LightConfig
from opclib.fcserver import FadecandyServer

logger = logging.getLogger('wc-controller')
logger.setLevel(logging.INFO)


def _execute(**kwargs) -> None:
    """
    Run the specified lighting configuration.

    :param kwargs: keyword arguments to pass to ``LightConfig`` factory
    :raises ValueError: if the specified configuration was not given properly
        formatted data
    """
    try:
        LightConfig.factory(**kwargs).run()
    except Exception as e:
        logger.error(e)


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
        logger.info(f'Attempting to run configuration: {kwargs}')
        self._set_current_proc(target=_execute, kwargs=kwargs)

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
            logger.debug(f'Terminating {self._current_proc}')
            self._current_proc.terminate()
            return True
        return False


def get_argument_parser() -> argparse.ArgumentParser:
    """
    Generate the command-line argument parser.
    """
    # TODO: Allow for arbitrary command-line argumnets. This would be useful if
    #   a user wants to add their own lighting configuration and it contains
    #   new JSON options, that way they don't have to update controller code.
    parser = argparse.ArgumentParser(
        description='Offline controller for Fadecandy server. These arguments '
                    'are used to either import or generate a JSON lighting '
                    'configuration which will be run via opclib.')
    parser.add_argument('-f', '--file', metavar='PATH',
                        help='path of JSON file specifying light configuration '
                             '(other arguments such as --color take precedent)')
    parser.add_argument('-p', '--pattern', metavar='PATTERN',
                        help='lighting pattern name to use')
    parser.add_argument('-s', '--strobe', action='store_true',
                        help='add a strobe effect')
    parser.add_argument('-c', '--color', metavar='COLOR',
                        help='color to use (#RRGGBB format)')
    parser.add_argument('-cl', '--color-list', nargs='+', metavar='COLOR',
                        help='list of colors to use (#RRGGBB format)')
    return parser


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] (%(name)s) %(levelname)s: %(message)s')

    parser = get_argument_parser()
    args = parser.parse_args()

    config = dict()
    if args.file:
        with open(args.file) as file:
            config = json.load(file)

    for field in ['pattern', 'strobe', 'color', 'color_list']:
        if getattr(args, field):
            config[field] = getattr(args, field)

    if config:
        server = FadecandyServer()
        server.start()  # start Fadecandy server if not already running

        control = Controller()
        control.run(**config)
        # TODO: Fix conflict when mixing dynamic configs across a separate
        #   client and controller processes
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
