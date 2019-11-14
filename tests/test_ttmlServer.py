#!/usr/bin/python
#
# Copyright 2018 British Broadcasting Corporation
#
# This is an internal BBC tool and is not licensed externally
# If you have received a copy of this erroneously then you do
# not have permission to reproduce it.

from unittest import TestCase, mock
from hypothesis import given, strategies as st
from rtpPayload_ttml import RTPPayload_TTML  # type: ignore

from rtpTTML import TTMLServer  # type: ignore


class TestTTMLServer (TestCase):
    @mock.patch("socket.socket")
    def setUp(self, mockSocket):
        self.server = TTMLServer("", 0)

    def setup_example(self):
        self.setUp()

    @given(
        st.text(min_size=1),
        st.integers(min_value=4))
    def test_fragmentDoc(self, doc, maxLen):
        fragments = self.server._fragmentDoc(doc, maxLen)

        reconstructedDoc = ""
        for fragment in fragments:
            self.assertLessEqual(len(bytearray(fragment, "utf-8")), maxLen)
            reconstructedDoc += fragment

        self.assertEqual(doc, reconstructedDoc)

    @given(st.datetimes())
    def test_datetimeToRTPTs(self, time):
        rtpTs = self.server._datetimeToRTPTs(time)

        self.assertIsInstance(rtpTs, int)
        self.assertGreaterEqual(rtpTs, 0)
        self.assertLess(rtpTs, 2**32)

    @given(
        st.text().filter(lambda x: len(bytearray(x, "utf-8")) < 2**16),
        st.integers(min_value=0, max_value=(2**32)-1),
        st.booleans())
    def test_generateRTPPacket(self, doc, time, marker):
        expectedSeqNum = self.server.nextSeqNum

        packet = self.server._generateRTPPacket(doc, time, marker)
        payload = RTPPayload_TTML().fromBytearray(packet.payload)

        self.assertEqual(packet.timestamp, time)
        self.assertEqual(packet.sequenceNumber, expectedSeqNum)
        self.assertEqual(packet.marker, marker)
        self.assertEqual(payload.userDataWords, doc)

        self.assertEqual(self.server.nextSeqNum, expectedSeqNum + 1)
