"""Per-browser session isolation (Mac owner vs phone guest)."""

import os
import tempfile
import unittest

from src.client_sessions import bind_client_session, reset_client_session
from src.memory import BeruMemory
from src.pipeline import BeruPipeline


class TestClientSessions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self.tmp.close()
        self.memory_path = self.tmp.name
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            f.write(
                '{"corrections":[],"known_users":{"Omar":{"is_owner":true,'
                '"permanently_verified":true,"full_name":"Omar Darwish",'
                '"first_name":"Omar","language":"en"}},'
                '"conversation_history":[],"learned_omar_facts":[]}'
            )

    def tearDown(self):
        os.unlink(self.memory_path)

    def test_owner_on_one_device_does_not_identify_another(self):
        memory = BeruMemory(memory_path=self.memory_path)

        mac = bind_client_session('mac-browser-uuid')
        try:
            memory.identify_session('Omar', language='en', is_owner=True)
            self.assertTrue(memory.is_owner())
            self.assertEqual(memory.get_user_name(), 'Omar')
        finally:
            reset_client_session(mac)

        phone = bind_client_session('phone-browser-uuid')
        try:
            self.assertFalse(memory.is_owner())
            self.assertFalse(memory.is_session_identified())
            self.assertTrue(memory.is_awaiting_owner_confirm())
        finally:
            reset_client_session(phone)

    def test_hello_on_phone_not_greeted_as_omar_after_mac_login(self):
        pipeline = BeruPipeline(load_model=False)
        pipeline.memory = BeruMemory(memory_path=self.memory_path)

        mac = bind_client_session('mac-session')
        try:
            pipeline.memory.identify_session('Omar', language='en', is_owner=True)
        finally:
            reset_client_session(mac)

        result = pipeline.chat_turn(
            'hello',
            client_session_id='phone-session',
            collector_session_id='phone-session',
        )
        self.assertFalse(result['is_owner'])
        response_lower = result['response'].lower()
        self.assertNotIn('omar', response_lower.split()[:8])


if __name__ == '__main__':
    unittest.main()
