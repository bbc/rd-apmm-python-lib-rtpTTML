import socket
from rtp import RTP  # type: ignore
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore

MAX_SEQ_NUM = (2**16) - 1


class TTMLClient:
    def __init__(self, port, callback, recvBufSize=None, timeout=None):
        self.fragments = {}
        self.curTimestamp = None
        self.port = port
        self.callback = callback

        if recvBufSize is None:
            self.recvBufSize = 2**16
        else:
            self.recvBufSize = recvBufSize

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if timeout is None:
            # Set the timeout value of the socket to 30sec
            self.socket.settimeout(30)
        else:
            self.socket.settimeout(timeout)

        self.socket.bind(('', self.port))

    def unloopSeqNum(self, prevNum, thisNum):
        perC10 = MAX_SEQ_NUM * 0.1
        perC90 = MAX_SEQ_NUM * 0.9

        if (thisNum > perC10) or (prevNum < perC90):
            return thisNum

        return thisNum + MAX_SEQ_NUM

    def keysComplete(self):
        minKey = min(self.fragments)
        maxKey = max(self.fragments)
        expectedLen = maxKey - minKey + 1

        return len(self.fragments) == expectedLen

    def processFragments(self):
        if not self.keysComplete():
            # Discard
            self.fragments = {}
            return

        # Reconstruct the document
        doc = ""

        for k, v in self.fragments.items():
            doc += v

        # We've finished re-constructing this document.
        # Discard the fragments.
        self.fragments = {}

        self.callback(doc, self.curTimestamp)

    def run(self):
        startSeqNum = None
        prevSeqNum = None

        while True:
            data = self.socket.recv(self.recvBufSize)

            packet = RTP().fromBytes(data)

            # Initialise or new doc. When initialising, we'll asume the first
            # packet is the start of the doc. It'll be found to be invalid
            # later if we were wrong. New TS means a new document
            if startSeqNum is None or packet.timestamp != self.curTimestamp:
                # If we haven't processed by now, document is incomplete
                # so we discard it
                self.fragments = {}

                # Assume this packet is the first. If we're wrong, the doc
                # won't be TTML valid when decoded anyway
                if startSeqNum is None:
                    prevSeqNum = packet.sequenceNumber - 1
                startSeqNum = packet.sequenceNumber
                self.curTimestamp = packet.timestamp

            payload = RTPPayload_TTML().fromBytearray(packet.payload)

            unloopedSeqNum = self.unloopSeqNum(
                prevSeqNum, packet.sequenceNumber)

            self.fragments[unloopedSeqNum] = payload.userDataWords

            prevSeqNum = unloopedSeqNum

            self.processFragments()
