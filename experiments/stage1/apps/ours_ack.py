import os

from nlipeval.nlip.transport import ack_handler, create_app

app = create_app(ack_handler, upload_url=os.environ.get("NLIP_UPLOAD_URL"))
