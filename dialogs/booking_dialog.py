# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Il s'agit d'un script Python qui définit un dialogue de réservation de vol.
Il utilise des classes de la bibliothèque BotBuilder pour créer un dialogue de
type "cascade" (WaterfallDialog) qui guide l'utilisateur à travers les étapes
de la réservation, telles que la saisie de la destination, de l'origine, de la
date de départ et de la date de retour, du budget, etc. Il utilise également des
classes de la bibliothèque LUIS pour analyser les réponses de l'utilisateur et
identifier les intents. Il utilise également des classes de la bibliothèque
datatypes_date_time pour résoudre les dates saisies par l'utilisateur. La classe
principale du script est BookingDialog, qui hérite de CancelAndHelpDialog, une
classe qui gère les intents d'annulation et d'aide."""

from datatypes_date_time.timex import Timex

from botbuilder.dialogs import WaterfallDialog, WaterfallStepContext, DialogTurnResult
from botbuilder.dialogs.prompts import ConfirmPrompt, TextPrompt, PromptOptions, NumberPrompt
from botbuilder.core import MessageFactory, BotTelemetryClient, NullTelemetryClient
from .cancel_and_help_dialog import CancelAndHelpDialog
from .date_resolver_dialog import DateResolverDialog

from booking_details import BookingDetails
from flight_booking_recognizer import FlightBookingRecognizer
from helpers.luis_helper import LuisHelper, Intent


class BookingDialog(CancelAndHelpDialog):
    """Flight booking implementation."""

    def __init__(
        self,
        luis_recognizer: FlightBookingRecognizer,
        dialog_id: str = None,
        telemetry_client: BotTelemetryClient = NullTelemetryClient()
        
    ):
        super(BookingDialog, self).__init__(
            dialog_id or BookingDialog.__name__, telemetry_client
        )
        self._luis_recognizer = luis_recognizer
        self.telemetry_client = telemetry_client
        
        number_prompt = NumberPrompt(NumberPrompt.__name__)
        number_prompt.telemetry_client = telemetry_client
        
        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = telemetry_client

        waterfall_dialog = WaterfallDialog(
            WaterfallDialog.__name__,
            [
                self.destination_step,
                self.origin_step,
                self.travel_date_step,
                self.travel_end_date_step,
                self.budget_step,
                self.n_adults_step,
                self.n_children_step,
                self.confirm_step,
                self.final_step
            ],
        )
        waterfall_dialog.telemetry_client = telemetry_client

        self.add_dialog(number_prompt)
        self.add_dialog(text_prompt)
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))
        self.add_dialog(
            DateResolverDialog(
                DateResolverDialog.START_DATE_DIALOG_ID, self.telemetry_client
            )
        )
        self.add_dialog(
            DateResolverDialog(
                DateResolverDialog.END_DATE_DIALOG_ID, self.telemetry_client
            )
        )
        self.add_dialog(waterfall_dialog)

        self.initial_dialog_id = WaterfallDialog.__name__

    async def destination_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for destination."""
        booking_details = step_context.options

        ### Flyme : Réadaptation des variables redéfinies dans ~/booking_details.py
        if booking_details.dst_city is None: # destination
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("To what city would you like to travel?")
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.dst_city) # destination

    async def origin_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for origin city."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.dst_city = step_context.result # destination
        
        if booking_details.or_city is None: # origin
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("From what city will you be travelling?")
                ),
            )  # pylint: disable=line-too-long,bad-continuation
            
            # intent, luis_result = await LuisHelper.execute_luis_query(
            #     self._luis_recognizer, user_inpt
            #     )
            # print(luis_result)
        
        return await step_context.next(booking_details.or_city) # origin

    async def travel_date_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for travel date.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.or_city = step_context.result # origin
        if not booking_details.str_date or self.is_ambiguous(
            booking_details.str_date # travel_date
        ):
            return await step_context.begin_dialog(
                DateResolverDialog.START_DATE_DIALOG_ID,
                booking_details.str_date,
            )

        return await step_context.next(booking_details.str_date) # travel_date
    
    async def travel_end_date_step(
            self, step_context: WaterfallStepContext
        ) -> DialogTurnResult:
        
        """Prompt for travel date of return.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.str_date = step_context.result
        if not booking_details.end_date or self.is_ambiguous(
            booking_details.end_date
        ):
            return await step_context.begin_dialog(
                DateResolverDialog.END_DATE_DIALOG_ID, booking_details.end_date
            )
            
        return await step_context.next(booking_details.end_date)
    
    async def budget_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for the budget."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.end_date = step_context.result
        if booking_details.budget is None:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("What is your budget?")
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.budget)   
    
    async def n_adults_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for the budget."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.budget = step_context.result
        if booking_details.n_adults is None:
            reprompt_msg = """Please include a numerical reference in your
            sentence.
            For example: "We are 2 adults traveling." or "We are two adults.".
            """
            return await step_context.prompt(
                NumberPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("For how many adult(s)?"),
                    retry_prompt=MessageFactory.text(reprompt_msg)
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.n_adults)      
    
    async def n_children_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for the budget."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.n_adults = step_context.result
        
        if booking_details.n_children is None:
            reprompt_msg = """Please include a numerical reference in your
            sentence.
            For example: "I have 1 children." or "I have one children.".
            """
            return await step_context.prompt(
                NumberPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("And how many children(s)?"),
                    retry_prompt=MessageFactory.text(reprompt_msg)
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.n_children)     
    
    async def confirm_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Confirm the information the user has provided."""
        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.n_children = step_context.result
        msg = (
            f"Please confirm, I have you traveling to: { booking_details.dst_city }"
            f" from: { booking_details.or_city } on: { booking_details.str_date }."
        )

        # Offer a YES/NO prompt.
        return await step_context.prompt(
            ConfirmPrompt.__name__, PromptOptions(prompt=MessageFactory.text(msg))
        )

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Complete the interaction and end the dialog."""
        if step_context.result:
            booking_details = step_context.options
        ### Flyme : End - Fin des modifications d'appel de méthodes
            return await step_context.end_dialog(booking_details)

        return await step_context.end_dialog()

    def is_ambiguous(self, timex: str) -> bool:
        """Ensure time is correct."""
        timex_property = Timex(timex)
        return "definite" not in timex_property.types
