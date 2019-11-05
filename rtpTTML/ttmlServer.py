from datetime import datetime
import socket
from rtp import RTP, PayloadType  # type: ignore
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore

EPOCH = datetime.utcfromtimestamp(0)


class TTMLServer:
    def __init__(self, address, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.address = address
        self.port = port

        self.prevSeqNum = 0

    def nextSeqNum(self):
        return self.prevSeqNum + 1

    def generateRTPPacket(self, doc, time):
        now_ms = int((time - EPOCH).total_seconds() * 1000.0)
        self.prevSeqNum += 1

        packet = RTP(
            timestamp=now_ms % 2**32,
            sequenceNumber=self.prevSeqNum,
            payload=RTPPayload_TTML(userDataWords=doc).toBytearray(),
            marker=True,
            payloadType=PayloadType.DYNAMIC_96
        )

        return packet

    def sendDoc(self, doc, time):
        packet = self.generateRTPPacket(doc, time)
        self.socket.sendto(
            bytes(packet.toBytearray()),
            (self.address, self.port))
