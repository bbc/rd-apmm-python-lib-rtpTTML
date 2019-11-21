from typing import Union, List, Optional, Generator
from datetime import datetime
import socket
from random import randrange
from rtp import RTP, PayloadType  # type: ignore
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore
import asyncio

EPOCH = datetime.utcfromtimestamp(0)


class AsyncTTMLSenderConnection (object):
    def __init__(self, parent: "TTMLSender"):
        self._parent = parent
        self._writer: Optional[asyncio.StreamWriter]

    async def _open(self) -> None:
        (_, self._writer) = await asyncio.open_connection(self._parent._address,
                                                          self._parent._port,
                                                          family=socket.AF_INET,
                                                          proto=socket.SOCK_DGRAM)

    async def _close(self) -> None:
        if self._writer is not None:
            self._writer.close()

    async def sendDoc(self, doc: str, time: datetime) -> None:
        for packet in self._parent._packetise_doc(doc, time):
            self._writer.write(packet.toBytes())
        await self._writer.drain()


class SyncTTMLSenderConnection (object):
    def __init__(self, parent: "TTMLSender"):
        self._parent = parent
        self._socket: Optional[socket.socket]

    def _open(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _close(self) -> None:
        if self._socket is not None:
            self._socket.close()

    def sendDoc(self, doc: str, time: datetime) -> None:
        for packet in self._parent._packetise_doc(doc, time):
            self._socket.sendto(packet.toBytes(), (self._parent.address, self._parent._port))
        await self._writer.drain()


class TTMLSender (object):
    def __init__(
       self,
       address: str,
       port: int,
       maxFragmentSize: int = 1200,
       payloadType: PayloadType = PayloadType.DYNAMIC_96,
       initialSeqNum: Union[int, None] = None,
       tsOffset: Union[int, None] = None):
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

        self._async_connection: Optional[AsyncTTMLSenderConnection] = None
        self._sync_connection: Optional[SyncTTMLSenderConnection] = None
        # self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    async def __aenter__(self) -> AsyncTTMLSenderConnection:
        self._async_connection = AsyncTTMLSenderConnection(self)
        await self._async_connection._open()
        return self._async_connection

    async def __aexit__(self, *args) -> None:
        if self._async_connection is not None:
            await self._async_connection._close()
            self._async_connection = None

    def __enter__(self) -> SyncTTMLSenderConnection:
        self._sync_connection = SyncTTMLSenderConnection(self)
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

    def _packetise_doc(self, doc: str, time: datetime) -> Generator[RTP, None, None]:
        rtpTs = self._datetimeToRTPTs(time)
        docFragments = self._fragmentDoc(doc, self._maxFragmentSize)

        lastIndex = len(docFragments) - 1
        for x in range(len(docFragments)):
            isLast = (x == lastIndex)
            packet = self._generateRTPPacket(docFragments[x], rtpTs, isLast)

            yield packet
