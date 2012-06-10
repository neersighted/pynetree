#!/usr/bin/env python

import os
import sys
import json
import time
import struct
import socket
import requests
import binascii
import multiprocessing


def loadConfig(file):
    """Loads the config"""
    try:
        config = json.load(open(file))
        return config

    except IOError:
        print("[pynetree] error: config could not be found")
        exit()


def fakeBeatConnection(beat_list_location, beat_name, beat_port,\
                    beat_current_users, beat_max_users, beat_salt):
    """Pings a Minecraft Classic Server List"""
    beat_params = {
                    "name": beat_name,
                    "port": beat_port,
                    "users": beat_current_users,
                    "max": beat_max_users,
                    "salt": beat_salt,
                    "public": "true",
                    "version": 7
    }

    beat = requests.get(beat_list_location, params=beat_params)

    if debug:
        print("[fakebeat:debug] beat url: %s" % beat.url)
        print("[fakebeat:debug] beat headers: %s" % beat.headers)

    return beat.status_code, beat.text


def fakeBeatStatus(beat, status_code, data):
    """Prints the status of a heartbeat"""
    if status_code == requests.codes.ok:
        status = "OK"
    else:
        status = "FAILED"

    print("[fakebeat] sent: %s" % beat)
    print("[fakebeat] status: %s" % status)

    if status == "OK":
        print("[fakebeat] returned data: %s" % data)
    else:
        print("[fakebeat] error code: %s" % status_code)


def fakeBeat(beats, beat_name, beat_port, beat_current_users,\
            beat_max_users, beat_salt, beat_time):
    """Automaticly connects to Minecraft Classic Server Lists"""
    total_count = 0
    individual_count = 0

    try:
        while True:
            time.sleep(beat_time)

            for beat in beats:
                beat_list_name = beats[beat]["name"]
                beat_list_location = beats[beat]["location"]

                beat_override_salt = beats[beat]["override_salt"]

                if beat_override_salt:
                    beat_salt = beat_override_salt

                if debug:
                    print("[fakebeat:debug] beat salt: %s" % beat_salt)
                    print("[fakebeat:debug] beat list: %s (%s)" % (beat_list_name,\
                                                    beat_list_location))

                beat = fakeBeatConnection(beat_list_location, beat_name,\
                                        beat_port, beat_current_users,\
                                        beat_max_users, beat_salt)

                beat_status_code = beat[0]
                beat_data = beat[1]

                fakeBeatStatus(beat_list_name, beat_status_code, beat_data)
                individual_count += 1
            total_count += 1

    except KeyboardInterrupt:
        if stats:
            print("[fakebeat:stats] individual beats: %s" % individual_count)
            print("[fakebeat:stats] total beats: %s" % total_count)
        print("[fakebeat] stopping...")


def simServerConnection(conn, addr):
    """Simulates a Minecraft Classic server connection"""
    data = conn.recv(64)

    client_name = data[2:].decode().replace(chr(0), "")
    client_name = client_name.replace(" ", "").replace("\r\n", "")
    client_ip = addr[0]

    raw_packet = binascii.hexlify(packet)

    print("[simserver] connect: %s (%s)" % (client_name, client_ip))
    conn.send(packet)
    print("[simserver] transmit: %s (%s)" % (client_name, client_ip))
    if debug:
        print("[simserver:debug] packet: %s (%s)" % (packet, raw_packet))
    conn.shutdown(socket.SHUT_RDWR)
    conn.close()
    print("[simserver] disconnect: %s (%s)" % (client_name, client_ip))


def simServer(server_ip, server_port, server_message):
    """Simulates a Minecraft Classic server"""
    count = 0

    global packet
    packet_struct = struct.Struct("B64s")
    packet_type = 14

    packet = packet_struct.pack(packet_type, server_message.encode())
    packet = packet.decode().replace(chr(0), chr(32)).encode()

    try:
        while True:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server.bind((server_ip, server_port))
                print("[simserver] bind: %s:%s" % (server_ip, server_port))
                break

            except Exception as e:
                print("[simserver] error: bind failed, is the port open?")
                print("[simserver] error details:")
                print(e)
                exit()
        while True:
            server.listen(1)
            conn, addr = server.accept()
            multiprocessing.Process(target=simServerConnection,\
                                    args=(conn, addr)).start()
            count += 1

    except KeyboardInterrupt:
        if stats:
            print("[simserver:stats] clients served: %s" % count)
        print("[simserver] stopping...")


def main():
    """pynetree - minecraft classic server emulator"""
    try:
        print(main.__doc__)

        print("[pynetree] loading config...")

        config = loadConfig("config")

        global debug, stats
        debug = config["debug"]
        stats = config["stats"]

        run_simserver = config["simserver"]["enabled"]
        server_ip = config["simserver"]["server_ip"]
        server_port = config["simserver"]["server_port"]
        server_message = config["simserver"]["server_message"]

        run_fakebeat = config["fakebeat"]["enabled"]
        beats = config["fakebeat"]["beats"]
        beat_time = config["fakebeat"]["beat_time"]
        beat_name = config["fakebeat"]["name"]
        beat_port = config["fakebeat"]["port"]
        beat_current_users = config["fakebeat"]["current_users"]
        beat_max_users = config["fakebeat"]["max_users"]

        use_beat_salt_file = config["fakebeat"]["salt_file"]["enabled"]
        beat_salt_file = config["fakebeat"]["salt_file"]["file"]

        if use_beat_salt_file:
            beat_salt = open(beat_salt_file, "r").readlines()
            beat_salt = "".join(beat_salt).replace("\n", "")
        else:
            beat_salt = config["fakebeat"]["salt"]

        if debug:
            print("[pynetree:debug] config: %s" % config)
        print("[pynetree] config loaded...")

        if run_fakebeat == False and run_simserver == False:
            print("[pynetree] error: no modules enabled")
            exit()
        if run_fakebeat:
            print("[fakebeat] starting...")
            fakebeat = multiprocessing.Process(target=fakeBeat, args=(beats,\
                                            beat_name, beat_port,\
                                            beat_current_users,\
                                            beat_max_users,\
                                            beat_salt, beat_time))
            fakebeat.start()

        if run_simserver:
            print("[simserver] starting...")
            simserver = multiprocessing.Process(target=simServer,\
                                                args=(server_ip,\
                                                server_port, server_message))
            simserver.start()

        while True:
            pass

    except KeyboardInterrupt:
        exit()

    except KeyError as e:
        print("[pynetree] error: malformed config (or missing item)")
        print("[pynetree] error details:")
        print(e)
        exit()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
