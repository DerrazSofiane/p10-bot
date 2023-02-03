from botbuilder.dialogs.prompts import Prompt, PromptOptions, PromptRecognizerResult
from botbuilder.core.turn_context import TurnContext
from botbuilder.schema import ActivityTypes

from flight_booking_recognizer import FlightBookingRecognizer
from config import DefaultConfig

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
            entities = luis_result.entities.get("$instance", {})
            from_entities = entities.get(entity_to_retrieve, [])
            # Double check with prebuilt model entity
            is_valid = ["geographyV2" in key for key in entities.keys()]
            if entity_to_retrieve == "budget":
                if len(from_entities) > 0:
                    if luis_result.entities.get(
                            entity_to_retrieve, [{"$instance": {}}]):
                        entity = str(from_entities[0]["text"]).capitalize()
                        print(f"found {entity_to_retrieve} :", entity)
            else:
                if len(from_entities) > 0 and True in is_valid:
                    if luis_result.entities.get(
                            entity_to_retrieve, [{"$instance": {}}]):
                        entity = str(from_entities[0]["text"]).capitalize()
                        print(f"found {entity_to_retrieve} :", entity)
            return entity
        
        entity = retrieve_entity()
        if entity is None and (self.dialog_id=="or_city" or self.dialog_id=="dst_city"):
            # Retry with the built-in entity to parse the city
            entity = retrieve_entity(entity_to_retrieve="geographyV2_city")
            
        if entity is None:
            prompt_result.succeeded = False
        else:
            prompt_result.succeeded = True
            prompt_result.value = entity

        return prompt_result
    
