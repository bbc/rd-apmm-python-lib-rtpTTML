import socket
from rtp import RTP  # type: ignore
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore


class TTMLClient:
    def __init__(self, port):
        self.port = port

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set the timeout value of the socket to 30sec
        self.socket.settimeout(30)
        self.socket.bind(('', self.port))

    def run(self, callback):
        while True:
            data = bytearray(self.socket.recv(2**16))

            packet = RTP().fromBytearray(data)
            payload = RTPPayload_TTML().fromBytearray(packet.payload)
            doc = payload.userDataWords

            callback(doc)
