import aiounittest
from botbuilder.core import TurnContext, ConversationState, MemoryStorage
from botbuilder.core.adapters import TestAdapter
from botbuilder.dialogs import DialogSet, DialogTurnStatus

from booking_details import BookingDetails
from config import DefaultConfig
from dialogs import MainDialog, BookingDialog
from flight_booking_recognizer import FlightBookingRecognizer


class BotTest(aiounittest.AsyncTestCase):
    async def execute_booking_dialog(self, turn_context: TurnContext, dialog_id: str,
                                     booking_details: BookingDetails = None):
        dialog_context = await self.dialogs.create_context(turn_context)
        result = await dialog_context.continue_dialog()
        if result.status == DialogTurnStatus.Empty:
            await dialog_context.begin_dialog(dialog_id, booking_details)
        elif result.status == DialogTurnStatus.Complete:
            await turn_context.send_activity(result.result)
        elif result.status == DialogTurnStatus.Waiting:
            pass
        else:
            raise Exception(f"Unexpected dialog turn status: {result.status}")
        await self.conversation_state.save_changes(turn_context)

    def init_booking_dialogs(self, dialog_id, booking_details=None):
        self.conversation_state = ConversationState(MemoryStorage())
        self.dialogs_state = self.conversation_state.create_property("dialog_state")
        self.dialogs = DialogSet(self.dialogs_state)
        if dialog_id == BookingDialog.__name__:
            self.dialogs.add(BookingDialog())
            adapter = TestAdapter(lambda ctx: self.execute_booking_dialog(ctx, dialog_id, booking_details))
        else:
            config = DefaultConfig()
            luis_recognizer = FlightBookingRecognizer(config)
            booking_dialog = BookingDialog()
            self.dialogs.add(MainDialog(luis_recognizer, booking_dialog))
            adapter = TestAdapter(lambda ctx: self.execute_booking_dialog(ctx, MainDialog.__name__))
        return adapter

    async def test_complete_waterfall_dialog(self):
        adapter = self.setup_booking_dialogs(BookingDialog.__name__, BookingDetails())
        
        disc1 = await adapter.test(
            "Hi! I would like to book a flight", # User
            "To what city would you like to travel?" # Bot
            )
        
        disc2 = await disc1.test(
            "I have to go to Sydney very soon", # User
            "From what city will you be travelling?" # Bot
            )
        
        disc3 = await disc2.test(
            "I'm going from London", # User
            "On what date would you like to travel?" # Bot
            )
        
        disc4 = await disc3.test(
            "I want to go the 1st of march, 2023", # User
            "On what date would you like to come back?" # Bot
            )
        
        disc5 = await disc4.test(
            "I would like to return the 15th of march, 2023", # User
            "What is your budget?" # Bot
            )
        
        disc6 = await disc5.test(
            "I only have a budget of 800$, I hope it's enough", # User
            "For how many adult(s)?" # Bot
            )
        
        disc7 = await disc6.test(
            "We are two adults traveling", # User
            "And how many child(ren)?" # Bot
            )
        
        disc8 = await disc7.send("I have 0 child") # User
        
        await disc8.assert_reply(
            "Just confirming, you are traveling from London to Sydney "
            "from 2023-03-01 to 2023-03-15 with 2 adult(s) "
            "and 0 child(ren), and a budget of 800 $. Does this sound correct? (1) Yes or (2) No"
            ) # Bot

    async def test_flight_booking_missing_informations(self):
        adapter = self.setup_booking_dialogs(MainDialog.__name__)
        
        disc1 = await adapter.test(
            "Hey!", # User
            "What can I help you with today?" # Bot
            )
        
        disc2 = await disc1.test(
            "I would like to go to Tijuana from Paris the 10th of August, 2023. "
            "I want to return the 15th of August 2023. I have a budget of 1500$ "
            "and we are 2 adults.", # User
            "And how many child(ren)?" # Bot
            )
        
        disc3 = await disc2.send("I have one child") # User
        
        await disc3.assert_reply(
            "Just confirming, you are traveling from Paris to Tijuana "
            "from 2023-08-10 to 2023-08-15 with 2 adult(s) "
            "and 1 child(ren), and a budget of 1500 $. Does this sound correct? (1) Yes or (2) No"
            ) # Bot
        
    async def test_bot_help(self):
        adapter = self.setup_booking_dialogs(MainDialog.__name__)
        
        disc1 = await adapter.test(
            "Hey!", # User
            "What can I help you with today?") # Bot
        
        disc2 = await disc1.test(
            "I want to go to Paris but I don't know what informations do you need", # User
            "From what city will you be travelling?" # Bot
            )
        
        disc3 = await disc2.send("help") # User
        
        await disc3.assert_reply("Show Help...") # Bot