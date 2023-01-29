from botbuilder.dialogs.prompts import Prompt, PromptOptions, TextPrompt, PromptRecognizerResult
from botbuilder.core.turn_context import TurnContext
from botbuilder.schema import ActivityTypes

from flight_booking_recognizer import FlightBookingRecognizer
from config import DefaultConfig
from helpers.luis_helper import LuisHelper, Intent

from typing import Dict


class TextToLuisPrompt(Prompt):
    def __init__(
        self,
        dialog_id: str,
        luis_recognizer: FlightBookingRecognizer = FlightBookingRecognizer(DefaultConfig),
        validator : object = None
        ):
        self.dialog_id = dialog_id
        self.luis_recognizer = luis_recognizer
        self.detected_intent = None
        super().__init__(dialog_id, validator=validator)

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
        recognizer_result = await self.luis_recognizer.recognize(turn_context)
        
        def retrieve_entity(
            luis_result=recognizer_result,
            entity_to_retrieve=self.dialog_id
            ):
            entity = None
            from_entities = recognizer_result.entities.get("$instance", {})
            from_entities = from_entities.get(entity_to_retrieve, [])
            if len(from_entities) > 0:
                if recognizer_result.entities.get(
                        entity_to_retrieve, [{"$instance": {}}]):
                    entity = from_entities[0]["text"].capitalize()
                    print(f"found {entity_to_retrieve} :", entity)
            return entity
        
        recognizer_result = retrieve_entity(recognizer_result)
        
        if recognizer_result is None:
            prompt_result.succeeded = False
        else:
            prompt_result.succeeded = True
            prompt_result.value = recognizer_result

        return prompt_result
    
