from __future__ import annotations
from typing import List, Optional, Tuple, cast
from datetime import datetime
import socket
import asyncio
from random import randrange
from rtp import RTP, PayloadType  # type: ignore
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore

EPOCH = datetime.utcfromtimestamp(0)


class AsyncTTMLTransmitterConnection (object):
    def __init__(self, parent: TTMLTransmitter) -> None:
        self._parent = parent
        self._transport: Optional[asyncio.DatagramTransport]
        self._protocol: Optional[asyncio.DatagramProtocol]

    @property
    def nextSeqNum(self):
        return self._parent._nextSeqNum

    async def _open(self) -> None:
        loop = asyncio.get_event_loop()

        # Typeshed incorrectly assumes Base Transport and Protocol types
        self._transport, self._protocol = cast(
            Tuple[asyncio.DatagramTransport, asyncio.DatagramProtocol],
            await loop.create_datagram_endpoint(
                asyncio.DatagramProtocol,
                remote_addr=(self._parent._address, self._parent._port),
                family=socket.AF_INET))

    async def _close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    async def sendDoc(self, doc: str, time: datetime) -> None:
        if self._transport is None:
            return

        for packet in self._parent._packetiseDoc(doc, time):
            self._transport.sendto(packet.toBytes())


class SyncTTMLTransmitterConnection (object):
    def __init__(self, parent: TTMLTransmitter) -> None:
        self._parent = parent
        self._socket: Optional[socket.socket]

    @property
    def nextSeqNum(self):
        return self._parent._nextSeqNum

    def _open(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _close(self) -> None:
        if self._socket is not None:
            self._socket.close()

    def sendDoc(self, doc: str, time: datetime) -> None:
        if self._socket is None:
            return

        for packet in self._parent._packetiseDoc(doc, time):
            self._socket.sendto(
                packet.toBytes(),
                (self._parent._address, self._parent._port))


class TTMLTransmitter:
    def __init__(
       self,
       address: str,
       port: int,
       maxFragmentSize: int = 1200,
       payloadType: PayloadType = PayloadType.DYNAMIC_96,
       initialSeqNum: int = None,
       tsOffset: Optional[int] = None) -> None:
        self._address = address
        self._port = port
        self._maxFragmentSize = maxFragmentSize
        self._payloadType = payloadType

        if initialSeqNum is not None:
            self._nextSeqNum = initialSeqNum
        else:
            self._nextSeqNum = randrange(2**16)

        if tsOffset is not None:
            self._tsOffset = tsOffset
        else:
            self._tsOffset = randrange(2**32)

        self._async_connection: Optional[AsyncTTMLTransmitterConnection] = None
        self._sync_connection: Optional[SyncTTMLTransmitterConnection] = None

    async def __aenter__(self) -> AsyncTTMLTransmitterConnection:
        self._async_connection = AsyncTTMLTransmitterConnection(self)
        await self._async_connection._open()
        return self._async_connection

    async def __aexit__(self, *args) -> None:
        if self._async_connection is not None:
            await self._async_connection._close()
            self._async_connection = None

    def __enter__(self) -> SyncTTMLTransmitterConnection:
        self._sync_connection = SyncTTMLTransmitterConnection(self)
        self._sync_connection._open()
        return self._sync_connection

    def __exit__(self, *args) -> None:
        if self._sync_connection is not None:
            self._sync_connection._close()
            self._sync_connection = None

    @property
    def nextSeqNum(self) -> int:
        return self._nextSeqNum

    def _fragmentDoc(self, doc: str, maxLen: int) -> List[RTP]:
        fragments = []
        thisStart = 0

        if doc == "":
            return []

        while True:
            thisEnd = thisStart + maxLen
            while len(bytearray(doc[thisStart:thisEnd], "utf-8")) > maxLen:
                thisEnd -= 1

            fragments.append(doc[thisStart:thisEnd])

            if thisEnd >= len(doc):
                break

            thisStart = thisEnd

        return fragments

    def _datetimeToRTPTs(self, time: datetime) -> int:
        now_ms = int((time - EPOCH).total_seconds() * 1000)
        timestamp = now_ms + self._tsOffset
        truncatedTS = timestamp % 2**32

        return truncatedTS

    def _generateRTPPacket(self, doc: str, time: int, marker: bool) -> RTP:
        packet = RTP(
            timestamp=time,
            sequenceNumber=self._nextSeqNum,
            payload=RTPPayload_TTML(userDataWords=doc).toBytearray(),
            marker=marker,
            payloadType=self._payloadType
        )
        self._nextSeqNum += 1

        return packet

    def _packetiseDoc(self, doc, time):
        packets = []

        rtpTs = self._datetimeToRTPTs(time)
        docFragments = self._fragmentDoc(doc, self._maxFragmentSize)

        lastIndex = len(docFragments) - 1
        for x in range(len(docFragments)):
            isLast = (x == lastIndex)
            packets.append(
                self._generateRTPPacket(docFragments[x], rtpTs, isLast))

        return packets
