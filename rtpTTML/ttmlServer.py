from datetime import datetime
import socket
from random import randrange
from rtp import RTP, PayloadType  # type: ignore
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore

EPOCH = datetime.utcfromtimestamp(0)


class TTMLServer:
    def __init__(
       self,
       address,
       port,
       payloadType=PayloadType.DYNAMIC_96,
       initialSeqNum=None,
       tsOffset=None):
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

    def nextSeqNum(self):
        return self.nextSeqNum

    def generateRTPPacket(self, doc, time):
        now_ms = int((time - EPOCH).total_seconds() * 1000)
        timestamp = now_ms + self.tsOffset
        truncatedTS = timestamp % 2**32

        packet = RTP(
            timestamp=truncatedTS,
            sequenceNumber=self.nextSeqNum,
            payload=RTPPayload_TTML(userDataWords=doc).toBytearray(),
            marker=True,
            payloadType=self.payloadType
        )
        self.nextSeqNum += 1

        return packet

    def sendDoc(self, doc, time):
        packet = self.generateRTPPacket(doc, time)

        self.socket.sendto(packet.toBytes(), (self.address, self.port))
