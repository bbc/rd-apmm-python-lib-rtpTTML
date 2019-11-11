#!/usr/bin/python
#
# Copyright 2018 British Broadcasting Corporation
#
# This is an internal BBC tool and is not licensed externally
# If you have received a copy of this erroneously then you do
# not have permission to reproduce it.

from unittest import TestCase
from hypothesis import given, strategies as st
from rtp import RTP  # type: ignore

from rtpTTML.ttmlClient import OrderedBuffer, MAX_SEQ_NUM


class TestOrderedBuffer (TestCase):
    def setUp(self):
        self.buffer = OrderedBuffer()

    def setup_example(self):
        self.setUp()

    @given(
        st.integers(min_value=0, max_value=MAX_SEQ_NUM),
        st.integers(min_value=1, max_value=10))
    def test_push(self, startKey, len):
        fragments = []
        for x in range(len):
            seqNum = (startKey + x) % (MAX_SEQ_NUM + 1)
            packet = RTP(sequenceNumber=seqNum)
            fragments.append((seqNum, packet))
            self.buffer.push(seqNum, packet)

        for seqNum, packet in fragments[-5:]:
            self.assertIn(seqNum, self.buffer._buffer)
            self.assertEqual(packet, self.buffer._buffer[seqNum])

        for seqNum, packet in fragments[:-5]:
            self.assertNotIn(seqNum, self.buffer._buffer)

    @given(
        st.integers(min_value=0, max_value=MAX_SEQ_NUM),
        st.integers(min_value=1, max_value=10))
    def test_pop(self, startKey, len):
        fragments = []
        for x in range(len):
            seqNum = (startKey + x) % (MAX_SEQ_NUM + 1)
            packet = RTP(sequenceNumber=seqNum)
            fragments.append((seqNum, packet))
            self.buffer.push(seqNum, packet)

        for _, packet in fragments[-5:]:
            poppedPacket = self.buffer.pop()
            self.assertEqual(packet, poppedPacket)

    @given(
        st.integers(min_value=0, max_value=MAX_SEQ_NUM),
        st.integers(min_value=1, max_value=10))
    def test_available(self, startKey, len):
        self.assertFalse(self.buffer.available())

        fragments = []
        for x in range(len):
            seqNum = (startKey + x) % (MAX_SEQ_NUM + 1)
            packet = RTP(sequenceNumber=seqNum)
            fragments.append((seqNum, packet))
            self.buffer.push(seqNum, packet)

        for _, packet in fragments[-5:]:
            self.assertTrue(self.buffer.available())
            self.buffer.pop()

        self.assertFalse(self.buffer.available())

    @given(
        st.integers(min_value=0, max_value=MAX_SEQ_NUM),
        st.integers(min_value=1, max_value=10))
    def test_get(self, startKey, len):
        fragments = []
        for x in range(len):
            seqNum = (startKey + x) % (MAX_SEQ_NUM + 1)
            packet = RTP(sequenceNumber=seqNum)
            fragments.append(packet)
            self.buffer.push(seqNum, packet)

        gotPackets = self.buffer.get()

        self.assertEqual(gotPackets, fragments[-5:])
        self.assertFalse(self.buffer.available())

    @given(
        st.integers(min_value=0, max_value=MAX_SEQ_NUM),
        st.integers(min_value=1, max_value=10))
    def test_pushGet(self, startKey, len):
        self.assertFalse(self.buffer.available())
        for x in range(len):
            seqNum = (startKey + x) % (MAX_SEQ_NUM + 1)
            packet = RTP(sequenceNumber=seqNum)
            ret = self.buffer.pushGet(seqNum, packet)
            self.assertEqual([packet], ret)
            self.assertFalse(self.buffer.available())

    @given(
        st.integers(min_value=0, max_value=MAX_SEQ_NUM),
        st.lists(st.booleans(), min_size=5, max_size=5))
    def test_pushGetMissing(self, startKey, keepList):
        self.assertFalse(self.buffer.available())
        keepList += ([True] * 5)

        expectedList = []
        receivedList = []

        for x in range(10):
            seqNum = (startKey + x) % (MAX_SEQ_NUM + 1)
            packet = RTP(sequenceNumber=seqNum)
            if keepList[x]:
                expectedList.append(packet)
                ret = self.buffer.pushGet(seqNum, packet)
                receivedList += ret

        self.assertEqual(expectedList, receivedList)
        self.assertFalse(self.buffer.available())

    @given(
        st.integers(min_value=0, max_value=MAX_SEQ_NUM),
        st.lists(st.integers(min_value=1, max_value=5),
                 min_size=2, max_size=2, unique=True))
    def test_pushGetSwapped(self, startKey, swap):
        self.assertFalse(self.buffer.available())
        expectedList = {}
        receivedList = []

        keyOffsets = list(range(10))
        keyOffsets[swap[0]], keyOffsets[swap[1]] = (
            keyOffsets[swap[1]], keyOffsets[swap[0]])

        for x in keyOffsets:
            seqNum = (startKey + x) % (MAX_SEQ_NUM + 1)
            packet = RTP(sequenceNumber=seqNum)
            expectedList[x] = packet
            ret = self.buffer.pushGet(seqNum, packet)
            receivedList += ret

        self.assertFalse(self.buffer.available())

        self.assertEqual(len(expectedList), len(receivedList))
        self.assertEqual(list(expectedList.values()), receivedList)
