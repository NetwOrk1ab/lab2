import logging
import socket
import time

import rdt

logging.basicConfig(level=logging.INFO)

server_host = "127.0.0.1"
server_port = 10000
TIMEOUT = 1
WINDOWSIZE = 10

if __name__ == "__main__":
    config = {"server_host": "127.0.0.1", "server_port": 10000, "timeout": 1, "rdt_timeout": 10, "windowsize": 10}
    clientsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    remote_server_address = (server_host, server_port)
    send = rdt.rdt(clientsocket, remote_server_address, config)
    send.init_connect()
    infomation = "a" * 100 + "b" * 100
    send.gbn_send(infomation)
    send.gbn_send("abcd" * 100)
    while True:
        time.sleep(2)
        try:
            print(send.gbn_recv())
        except rdt.noinfoException:
            pass
    # print(send.gbn_recv())
    a = 1  # it just for debug breakpoint
    # send.close()
