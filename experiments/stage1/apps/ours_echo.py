import os

from nlipeval.nlip.transport import create_app, echo_handler

app = create_app(echo_handler, upload_url=os.environ.get("NLIP_UPLOAD_URL"), issue_conversation=False)
