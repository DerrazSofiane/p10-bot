from botbuilder.dialogs.prompts import Prompt, PromptOptions, TextPrompt, PromptRecognizerResult
from botbuilder.core.turn_context import TurnContext
from botbuilder.schema import ActivityTypes
from botbuilder.dialogs import WaterfallDialog, WaterfallStepContext, DialogTurnResult
from botbuilder.core import MessageFactory, BotTelemetryClient, NullTelemetryClient
from flight_booking_recognizer import FlightBookingRecognizer
from helpers.luis_helper import LuisHelper, Intent
from typing import Callable, Dict


class TextToLuisPrompt(Prompt):
    def __init__(
        self, dialog_id: str, luis_recognizer: FlightBookingRecognizer=FlightBookingRecognizer
        ):
        self.luis_recognizer = luis_recognizer
        self.detected_intent = None
        super().__init__(dialog_id)

    async def on_prompt(
        self, turn_context: TurnContext, 
        state: Dict[str, object], 
        options: PromptOptions, 
        is_retry: bool, 
    ):
        if not turn_context:
            raise TypeError("turn_context can't be None")
        if not options:
            raise TypeError("options can't be None")

        if is_retry and options.retry_prompt is not None:
            await turn_context.send_activity(options.retry_prompt)
        else:
            if options.prompt is not None:
                await turn_context.send_activity(options.prompt)   
                
    async def on_recognize(self,
        turn_context: TurnContext, 
        state: Dict[str, object], 
        options: PromptOptions, 
    ) -> PromptRecognizerResult:  
        if not turn_context:
            raise TypeError("turn_context can't be None")

        if turn_context.activity.type == ActivityTypes.message:
            usertext = turn_context.activity.text

        prompt_result = PromptRecognizerResult()
        
        print(usertext)
        prompt_result.value = usertext
        prompt_result.succeeded = True

        return prompt_result