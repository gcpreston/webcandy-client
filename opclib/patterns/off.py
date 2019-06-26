from .solid_color import SolidColor


class Off(SolidColor):
    """
    Turn the LEDs off.
    """

    @property
    def name(self) -> str:
        return 'off'

    def __init__(self):
        super().__init__('#000000')  # put black pixels
