#!/usr/bin/python
#
# Copyright 2018 British Broadcasting Corporation
#
# This is an internal BBC tool and is not licensed externally
# If you have received a copy of this erroneously then you do
# not have permission to reproduce it.

"""\
High level python library for transmitting/receiving TTML over RTP.
"""

from .ttmlTransmitter import TTMLTransmitter
from .ttmlReceiver import TTMLReceiver

__all__ = ["TTMLTransmitter", "TTMLReceiver"]

template = True
