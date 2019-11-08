import socket
from rtp import RTP  # type: ignore
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore

MAX_SEQ_NUM = (2**16) - 1


class OrderedBuffer:
    def __init__(self, maxSize=5, maxKey=MAX_SEQ_NUM):
        self.maxSize = maxSize
        self.maxKey = maxKey
        self.mostRecentKey = None
        self.buffer = {}

    def nextKey(self):
        nextKey = self.mostRecentKey + 1

        return nextKey % (self.maxKey + 1)

    def ffwMostRecent(self):
        if len(self.buffer) == 0:
            return

        while self.nextKey() not in self.buffer:
            self.mostRecentKey = self.nextKey()

    def pop(self):
        ret = self.buffer.pop(self.nextKey(), None)
        self.mostRecentKey = self.nextKey()

        return ret

    def push(self, key, value):
        self.buffer[key] = value

        if self.mostRecentKey is None:
            self.mostRecentKey = key - 1

        if len(self.buffer) >= self.maxSize:
            self.ffwMostRecent()

        if len(self.buffer) > self.maxSize:
            self.pop()

    def available(self):
        available = False

        if len(self.buffer) > 0:
            if ((self.mostRecentKey is None) or
               self.nextKey() in self.buffer):
                available = True

        return available

    def get(self):
        ret = []

        while self.available():
            ret.append(self.pop())

        return ret

    def pushGet(self, key, value):
        self.push(key, value)
        return self.get()


class TTMLClient:
    def __init__(self, port, callback, recvBufSize=None, timeout=None):
        self.fragments = {}
        self.curTimestamp = None
        self.prevSeqNum = None
        self.port = port
        self.callback = callback

        if recvBufSize is None:
            self.recvBufSize = 2**16
        else:
            self.recvBufSize = recvBufSize

        self.packetBuff = OrderedBuffer()

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

        # Account for missing packets around edges
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

    def processPacket(self, packet):
        # Initialise or new doc. When initialising, we'll asume the first
        # packet is the start of the doc. It'll be found to be invalid
        # later if we were wrong. New TS means a new document
        if (self.prevSeqNum is None or
           packet.timestamp != self.curTimestamp):
            # If we haven't processed by now, document is incomplete
            # so we discard it
            self.fragments = {}

            # Assume this packet is the first in doc. If we're wrong, the doc
            # won't be valid TTML when decoded anyway
            if self.prevSeqNum is None:
                self.prevSeqNum = packet.sequenceNumber - 1
            self.curTimestamp = packet.timestamp

        payload = RTPPayload_TTML().fromBytearray(packet.payload)

        unloopedSeqNum = self.unloopSeqNum(
            self.prevSeqNum, packet.sequenceNumber)

        self.fragments[unloopedSeqNum] = payload.userDataWords

        self.prevSeqNum = unloopedSeqNum

    def run(self):
        while True:
            data = self.socket.recv(self.recvBufSize)

            newPacket = RTP().fromBytes(data)

            packets = self.packetBuff.pushGet(
                newPacket.sequenceNumber, newPacket)

            for packet in packets:
                self.processPacket(packet)

                if packet.marker:
                    self.processFragments()
