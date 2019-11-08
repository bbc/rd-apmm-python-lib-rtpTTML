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
       payloadType: PayloadType = PayloadType.DYNAMIC_96,
       initialSeqNum: Union[int, None] = None,
       tsOffset: Union[int, None] = None):
        self.address = address
        self.port = port
        self.payloadType = payloadType

        if initialSeqNum is not None:
            self.nextSeqNum = initialSeqNum
        else:
            self.nextSeqNum = randrange((2**16)-1)

        if tsOffset is not None:
            self.tsOffset = tsOffset
        else:
            self.tsOffset = randrange((2**32)-1)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def fragmentDoc(self, doc: str, maxLen: int) -> List[RTP]:
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

    def generateRTPPacket(self, doc: str, time: int, marker: bool) -> RTP:
        packet = RTP(
            timestamp=time,
            sequenceNumber=self.nextSeqNum,
            payload=RTPPayload_TTML(userDataWords=doc).toBytearray(),
            marker=marker,
            payloadType=self.payloadType
        )
        self.nextSeqNum += 1

        return packet

    def sendDoc(self, doc: str, time: datetime) -> None:
        now_ms = int((time - EPOCH).total_seconds() * 1000)
        timestamp = now_ms + self.tsOffset
        truncatedTS = timestamp % 2**32

        maxFragmentSize = 1200  # TODO: measure this or select a sensible val

        docFragments = self.fragmentDoc(doc, maxFragmentSize)

        for x in range(len(docFragments)):
            isLast = x == (len(docFragments) - 1)
            packet = self.generateRTPPacket(
                docFragments[x], truncatedTS, isLast)

            self.socket.sendto(packet.toBytes(), (self.address, self.port))
