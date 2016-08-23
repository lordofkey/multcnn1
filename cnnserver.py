# _*_coding:utf-8_*_
import socket
import numpy as np
import struct
import Queue
import threading
import os
import time
import dpmanager
import logging

logging.basicConfig(filename='cnnserver.log', filemode='a')
Qcon = Queue.Queue(200)
HOST = '0.0.0.0'
PORT = 8145
inner_host = '0.0.0.0'
inner_port = 9231
PARAM_LEN = 128
SAVE_IMG = 1

try:
    mmanager = dpmanager.ModelManage(inner_host, inner_port)
except:
    logging.exception("Exception Logged")
#接收线程
def receivedata():
    while True:
        try:
            conn = Qcon.get()
            param = conn.recv(PARAM_LEN)
            conn.sendall('s')
            width = struct.unpack('Q', conn.recv(8))[0]
            height = struct.unpack('Q', conn.recv(8))[0]
            file_size = width * height
            recv_size = 0
            data = ''
            while recv_size < file_size:
                if file_size - recv_size > 10240:
                    temp_recv = conn.recv(10240)
                    data += temp_recv
                else:
                    temp_recv = conn.recv(file_size - recv_size)
                    data += temp_recv
                recv_size = len(data)
            img = np.fromstring(data, dtype=np.uint8)
            img = img.reshape(height, width)
            mmanager.put(param, conn, img)
        except dpmanager.NoModelResource:           
            conn.sendall('failed')
            conn.close()
            continue
        except:
            conn.close()
            logging.exception("err receiving from client")
            continue
        ##################################################################################


def updateshow():
    while True:
        time.sleep(0.2)
        connum = Qcon.qsize()
        serlist = mmanager.checkload()
        os.system('clear')

        print '################################################################################'
        print '#      接收列队负载：', connum
        for ser in serlist:
            print '#      服务器', ser[0], '负载：', ser[1]

#创建显示线程
try:
    sthread = threading.Thread(target=updateshow)
    sthread.setDaemon(True)
    sthread.start()

#创建接收线程
    for i in range(100):
        sthread = threading.Thread(target=receivedata)
        sthread.setDaemon(True)
        sthread.start()
except:
    logging.exception("thread starting Exception Logged")

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))
s.listen(1)
while True:
    try:
        conn, addr = s.accept()
        Qcon.put(conn)
    except:
        logging.exception("socket acception Exception Logged")
        continue

