# _*_coding:utf-8_*_
import socket
import numpy as np
import struct
import datetime
import Queue
import threading
import os
import time
import dpmanager

Qcon = Queue.Queue(200)
HOST = '0.0.0.0'
PORT = 8145
inner_host = '0.0.0.0'
inner_port = 9231

PARAM_LEN = 128
SAVE_IMG = 1

mmanager = dpmanager.ModelManage(inner_host, inner_port)

def receivedata():
    while True:
        try:
            tmp = Qcon.get()
            conn = tmp[0]
            process_num = tmp[1]
            param = conn.recv(PARAM_LEN)
        except:
            continue

        ############################################
        try:
            conn.sendall('s')
        except:
            continue
        try:
            width = struct.unpack('Q', conn.recv(8))[0]
            height = struct.unpack('Q', conn.recv(8))[0]
        except:
            continue
        file_size = width * height
        recv_size = 0
        data = ''
        try:
            while recv_size < file_size:
                if file_size - recv_size > 10240:
                    temp_recv = conn.recv(10240)
                    data += temp_recv
                else:
                    temp_recv = conn.recv(file_size - recv_size)
                    data += temp_recv
                recv_size = len(data)
        except:
            continue
        img = np.fromstring(data, dtype=np.uint8)
        img = img.reshape(height, width)
        mmanager.put(param, img, process_num)
        ##################################################################################
        m_rlt = ''
        try:
            conn.sendall(m_rlt)
        except:
            continue
        conn.close()


def updateshow():
    while True:
        connum = Qcon.qsize()
        time.sleep(0.2)
        os.system('clear')
        print '################################################################################'
        print '#      接收列队负载：', connum
        serlist = list()
        listmutex.acquire()
        for model in modellist:
            serlist.append((model.name, model.qimpro.qsize()))
        listmutex.release()
        for ser in serlist:
            print '#      服务器', ser[0], '负载：', ser[1]


# sthread = threading.Thread(target=updateshow)
# sthread.setDaemon(True)
# sthread.start()


for i in range(100):
    sthread = threading.Thread(target=receivedata)
    sthread.setDaemon(True)
    sthread.start()


s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))
s.listen(1)
process_num = 0
while True:
    conn, addr = s.accept()
    Qcon.put((conn, process_num))
    process_num += 1






