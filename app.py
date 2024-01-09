from flask import Flask
from flask_sockets import Sockets
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

import json


app = Flask(__name__)
sockets = Sockets(app)

from api import api
app.register_blueprint(api)

from audio_socket import audio_socket
sockets.register_blueprint(audio_socket)

HTTP_SERVER_PORT = 8000

print("Server listening on: http://localhost:" + str(HTTP_SERVER_PORT))
print("Route for media: ws://localhost:" + str(HTTP_SERVER_PORT) + '/media')

if __name__ == '__main__':
    server = pywsgi.WSGIServer(('localhost', HTTP_SERVER_PORT), app, handler_class=WebSocketHandler)
    server.serve_forever()
