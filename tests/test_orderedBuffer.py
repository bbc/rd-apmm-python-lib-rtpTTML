#!/usr/bin/python
#
# James Sandford, copyright BBC 2020
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import TestCase
from hypothesis import given, strategies as st  # type: ignore
from rtp import RTP

from rtpTTML.ttmlReceiver import OrderedBuffer, MAX_SEQ_NUM


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
        expectedList = []
        receivedList = []

        for x in list(range(10)):
            seqNum = (startKey + x) % (MAX_SEQ_NUM + 1)
            packet = RTP(sequenceNumber=seqNum)
            expectedList.append(packet)

        swappedPackets = expectedList.copy()
        swappedPackets[swap[0]], swappedPackets[swap[1]] = (
            swappedPackets[swap[1]], swappedPackets[swap[0]])

        for packet in swappedPackets:
            ret = self.buffer.pushGet(packet.sequenceNumber, packet)
            receivedList += ret

        self.assertFalse(self.buffer.available())

        self.assertEqual(len(expectedList), len(receivedList))
        self.assertEqual(expectedList, receivedList)
