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
from botbuilder.dialogs.prompts import (
    ConfirmPrompt,
    TextPrompt,
    PromptOptions,
    NumberPrompt,
    )
from botbuilder.core import MessageFactory, BotTelemetryClient, NullTelemetryClient
from .cancel_and_help_dialog import CancelAndHelpDialog
from .date_resolver_dialog import DateResolverDialog
from dialogs.custom_prompts import TextToLuisPrompt


class BookingDialog(CancelAndHelpDialog):
    """Flight booking implementation."""

    def __init__(
        self,
        dialog_id: str = None,
        telemetry_client: BotTelemetryClient = NullTelemetryClient()
    ):
        super(BookingDialog, self).__init__(
            dialog_id or BookingDialog.__name__, telemetry_client
        )
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
        self.add_dialog(TextToLuisPrompt("dst_city"))
        self.add_dialog(TextToLuisPrompt("or_city"))
        self.add_dialog(TextToLuisPrompt("budget"))
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))
        self.add_dialog(
            DateResolverDialog("str_date", self.telemetry_client)
        )
        self.add_dialog(
            DateResolverDialog("end_date", self.telemetry_client)
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
            retry_prompt = "Sorry, I couldn't find this place. Please enter a valid place."
            return await step_context.prompt(
                "dst_city",
                PromptOptions(
                    prompt=MessageFactory.text("To what city would you like to travel?"),
                    retry_prompt=MessageFactory.text(retry_prompt)
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.dst_city) # destination

    async def origin_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for origin city."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.dst_city = step_context.result # destination
        
        if booking_details.or_city is None: # origin
            retry_prompt = "Sorry, I couldn't find this place. Please enter a valid place."
            return await step_context.prompt(
                "or_city",
                PromptOptions(
                    prompt=MessageFactory.text("From what city will you be travelling?"),
                    retry_prompt=MessageFactory.text(retry_prompt)
                ),
            )  # pylint: disable=line-too-long,bad-continuation
        
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
                "str_date", booking_details.str_date
            )  # pylint: disable=line-too-long

        return await step_context.next(booking_details.str_date) # travel_date
    
    async def travel_end_date_step(
            self, step_context: WaterfallStepContext
        ) -> DialogTurnResult:
        
        """Prompt for travel date of return.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.str_date = step_context.result
        print(booking_details.str_date)
        if not booking_details.end_date or self.is_ambiguous(
            booking_details.end_date
        ):
            return await step_context.begin_dialog(
                "end_date", booking_details.end_date
            )  # pylint: disable=line-too-long
            
        return await step_context.next(booking_details.end_date)
    
    async def budget_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for the budget."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.end_date = step_context.result
        if booking_details.budget is None:
            retry_prompt = """Sorry, I couldn't process your budget input. Try
            in a different way. Eg. 'I have a budget of 500$.'."""
            return await step_context.prompt(
                "budget",
                PromptOptions(
                    prompt=MessageFactory.text("What is your budget?"),
                    retry_prompt=MessageFactory.text(retry_prompt)
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
            For example: "I have 1 child." or "I have one child.".
            """
            return await step_context.prompt(
                NumberPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("And how many child(ren)?"),
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
            f"""Please confirm, I have you traveling
            \nto: {booking_details.dst_city};
            \nfrom: {booking_details.or_city};
            \ndeparture on: {booking_details.str_date};
            \nreturn on: {booking_details.end_date};
            \nfor {booking_details.n_adults} adult(s);
            \nand {booking_details.n_children} children(s);
            \nwith a budget of: {booking_details.budget}."""
        )

        # Offer a YES/NO prompt.
        return await step_context.prompt(
            ConfirmPrompt.__name__, PromptOptions(prompt=MessageFactory.text(msg))
        )

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Complete the interaction and end the dialog."""
        booking_details = step_context.options
        properties = {
            "or_city": str(booking_details.or_city),
            "dst_city": str(booking_details.dst_city),
            "str_date": str(booking_details.str_date),
            "end_date": str(booking_details.end_date),
            "budget": str(booking_details.budget),
            "n_adults": str(booking_details.n_adults),
            "n_children": str(booking_details.n_children)
        }
        print(properties)

        if step_context.result:
            self.telemetry_client.track_trace("Booking confirmed", properties, "INFO")
            return await step_context.end_dialog(booking_details)

        self.telemetry_client.track_trace("Booking declined", properties, "ERROR")
        await step_context.context.send_activity(
            MessageFactory.text("I invite you to make a new booking.")
        )

        return await step_context.end_dialog()

    # async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
    #     """Complete the interaction and end the dialog."""
    #     if step_context.result:
    #         booking_details = step_context.options
    #     ### Flyme : End - Fin des modifications d'appel de méthodes
    #         return await step_context.end_dialog(booking_details)

    #     return await step_context.end_dialog()

    def is_ambiguous(self, timex: str) -> bool:
        """Ensure time is correct."""
        timex_property = Timex(timex)
        return "definite" not in timex_property.types
