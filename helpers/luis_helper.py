# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from enum import Enum
from typing import Dict
from botbuilder.ai.luis import LuisRecognizer
from botbuilder.core import IntentScore, TopIntent, TurnContext

from booking_details import BookingDetails


# class Intent(Enum):
#     BOOK_FLIGHT = "BookFlight"
#     CANCEL = "Cancel"
#     GET_WEATHER = "GetWeather"
#     NONE_INTENT = "NoneIntent"

### BEGIN : Redéfinition des intentions
class Intent(Enum):
    BOOK_FLIGHT = "BookFlightIntent"
    CANCEL = "Communication_Cancel"
    CONFIRM = "Communication_Confirm"
    NONE_INTENT = "None"
### END


def top_intent(intents: Dict[Intent, dict]) -> TopIntent:
    max_intent = Intent.NONE_INTENT
    max_value = 0.0

    for intent, value in intents:
        intent_score = IntentScore(value)
        if intent_score.score > max_value:
            max_intent, max_value = intent, intent_score.score

    return TopIntent(max_intent, max_value)


class LuisHelper:
    @staticmethod
    async def execute_luis_query(
        luis_recognizer: LuisRecognizer, turn_context: TurnContext
    ) -> (Intent, object):
        """
        Returns an object with preformatted LUIS results for the bot's dialogs to consume.
        """
        result = None
        intent = None

        try:
            recognizer_result = await luis_recognizer.recognize(turn_context)

            intent = (
                sorted(
                    recognizer_result.intents,
                    key=recognizer_result.intents.get,
                    reverse=True,
                )[:1][0]
                if recognizer_result.intents
                else None
            )

            if intent == Intent.BOOK_FLIGHT.value:
                result = BookingDetails()
                # We need to get the result from the LUIS JSON which at every level returns an array.
                to_entities = recognizer_result.entities.get("$instance", {}).get("dst_city", [])
                if len(to_entities) > 0:
                    if recognizer_result.entities.get("dst_city", [{"$instance": {}}]):
                        result.dst_city = to_entities[0]["text"].title()
                        print("found dst_city :", result.dst_city)
                    else:
                        result.unsupported_airports.append(to_entities[0]["text"].title())

                from_entities = recognizer_result.entities.get("$instance", {}).get("or_city", [])
                if len(from_entities) > 0:
                    if recognizer_result.entities.get("or_city", [{"$instance": {}}]):
                        result.or_city = from_entities[0]["text"].title()
                        print("found or_city :", result.or_city)
                    else:
                        result.unsupported_airports.append(from_entities[0]["text"].title())

                budget_entities = recognizer_result.entities.get("budget", [])
                if len(budget_entities) > 0:
                    result.budget = budget_entities[0]
                    print("found budget :", result.budget)

                n_adults_entities = recognizer_result.entities.get("n_adults", [])
                if len(n_adults_entities) > 0:
                    result.n_adults = n_adults_entities[0]
                    print("found n_adults :", result.n_adults)

                n_children_entities = recognizer_result.entities.get("n_children", [])
                if len(n_children_entities) > 0:
                    result.n_children = n_children_entities[0]
                    print("found n_children :", result.n_children)

                # This value will be a TIMEX. And we are only interested in a
                # Date so grab the first result and drop the Time part. TIMEX
                # is a format that represents DateTime expressions that include
                # some ambiguity. e.g. missing a Year.
                date_entities = recognizer_result.entities.get("datetime", [])
                if date_entities:
                    if len(date_entities)==1:
                        timex = date_entities[0]["timex"]
                        if date_entities[0]['type'] == 'daterange':
                            datetime_range = timex[0].strip('(').strip(')').split(',')
                            result.str_date = datetime_range[0]
                            result.end_date = datetime_range[1]
                        elif date_entities[0]['type'] == 'date':
                            result.str_date = timex[0]
                    
                    elif len(date_entities)==2:
                        timex1 = date_entities[0]["timex"]
                        timex2 = date_entities[1]["timex"]
                        if timex1[0] <= timex2[0]:
                            result.str_date = timex1[0]
                            result.end_date = timex2[0]
                        else:
                            result.str_date = timex2[0]
                            result.end_date = timex1[0]
                    
        except Exception as exception:
            print(exception)
            
        return intent, result
