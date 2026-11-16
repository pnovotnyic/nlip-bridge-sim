"""A minimal application for nlip_server (run in stage1/venvs/server): it answers every message with a new text
message 'ok'. Unlike the library's echo application it does not return the request, so whatever the library does
with tokens and control messages is visible."""
from nlip_sdk.nlip import NLIP_Factory
from nlip_server.server import NLIP_Session, SafeApplication, setup_server


class AckSession(NLIP_Session):
    def execute(self, msg):
        return NLIP_Factory.create_text("ok")


class AckApplication(SafeApplication):
    def create_session(self):
        return AckSession()


app = setup_server(AckApplication())
