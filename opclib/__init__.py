# TODO: Separate opclib, make it a separate library and repository
import opclib.patterns

from opclib.fcserver import FadecandyServer

pattern_names = [str(p.name) for p in opclib.patterns.__all__]

__all__ = opclib.patterns.__all__ + [pattern_names, FadecandyServer]
