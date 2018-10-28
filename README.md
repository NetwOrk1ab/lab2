this is a gbn rdt protocol base on UDP
======================================

>for rdt class,it wrapper udp packet to a high level protocol.<br>with rdt,all data transfer will be reliable.

### class rdt :

##### create a rdt object : 
```python
# for this socket should be a udp socket.
# address should be a tuple with (host,ip),it is remote server address.
# config is a dic in python here is example
import rdt
config = {"server_host":"127.0.0.1","server_port":10000,"timeout":1,"rdt_timeout":10,"windowsize":10}
rdt = rdt(socket,address,config)
```

#### init a connect with remote server:
just call init_connect,it will connect with rdt remote server
that will begin two threads ,one for send,one for recv.
```python
rdt.init_connect()
```

#### bind on server 
a wrap for udb bind ,actually argument is no use.
it will use self address.
```python
rdt.bind(address) # here address is no use.
```

#### accept from client
just like a udp return a clientrdt,and a address
```python
clientrdt,address = rdt.accept()
```

#### gbn_send send data to another host
```python
information = "some string here"
rdt.gbn_send(info=information)
```

#### gbn_recv receive from another host
if no packet to recv ,raise noinfoException````
```python
information = rdt.gbn_recv() # just a packet .
```
