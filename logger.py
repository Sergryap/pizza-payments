import logging
from telegram.bot import Bot


class BotLogsHandler(logging.Handler):

    def __init__(self, token: str, chat_id: str):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.bot = Bot(token=self.token)

    def emit(self, record: logging.LogRecord) -> None:
        log_entry = self.format(record)
        self.bot.send_message(chat_id=self.chat_id, text=log_entry)
