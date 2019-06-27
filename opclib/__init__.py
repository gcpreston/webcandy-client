# TODO: Separate opclib, make it a separate library and repository
from . import patterns
from .fcserver import FadecandyServer

pattern_names = patterns.__all__
modifier_names = patterns.modifiers.__all__

__all__ = [
    'pattern_names',
    'modifier_names',
    'FadecandyServer'
] + patterns.__all__
