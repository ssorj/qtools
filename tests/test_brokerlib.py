#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

from qtools.brokerlib import _Topic

class _NullBroker:
    def info(self, *args):
        pass

    def notice(self, *args):
        pass

class _Connection:
    remote_container = "test"

class _Delivery:
    def __init__(self):
        self.connection = _Connection()

class _Consumer:
    def __init__(self, credit=0):
        self.is_sender = True
        self.credit = credit
        self.connection = _Connection()
        self.messages = []

    def send(self, message):
        assert self.credit > 0
        self.credit -= 1
        self.messages.append(message)

def store(topic, *messages):
    for message in messages:
        topic.store_message(_Delivery(), message)

def test_topic_evicts_read_messages():
    topic = _Topic(_NullBroker(), "topic1")
    consumer = _Consumer(credit=3)

    topic.add_consumer(consumer)
    store(topic, "one", "two", "three")

    assert list(topic.messages) == ["one", "two", "three"]

    topic.forward_messages()

    assert consumer.messages == ["one", "two", "three"]
    assert list(topic.messages) == []
    assert topic.consumer_offsets[consumer] == 0

def test_topic_evicts_only_after_all_consumers_read():
    topic = _Topic(_NullBroker(), "topic1")
    fast = _Consumer(credit=3)
    slow = _Consumer(credit=1)

    topic.add_consumer(fast)
    topic.add_consumer(slow)
    store(topic, "one", "two", "three")
    topic.forward_messages()

    assert fast.messages == ["one", "two", "three"]
    assert slow.messages == ["one"]
    assert list(topic.messages) == ["two", "three"]
    assert topic.consumer_offsets[fast] == 2
    assert topic.consumer_offsets[slow] == 0

    slow.credit = 2
    topic.forward_messages()

    assert slow.messages == ["one", "two", "three"]
    assert list(topic.messages) == []
    assert topic.consumer_offsets[fast] == 0
    assert topic.consumer_offsets[slow] == 0

def test_topic_discards_messages_without_consumers():
    topic = _Topic(_NullBroker(), "topic1")

    store(topic, "one", "two")

    assert list(topic.messages) == []

def test_topic_removing_last_consumer_discards_messages():
    topic = _Topic(_NullBroker(), "topic1")
    consumer = _Consumer()

    topic.add_consumer(consumer)
    store(topic, "one", "two")

    assert list(topic.messages) == ["one", "two"]

    topic.remove_consumer(consumer)

    assert list(topic.messages) == []
    assert not topic.consumer_offsets
