import logging
import socket
import struct
import threading
import time

SR = True
# lab works well verify
verify = True  # never open it when rdt is used.it just use for test.

# recv should be bigger than send.
request_connect = b"hello,i want connect"
ack_connect = b"ok,let's connect"
hand_connect = b"come on"


class connectException(Exception):
    pass


class noinfoException(Exception):
    pass


class rdt:
    def __init__(self, socket: socket.socket, address: (str, int), config):
        # envir value
        logging.info("init rdt in " + str(address))
        self.configure = config
        self.socket = socket
        self.send_buffer = []
        self.recv_buffer = []
        self.recv_max_seq = -1
        self.timeout = config["timeout"]
        self.rdt_timeoutStep = int(config["rdt_timeout"] / (config["timeout"] + 0.1))
        self.base = 0
        self.nextsequm = 0
        self.windowSize = config["windowsize"]
        self.group_size = 100  # bytes ,that is 100 bytes a group
        self.timer = 0
        self.MaxAckSeq = -1
        self.address = address
        self.connected = False
        self.Lock = threading.Lock()  # this could be optimized.
        # init rdt
        self.socket.settimeout(self.timeout)
        # optional
        self.sr_recv = []

    def init_connect(self):
        try:
            self.socket.sendto(request_connect, self.address)
            logging.info("send request connect to " + str(self.address))
            accept, a = self.socket.recvfrom(len(ack_connect))
        except socket.timeout:
            logging.info("rdt connect failed with " + str(self.address))
            return
        if not accept == ack_connect:
            logging.info("rdt connect failed with " + str(self.address))
            return
        else:
            logging.info("receive ack connect to " + str(self.address))
            self.socket.sendto(hand_connect, self.address)
            logging.info("send hand connect to " + str(self.address))
        self.connected = True
        self._init_threads(self)
        logging.info("rdt connect successful with " + str(self.address))

    def bind(self, address):
        logging.info("the sever bind in " + str(self.address))
        self.socket.bind(self.address)

    def accept(self):
        try:
            receive, a1 = self.socket.recvfrom(1000)
            logging.info("receive " + str(receive) + " from " + str(a1))
            if receive == request_connect:
                self.socket.sendto(ack_connect, a1)

                logging.info("send ack connect to " + str(a1))
            else:
                logging.info("rdt accept failed from " + str(a1))
                return None
            receive, a2 = self.socket.recvfrom(1000)
            logging.info("receive " + str(receive) + " from " + str(a1))
        except socket.timeout:
            return None
        if receive == hand_connect and a1 == a2:
            newrdt = rdt(self.socket, a1, self.configure)
            logging.info("connect successful with " + str(a1))
            newrdt.connected = True
            self._init_threads(newrdt)
            return newrdt, a1
        else:
            logging.info("rdt accept failed from " + str(self.address))
            return None

    # All the functions below # need to make the connected flag True.
    # Here we need to consider the process of seq sequence number from 0xff->0x0
    # this will cause this problem in transfer 100bytes*0x7f.
    def send_thread(self):
        # use with self.Lock: in this code
        while True:
            time.sleep(0.1)
            with self.Lock:
                if len(self.send_buffer) == 0:
                    continue
                if not self.connected:
                    break
                # if len(self.send_buffer)<self.windowSize or self.nextsequm-self.base == self.windowSize:
                #    continue
                if self.nextsequm - self.base < len(self.send_buffer) and self.nextsequm < self.base + self.windowSize:
                    logging.info(
                        "sending chunk data " + str(self.send_buffer[self.nextsequm - self.base]) + " to " + str(
                            self.address))
                    self.socket.sendto(self.send_buffer[self.nextsequm - self.base], self.address)
                    # Recycle the serial number
                    if self.nextsequm == 0x7f:
                        self.nextsequm = 0
                    else:
                        self.nextsequm += 1
                # timer setting
                if self.MaxAckSeq >= self.base:
                    # remove already ack packets
                    self.send_buffer = self.send_buffer[self.MaxAckSeq + 1 - self.base:]
                    self.base = self.MaxAckSeq + 1
                    self.timer = 0
                else:
                    if self.timer <= self.rdt_timeoutStep:
                        self.timer += 1
                    else:
                        logging.info("timer is max when base = " + str(self.base))
                        logging.info("re transfer seq from " + str(self.base) + " to " + str(self.nextsequm))
                        for i in range(self.nextsequm - self.base):
                            self.socket.sendto(self.send_buffer[i], self.address)
                        self.timer = 0

    # get 1 byte
    def recv_thread(self):
        while True:
            time.sleep(0.1)
            with self.Lock:
                try:
                    data, address = self.socket.recvfrom(1000)
                    logging.info("recv " + str(data) + " from " + str(address))
                    first_byte = data[:1]
                    type, seq = self.parseFirstByte(first_byte)
                    if type == 0:  # a ack_type
                        logging.info("receive ack " + str(seq))
                        if seq > self.MaxAckSeq:
                            self.MaxAckSeq = seq
                    else:
                        dataFrame = data[1:]
                        # lengthbyte = dataFrame[:1]
                        # final,length = self.parseSecondByte(lengthbyte)
                        if self.recv_max_seq + 1 == seq:
                            self.recv_max_seq = seq
                            self.recv_buffer.append(first_byte + dataFrame)
                            if not verify:
                                self.socket.sendto(self.constructFirst(0, self.recv_max_seq), self.address)
                                logging.info("send ack " + str(self.recv_max_seq) + " ..... ")
                            else:

                                # just for test
                                if self.recv_max_seq == 5:
                                    logging.info("don't send ack lalalala")
                                else:
                                    self.socket.sendto(self.constructFirst(0, self.recv_max_seq), self.address)
                                    logging.info("send ack " + str(self.recv_max_seq) + " ..... ")
                                # if random.random()<0.7:
                                #   self.socket.sendto(self.constructFirst(0,self.recv_max_seq),self.address)
                                #   logging.info("send ack "+str(self.recv_max_seq)+" ..... ")
                                # else :
                                #   logging.info("random verify it works")
                        else:
                            if self.recv_max_seq != -1:
                                if not verify:
                                    self.socket.sendto(self.constructFirst(0, self.recv_max_seq), self.address)
                                else:  # just for test
                                    logging.info("don't send ack lalalala")

                    # if it's a ack then read seq and renew maxack
                    # else it is a data, read all 1+100 bytes and store to recv_buffer
                    # ,judge seq is right or not, if right,store to buffer
                    # send maxseq ack to host
                except socket.timeout:
                    continue

    def sr_send_thread(self):
        # use with self.Lock: in this code
        timers = {}
        for i in range(self.windowSize):
            timers[i] = 0
        while True:
            time.sleep(0.1)
            with self.Lock:
                if len(self.send_buffer) == 0:
                    continue
                if not self.connected:
                    break
                # if len(self.send_buffer)<self.windowSize or self.nextsequm-self.base == self.windowSize:
                #    continue
                if self.nextsequm - self.base < len(self.send_buffer) and self.nextsequm < self.base + self.windowSize:
                    logging.info(
                        "sending chunk data " + str(self.send_buffer[self.nextsequm - self.base]) + " to " + str(
                            self.address))
                    self.socket.sendto(self.send_buffer[self.nextsequm - self.base], self.address)
                    # Recycle the serial number
                    if self.nextsequm == 0x7f:
                        self.nextsequm = 0
                    else:
                        self.nextsequm += 1
                # timer setting
                for i in range(self.nextsequm - self.base):
                    if i + self.base not in self.sr_recv:
                        timers[i] += 1
                        if timers[i] > self.rdt_timeoutStep:
                            self.socket.sendto(self.send_buffer[i], self.address)
                            logging.info("timeout and resend " + str(self.send_buffer[i]) + " to " + str(self.address))
                            timers[i] = 0

                # self.base renew ,self.sr_recv = [] it is a seq ack recv list
                offset = 0
                while self.base + offset in self.sr_recv:
                    offset += 1
                self.base += offset
                # renew send buffer
                self.send_buffer = self.send_buffer[offset:]
                # update timers
                for i in range(self.windowSize):
                    if i + offset < self.windowSize:
                        timers[i] = timers[i + offset]
                    else:
                        timers[i] = 0
                # update sr_recvs reduce
                for i in self.sr_recv:
                    if i < self.base:
                        self.sr_recv.remove(i)

    def sr_recv_thread(self):
        sr_base = 0
        sr_tmp_buffers = {}
        while True:
            time.sleep(0.1)
            with self.Lock:
                try:
                    data, address = self.socket.recvfrom(1000)
                    logging.info("recv " + str(data) + " from " + str(address))
                    first_byte = data[:1]
                    type, seq = self.parseFirstByte(first_byte)
                    if type == 0:  # a ack_type
                        logging.info("receive ack " + str(seq))
                        if seq not in self.sr_recv:
                            self.sr_recv.append(seq)
                    else:
                        if seq < sr_base + self.windowSize:
                            if not verify:
                                self.socket.sendto(self.constructSecond(0, seq), self.address)
                                logging.info("send ack " + str(seq) + " to " + str(self.address))
                            else:
                                if not seq == 2:
                                    self.socket.sendto(self.constructSecond(0, seq), self.address)
                                    logging.info("send ack " + str(seq) + " to " + str(self.address))
                        if seq >= sr_base and seq < sr_base + self.windowSize:
                            if seq not in sr_tmp_buffers:
                                sr_tmp_buffers[seq] = data
                        offset = 0
                        while sr_base + offset in sr_tmp_buffers:
                            self.recv_buffer.append(sr_tmp_buffers[sr_base + offset])
                            offset += 1
                        for i in range(offset):
                            del sr_tmp_buffers[sr_base + i]
                        sr_base += offset

                        # lengthbyte = dataFrame[:1]
                        # final,length = self.parseSecondByte(lengthbyte)

                    # if it's a ack then read seq and renew maxack
                    # else it is a data, read all 1+100 bytes and store to recv_buffer
                    # ,judge seq is right or not, if right,store to buffer
                    # send maxseq ack to host
                except socket.timeout:
                    continue


    def parseSecondByte(self, second):
        secondInt, = struct.unpack("!B", second)
        if secondInt & 0x80 == 0:
            return 0, secondInt & 0x7f  # return ack_type
        else:
            return 1, secondInt & 0x7f  # return data_type

    def parseFirstByte(self, first):
        firstInt, = struct.unpack("!B", first)
        if firstInt & 0x80 == 0:
            return 0, firstInt & 0x7f  # return ack_type
        else:
            return 1, firstInt & 0x7f  # return data_type

    # type 0 is ack,and 1 is data
    def constructFirst(self, type, seq):
        number = (type << 7) | seq
        return struct.pack("!B", number)

    # final 0 is no next ,and 1 is has next
    def constructSecond(self, final, length):
        number = (final << 7) | length
        return struct.pack("!B", number)

    def gbn_send(self, info: str):
        with self.Lock:
            data = info.encode()
            import math
            max_group_number = math.ceil(len(data) / self.group_size)
            if len(self.send_buffer) == 0:
                final_buffer_seq = self.base
            else:
                type, seq = self.parseFirstByte(self.send_buffer[-1][:1])
                if seq == 0x7f:
                    final_buffer_seq = 0
                else:
                    final_buffer_seq = seq + 1
            for i in range(max_group_number):
                firstchunk = self.constructFirst(1, final_buffer_seq + i)
                if i == max_group_number - 1:  # the last chunk
                    secondchunk = self.constructSecond(0, len(data) - self.group_size * i)
                    datachunk = data[self.group_size * i:]
                    datachunk = datachunk + b"\x00" * (self.group_size - len(datachunk))
                else:
                    secondchunk = self.constructSecond(1, self.group_size)
                    datachunk = data[self.group_size * i:self.group_size * (i + 1)]
                # construct a packet.
                self.send_buffer.append(firstchunk + secondchunk + datachunk)

    # gbn recv one packet when be called each time.
    def gbn_recv(self):
        with self.Lock:
            packet_number = 0
            final_packet_length = 0
            for index, packet in enumerate(self.recv_buffer):
                final, length = self.parseSecondByte(packet[1:2])
                if final == 0:
                    packet_number = index + 1
                    final_packet_length = length
                    break
                else:
                    if index == len(self.recv_buffer) - 1:
                        raise noinfoException
            buffer = b''
            for i in range(packet_number):
                if i == packet_number:
                    buffer += self.recv_buffer[i][2:2 + final_packet_length]
                else:
                    buffer += self.recv_buffer[i][2:102]
            self.recv_buffer = self.recv_buffer[packet_number:]
            return buffer.decode()

    def _init_threads(self, newrdt):
        if not SR:
            send = threading.Thread(name="send", target=newrdt.send_thread, daemon=False)
        else:
            send = threading.Thread(name="send", target=newrdt.sr_send_thread, daemon=False)
        if not SR:
            recv = threading.Thread(name="recv", target=newrdt.recv_thread, daemon=False)
        else:
            recv = threading.Thread(name="recv", target=newrdt.sr_recv_thread, daemon=False)
        send.start()
        recv.start()
