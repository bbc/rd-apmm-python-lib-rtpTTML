from __future__ import annotations
from typing import List, Callable, Union, Dict, Optional, Tuple, cast
import socket
import asyncio
from collections import OrderedDict
from rtp import RTP  # type: ignore
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore

MAX_SEQ_NUM = (2**16) - 1


class OrderedBuffer:
    def __init__(self, maxSize: int = 5, maxKey: int = MAX_SEQ_NUM) -> None:
        self._initialised = False
        self._maxSize = maxSize
        self._maxKey = maxKey
        self._mostRecentKey = 0
        self._buffer: Dict[int, RTP] = {}

    def _nextKey(self) -> int:
        nextKey = self._mostRecentKey + 1

        return nextKey % (self._maxKey + 1)

    def _ffwMostRecent(self) -> None:
        if len(self._buffer) == 0:
            return

        while self._nextKey() not in self._buffer:
            self._mostRecentKey = self._nextKey()

    def pop(self) -> RTP:
        ret = self._buffer.pop(self._nextKey(), None)
        self._mostRecentKey = self._nextKey()

        return ret

    def push(self, key: int, value: RTP) -> None:
        self._buffer[key] = value

        if not self._initialised:
            self._mostRecentKey = key - 1
            self._initialised = True

        if len(self._buffer) >= self._maxSize:
            self._ffwMostRecent()

        if len(self._buffer) > self._maxSize:
            self.pop()

    def available(self) -> bool:
        available = False

        if self._nextKey() in self._buffer:
            available = True

        return available

    def get(self) -> List[RTP]:
        ret = []

        while self.available():
            ret.append(self.pop())

        return ret

    def pushGet(self, key: int, value: RTP) -> List[RTP]:
        self.push(key, value)
        return self.get()


class TTMLDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, parent: TTMLReceiver) -> None:
        self._parent = parent
        super().__init__()

    def datagram_received(self, data, addr) -> None:
        self._parent._processData(data)


class TTMLReceiver:
    def __init__(
       self,
       port: int,
       callback: Callable[[str, int], None],
       recvBufSize: int = None,
       timeout: Union[float, None] = None) -> None:
        self._fragments: Dict[int, RTP] = OrderedDict()
        self._curTimestamp = 0
        self._port = port
        self._callback = callback
        self._socket: Optional[socket.socket]
        self._transport: Optional[asyncio.DatagramTransport]
        self._protocol: Optional[TTMLDatagramProtocol]

        if recvBufSize is None:
            self._recvBufSize = 2**16
        else:
            self._recvBufSize = recvBufSize

        self._packetBuff = OrderedBuffer()

        if timeout is None:
            self._timeout = 30.0
        else:
            self._timeout = timeout

    def _unloopSeqNum(self, prevNum: int, thisNum: int) -> int:
        loopOffset = MAX_SEQ_NUM + 1

        prevNumMod = prevNum % loopOffset

        prevNumOffset = prevNum - prevNumMod  # prevNum may already have looped

        # Margins for detecting when number has looped
        perC10 = MAX_SEQ_NUM * 0.1
        perC90 = MAX_SEQ_NUM * 0.9

        # Account for missing packets around edges
        if (thisNum > perC10) or (prevNumMod < perC90):
            return thisNum + prevNumOffset

        # Num has looped
        return thisNum + loopOffset + prevNumOffset

    def _keysComplete(self) -> bool:
        if len(self._fragments) == 0:
            return False

        minKey = min(self._fragments)
        maxKey = max(self._fragments)
        expectedLen = maxKey - minKey + 1

        return len(self._fragments) == expectedLen

    def _processFragments(self) -> None:
        if not self._keysComplete():
            # Discard
            self._fragments.clear()
            return

        # Reconstruct the document
        doc = ""

        for k, v in self._fragments.items():
            doc += v

        # We've finished re-constructing this document.
        # Discard the fragments.
        self._fragments.clear()

        self._callback(doc, self._curTimestamp)

    def _processPacket(self, packet: RTP) -> None:
        # New TS means a new document
        if self._curTimestamp != packet.timestamp:
            # If we haven't processed by now, document is incomplete
            # so we discard it
            self._fragments.clear()

            # Assume this packet is the first in doc. If we're wrong, the doc
            # won't be valid TTML when decoded anyway
            self._curTimestamp = packet.timestamp

        seqNumber = packet.sequenceNumber
        if len(self._fragments) > 0:
            seqNumber = self._unloopSeqNum(
                max(self._fragments), packet.sequenceNumber)

        payload = RTPPayload_TTML().fromBytearray(packet.payload)
        self._fragments[seqNumber] = payload.userDataWords

    def _processData(self, data: bytes) -> None:
        newPacket = RTP().fromBytes(data)

        packets = self._packetBuff.pushGet(
            newPacket.sequenceNumber, newPacket)

        for packet in packets:
            self._processPacket(packet)

            if packet.marker:
                self._processFragments()

    def run(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(self._timeout)
        self._socket.bind(('', self._port))

        while True:
            data = self._socket.recv(self._recvBufSize)
            self._processData(data)

    def async_close(self) -> None:
        if self._transport is not None:
            self._transport.close()

    async def async_run(self) -> None:
        loop = asyncio.get_event_loop()

        # Typeshed incorrectly assumes Base Transport and Protocol types
        # Typeshed also incorrectly says local_addr's address can't be None
        self._transport, self._protocol = cast(
            Tuple[asyncio.DatagramTransport, TTMLDatagramProtocol],
            await loop.create_datagram_endpoint(
                lambda: TTMLDatagramProtocol(self),
                local_addr=(None, self._port),  # type: ignore
                family=socket.AF_INET))
