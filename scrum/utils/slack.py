from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from django.conf import settings


class SlackNotifier:
    def __init__(self):
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self.channel = settings.SLACK_DEFAULT_CHANNEL

    def send_message(self, message):
        try:
            response = self.client.chat_postMessage(channel=self.channel, text=message)
            return response
        except SlackApiError as e:
            print(f"Error sending message to Slack: {e.response['error']}")
            return None
