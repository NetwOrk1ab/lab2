import socket
import rdt
import logging
import time

logging.basicConfig(level=logging.INFO)

server_host = "127.0.0.1"
server_port = 10000
TIMEOUT = 1
WINDOWSIZE = 10


if __name__=="__main__":
    config = {"server_host":"127.0.0.1","server_port":10000,"timeout":1,"rdt_timeout":10,"windowsize":10}
    clientsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    server_bind = (server_host,server_port)
    rdt = rdt.rdt(clientsocket,server_bind,config)
    rdt.bind(server_bind)
    while True:
        time.sleep(1)
        a = rdt.accept()
        if a!=None:
            clientrdt,address = a
            break
    clientsocket.send("b"*100)
    while True:
        try:
            time.sleep(2)
            print(clientrdt.gbn_recv())
        except rdt.noinfoException:
            pass
