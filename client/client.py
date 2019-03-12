import asyncio
import io
import ssl
import sys
import json

import base64

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.errors import ErrorCodes
from h2.events import (
    SettingsAcknowledged, DataReceived, StreamEnded, PushedStreamReceived
)
from h2.exceptions import ProtocolError


class H2Protocol(asyncio.Protocol):

    def __init__(self):
        print("------------ init ------------")
        config = H2Configuration(client_side=True, header_encoding='utf-8')
        self.conn = H2Connection(config=config)
        self.transport = None
        self.stream_data = {}

    def send_request(self):
        print("------------ send_request ------------")
        request_headers = [(':method', 'POST'),
                           (':scheme', 'https'),                           
                           (':path', '/index.html'),
                           (':authority', 'localhost'),
                           ('user-agent', 'hyper-h2/1.0.0')]

        # self.conn.send_headers(1, request_headers, end_stream=True)

        # headers = collections.OrderedDict(request_headers)
        '''
        with open("myfile", "rb") as f:
            byte = f.read(1024)
            while byte != b"":
                # Do stuff with byte.
                byte = f.read(1)
        '''

        with open(sys.argv[1], "rb") as image_file:
            encoded_string=base64.b64encode(image_file.read())
        
        print("\n ENCODED STRING FOR IMAGE : " + str(encoded_string)+ "\n")
        
        tags = []
        i = 0
        for arg in sys.argv :
            i = i+1
            if i>2 :
                tags.append(arg)



        data = {'file_name': sys.argv[1],
                'image': encoded_string.decode('utf-8'),
                 'tags': tags }
        print(data)

        encoded_data = json.dumps(data).encode('utf-8')
        '''
        data_json = json.dumps(
            {"headers": headers, "body": encoded_data}, indent=4
        ).encode("utf8")
        '''

        # data = encoded_string

        self.conn.send_headers(1, request_headers, end_stream=False)
        self.conn.send_data(1, encoded_data, end_stream=True)


    def connection_made(self, transport):
        print("------------ connection_made ------------")
        self.transport = transport
        self.conn.initiate_connection()
        self.transport.write(self.conn.data_to_send())

    def data_received(self, data):
        print("------------ data_received ------------")
        try:
            events = self.conn.receive_data(data)
        except ProtocolError as e:
            self.transport.write(self.conn.data_to_send())
            self.transport.close()
        else:
            self.transport.write(self.conn.data_to_send())
            for event in events:
                print(event)
                if isinstance(event, SettingsAcknowledged):
                    print(" ---> 1 ")
                    self.send_request()
                if isinstance(event, DataReceived):
                    print(" ---> 2 ")
                    self.receive_data(event.data, event.stream_id)
                if isinstance(event, StreamEnded):
                    print(" ---> 3 ")
                    self.log_data(event.stream_id)
                if isinstance(event, PushedStreamReceived):
                    print(" ---> 4 ")
                    self.log_push(event.headers, event.parent_stream_id, event.pushed_stream_id)
        self.transport.write(self.conn.data_to_send())

    def log_push(self, headers, pid, sid):
        print("------------ log_push ------------")
        print("Received server push of stream id: " + str(sid))

    def receive_data(self, data, stream_id):
        print("------------ receive_data ------------")
        try:
            if stream_id in self.stream_data:
                stream_data = self.stream_data[stream_id]
            else:
                stream_data = io.BytesIO()
                self.stream_data[stream_id] = stream_data
        except KeyError:
            self.conn.reset_stream(
                stream_id, error_code=ErrorCodes.PROTOCOL_ERROR
            )
        else:
            stream_data.write(data)

    def log_data(self, stream_id):
        print("------------ log_data ------------")
        data = self.stream_data[stream_id]
        data.seek(0)
        # print('=======DATA, STREAM ID: ' + str(stream_id) + '=======')
        # print(data.read().decode('UTF-8'))
        print(json.loads(data.read().decode('utf-8'))['body'])
        print('=================================')



print("------------ main ------------")
ssl_context = ssl._create_unverified_context()
# ssl_context.options |= (
#         ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
# )
# ssl_context.set_ciphers("ECDHE+AESGCM")
# ssl_context.load_cert_chain(certfile=RESOURCE + "cert.crt", keyfile=RESOURCE + "cert.key")
ssl_context.check_hostname = False
# ssl_context.load_verify_locations(RESOURCE + 'cert.crt')
ssl_context.load_cert_chain(certfile="cert.crt", keyfile="cert.key")

loop = asyncio.get_event_loop()
coro = loop.create_connection(H2Protocol, host='localhost', port=8443, ssl=ssl_context)
loop.run_until_complete(coro)
loop.run_forever()
loop.close()