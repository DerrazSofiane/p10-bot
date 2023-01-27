import os
import unittest
from unittest.mock import Mock
from botbuilder.core import BotFrameworkAdapter, TurnContext
from botbuilder.schema import Activity

class MyChatbotTest(unittest.TestCase):

    def setUp(self):
        self.adapter = BotFrameworkAdapter()
        self.bot = MyChatbot()
        self.turn_context = TurnContext(self.adapter, Activity())

    def test_on_message_activity(self):
        activity = Activity(type='message', text='Hello')
        self.adapter.process_activity(activity, self.bot.on_turn)
        self.assertEqual(self.turn_context.responses[0].text, 'Hello! How can I help you?')

    def test_on_message_activity_with_unknown_intent(self):
        activity = Activity(type='message', text='I have no idea what I am saying')
        self.adapter.process_activity(activity, self.bot.on_turn)
        self.assertEqual(self.turn_context.responses[0].text, 'Sorry, I am not sure what you mean.')