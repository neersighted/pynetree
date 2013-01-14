#!/usr/bin/env python
"""
pynetree -- minecraft classic server emulator

Usage:
    pynetree [-v] [-i <ip>] [-p <port>] <message>
    pynetree -V | --version
    pynetree -h | --help

Options:
    -i <ip>, --ip=<ip>        Set the ip to listen on [default: 0.0.0.0].
    -p <port>, --port=<port>  Set the port to listen on [default: 25565].
    -v, --verbose             Print verbose output.
    -V, --version             Print the version and exit.
    -h, --help                Print this message and exit.
"""
version = "2.0"

import binascii
from docopt import docopt
from multiprocessing import Process
from os import urandom
import requests
from select import select
import socket
import struct
from time import sleep


class Server:
    def __init__(self,
                 ip="0.0.0.0",
                 port=25565,
                 message="The server is currently offline!"):
        self.ip      = ip
        self.port    = port
        self.message = message
        self.socket  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.backlog = 1
        self.packet  = struct.pack("B64s", 14, self.message.encode())

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def bind(self):
        self.socket.bind((self.ip, self.port))
        self.socket.listen(self.backlog)

    def receive(self):
        conn, addr = self.socket.accept()

        return ServerConnection(conn, self.packet)

    def fileno(self):
        return self.socket.fileno()

class ServerConnection:
    def __init__(self,
                 socket,
                 reply):
        self.socket = socket
        self.reply = reply

    def handle(self):
        self.socket.recv(64)

        self.socket.send(self.reply)

        return self.reply

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

        return self.socket

    def fileno(self):
        return self.socket.fileno()

class HeartBeat:
    def __init__(self,
                 url="http://minecraft.net/heartbeat.jsp",
                 name="A Minecraft Server",
                 port=25565,
                 current_users=0,
                 max_users=10,
                 salt=None):
        if not salt:
            self.salt = self.gen_salt()
        self.url      = url
        self.params   = {
            "name":     name,
            "port":     port,
            "users":    current_users,
            "max":      max_users,
            "salt":     self.salt,
            "public":   "true",
            "version":  7
        }

    def beat(self):
        request = requests.post(self.url, params=self.params)

        if request.status_code == requests.codes.ok:
            return (True, request.text)
        else:
            return (False, request.status_code)

    def gen_salt(self):
        return binascii.hexlify(urandom(6)).decode()


def server_loop(**options):
    server = Server(
        options["--ip"],
        int(options["--port"]),
        options["<message>"]
    )
    server.bind()

    sockets = [server]

    while True:
        input, output, exception = select(sockets,[],[])

        for s in input:
            if s == server:
                sockets.append(s.receive())
            else:
                s.handle()
                s.close()

                sockets.remove(s)

def beat_loop(**options):
    beat = HeartBeat

    while True:
        sleep(30)

        beat.beat()


if __name__ == '__main__':
    options = docopt(__doc__, version=version, help=True)

    Process(target=server_loop, kwargs=options).start()
    Process(target=beat_loop, kwargs=options).start()
