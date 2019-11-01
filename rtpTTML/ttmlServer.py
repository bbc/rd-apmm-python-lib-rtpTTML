from datetime import datetime
from copy import deepcopy
import socket
from rtp import RTP, PayloadType
from rtpPayload_ttml import RTPPayload_TTML

EPOCH = datetime.utcfromtimestamp(0)


class TTMLServer:
    def __init__(self, address, port):
        self.baseRTP = RTP(
            marker=True,
            payloadType=PayloadType.DYNAMIC_96
        )

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = address
        self.port = port

    def nextSeqNum(self):
        return self.baseRTP.sequenceNumber + 1

    def generateRTPPacket(self, doc, time):
        now_ms = int((time - EPOCH).total_seconds() * 1000.0)

        self.baseRTP.sequenceNumber += 1
        nextRTP = deepcopy(self.baseRTP)
        nextRTP.timeBase = now_ms % 2**32

        nextRTP.payload = RTPPayload_TTML(userDataWords=doc).toBytearray()

        return nextRTP

    def sendDoc(self, doc, time):
        packet = self.generateRTPPacket(doc, time)
        self.socket.sendto(bytes(packet), (self.address, self.port))
