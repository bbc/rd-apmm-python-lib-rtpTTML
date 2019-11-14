from typing import Union, List
from datetime import datetime
import socket
from random import randrange
from rtp import RTP, PayloadType  # type: ignore
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore

EPOCH = datetime.utcfromtimestamp(0)


class TTMLServer:
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

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

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

    def sendDoc(self, doc: str, time: datetime) -> None:
        rtpTs = self._datetimeToRTPTs(time)
        docFragments = self._fragmentDoc(doc, self._maxFragmentSize)

        lastIndex = len(docFragments) - 1
        for x in range(len(docFragments)):
            isLast = (x == lastIndex)
            packet = self._generateRTPPacket(docFragments[x], rtpTs, isLast)

            self._socket.sendto(packet.toBytes(), (self._address, self._port))
