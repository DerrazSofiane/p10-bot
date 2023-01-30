# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Ce fichier main_dialog.py contient la classe MainDialog, qui est un composant
de dialogue pour un bot de voyage basé sur LUIS (Language Understanding Intelligent Service).
La classe MainDialog hérite de la classe ComponentDialog de Bot Builder SDK et
utilise des dialogues en cascades pour gérer les différents scénarios de
dialogue possibles avec l'utilisateur. Les dialogues en cascade sont définis en
utilisant la classe WaterfallDialog et les étapes de la cascade sont définies par
des méthodes asynchrones (async) qui prennent un WaterfallStepContext en entrée
et retournent un DialogTurnResult.

Lorsque MainDialog est instancié, il prend en entrée un objet luis_recognizer de
type FlightBookingRecognizer, un objet booking_dialog de type BookingDialog et un
objet telemetry_client de type BotTelemetryClient. Il initialise également un
TextPrompt et un WaterfallDialog pour gérer les interactions avec l'utilisateur.

La méthode intro_step est appelée en premier et affiche un message de bienvenue
à l'utilisateur. Si LUIS n'est pas configuré, elle affiche un message informant
l'utilisateur que toutes les fonctionnalités ne sont pas disponibles. Sinon,
elle envoie un message demandant à l'utilisateur comment il peut être aidé.

La méthode act_step est appelée ensuite. Si LUIS n'est pas configuré, elle
démarre le dialogue de réservation en passant une instance vide de BookingDetails.
Sinon, elle appelle LUIS pour obtenir les détails de la réservation
(si l'intention est de réserver un vol) ou les informations sur la météo
(si l'intention est d'obtenir la météo) puis démarre le dialogue de réservation
en passant les détails obtenus de LUIS. Si LUIS ne parvient pas à comprendre
l'intention de l'utilisateur, elle envoie un message demandant à l'utilisateur
de reformuler sa demande.

La méthode final_step est enfin appelée pour afficher un message de confirmation
ou un message d'erreur à l'utilisateur en fonction de la réussite ou de l'échec
de la réservation.
"""

from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    WaterfallStepContext,
    DialogTurnResult,
)
from botbuilder.dialogs.prompts import TextPrompt, PromptOptions
from botbuilder.core import (
    MessageFactory,
    TurnContext,
    BotTelemetryClient,
    NullTelemetryClient,
)
from botbuilder.schema import InputHints

from booking_details import BookingDetails
from flight_booking_recognizer import FlightBookingRecognizer
from helpers.luis_helper import LuisHelper, Intent
from .flight_itinerary_card import FlightItineraryCard
from .booking_dialog import BookingDialog


class MainDialog(ComponentDialog):
    def __init__(
            self,
            luis_recognizer: FlightBookingRecognizer,
            booking_dialog: BookingDialog,
            telemetry_client: BotTelemetryClient = NullTelemetryClient(),
    ):
        super(MainDialog, self).__init__(MainDialog.__name__)
        self.telemetry_client = telemetry_client or NullTelemetryClient()
        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = self.telemetry_client

        booking_dialog.telemetry_client = self.telemetry_client

        wf_dialog = WaterfallDialog(
            "WFDialog", [self.intro_step, self.act_step, self.final_step]
        )
        wf_dialog.telemetry_client = self.telemetry_client

        self._luis_recognizer = luis_recognizer
        self._booking_dialog_id = booking_dialog.id

        self.add_dialog(text_prompt)
        self.add_dialog(booking_dialog)
        self.add_dialog(wf_dialog)

        self.initial_dialog_id = "WFDialog"

    async def intro_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            await step_context.context.send_activity(
                MessageFactory.text(
                    "NOTE: LUIS is not configured. To enable all capabilities, add 'LuisAppId', 'LuisAPIKey' and "
                    "'LuisAPIHostName' to the appsettings.json file.",
                    input_hint=InputHints.ignoring_input,
                )
            )

            return await step_context.next(None)
        
        message_text = (
            str(step_context.options)
            if step_context.options
            else "What can I help you with today?"
        )
        prompt_message = MessageFactory.text(
            message_text, message_text, InputHints.expecting_input
        )

        return await step_context.prompt(
            TextPrompt.__name__, PromptOptions(prompt=prompt_message)
        )

    async def act_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            # LUIS is not configured, we just run the BookingDialog path with an empty BookingDetailsInstance.
            return await step_context.begin_dialog(
                self._booking_dialog_id, BookingDetails()
            )

        # Call LUIS and gather any potential booking details. (Note the TurnContext has the response to the prompt.)
        intent, luis_result = await LuisHelper.execute_luis_query(
            self._luis_recognizer, step_context.context
        )
        print(intent)
        if intent == Intent.BOOK_FLIGHT.value and luis_result:
            # Show a warning for Origin and Destination if we can't resolve them.
            await MainDialog._show_warning_for_unsupported_cities(
                step_context.context, luis_result
            )

            # Run the BookingDialog giving it whatever details we have from the LUIS call.
            return await step_context.begin_dialog(self._booking_dialog_id, luis_result)

        elif intent == Intent.CANCEL.value:
            cancel_text = "See you soon!"
            cancel_message = MessageFactory.text(
                cancel_text, cancel_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(cancel_message)

        elif intent == Intent.CONFIRM.value:
            confirm_text = "Good!"
            confirm_message = MessageFactory.text(
                confirm_text, confirm_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(confirm_message)
            
        elif intent == Intent.NONE_INTENT.value:
            none_text = """Sorry, I'm programmed to book flights. Please try to
            express your intent clearly."""
            none_message = MessageFactory.text(
                none_text, none_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(none_message)
                       
        else:
            didnt_understand_text = (
                "Sorry, I didn't get that. Please try asking in a different way"
            )
            didnt_understand_message = MessageFactory.text(
                didnt_understand_text, didnt_understand_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(didnt_understand_message)

        return await step_context.next(None)

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # If the child dialog ("BookingDialog") was cancelled or the user failed to confirm,
        # the Result here will be null.
        if step_context.result is not None:
            result = step_context.result
            
            flight_card = FlightItineraryCard(result)
            card = flight_card.create_attachment()
            response = MessageFactory.attachment(card)
            await step_context.context.send_activity(response)
            
            msg_txt = f"""Your flight is confirmed for {result.n_adults}
            adult(s) and {result.n_children}, from {result.or_city} to
            {result.dst_city}, on {result.str_date} and return on
            {result.end_date}.
            All of the booking details will be sent to you via email. Have a
            good flight!
            """
            message = MessageFactory.text(msg_txt, msg_txt, InputHints.ignoring_input)
            await step_context.context.send_activity(message)

        # prompt_message = "Do you want something else?"
        # return await step_context.replace_dialog(self.id, prompt_message)
        return await step_context.end_dialog()

    @staticmethod
    async def _show_warning_for_unsupported_cities(
        context: TurnContext, luis_result: BookingDetails
    ) -> None:
        """
        Shows a warning if the requested From or To cities are recognized as entities but they are not in the Airport entity list.
        In some cases LUIS will recognize the From and To composite entities as a valid cities but the From and To Airport values
        will be empty if those entity values can't be mapped to a canonical item in the Airport.
        """
        if luis_result.unsupported_airports:
            message_text = (
                f"Sorry but the following airports are not supported:"
                f" {', '.join(luis_result.unsupported_airports)}"
            )
            message = MessageFactory.text(
                message_text, message_text, InputHints.ignoring_input
            )
            await context.send_activity(message)
