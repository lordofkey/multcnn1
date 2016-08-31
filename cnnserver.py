# _*_coding:utf-8_*_
import socket
import numpy as np
import cv2
import struct
import Queue
import threading
import os
import time
import dpmanager
import logging
import pymongo



logger = logging.getLogger('TOEClogger')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('cnnserver.log')
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
#logger.addHandler(ch)

dbclient = pymongo.MongoClient(host="172.1.10.134")
Qcon = Queue.Queue(200)
HOST = '0.0.0.0'
PORT = 8145
inner_host = '0.0.0.0'
inner_port = 9233
PARAM_LEN = 128
SAVE_IMG = 1
httphost = '0.0.0.0'
httpport = 10102



try:
    mmanager = dpmanager.ModelManage(inner_host, inner_port)
except:
    logger.exception("Exception Logged")
#接收线程
def receivedata():
    while True:
        try:
            conn = Qcon.get()
            m_rlt = 'failed'
            adrr = 'lost'
            proQ = Queue.Queue()
            token = struct.unpack('10s', conn.recv(10))[0]
            if token == "1234567890":
                buf = struct.pack('i', 1)
                conn.send(buf)
            else:
                buf = struct.pack('i', 0)
                conn.send(buf)
                conn.close()
                return
            lens = struct.unpack('2i', conn.recv(8))
            param = struct.unpack(str(lens[0]) + 's', conn.recv(lens[0]))[0]
            file_size = lens[1]
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
            data = np.fromstring(data, np.uint8)
            img = cv2.imdecode(data, 0)
            mmanager.put(param, img, proQ)
            returnmsg = proQ.get(block=True, timeout=5)
            m_rlt = returnmsg[0]
            adrr = returnmsg[1]
        except dpmanager.NoModelResource:
            pass
        except:
            logger.exception("dumped during receiving")
        finally:
            try:
                dbclient.deepldb.test.save({'imgadr': adrr, 'result': m_rlt, 'sername': param})
            except:
                logger.exception("db Exception")
            try:
                conn.send(m_rlt)
                conn.close()
            except:
                logger.exception("client connect exception")

        ##################################################################################


def updateshow():
    sh = socket.socket()
    sh.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sh.bind((httphost, httpport))
    sh.listen(1)
    while True:
        try:
            conn, addr = sh.accept()
            connum = Qcon.qsize()
            serlist = mmanager.checkload()
            shownum = 1 + serlist.__len__()
            data = struct.pack('i', shownum)
            data += struct.pack('=i'+str(len("receivelist"))+'si', len("receivelist"), "receivelist", connum)
            for ser in serlist:
                data += struct.pack('=i'+str(len(ser[0]))+'si', len(ser[0]), ser[0], ser[1])
            conn.sendall(data)
            conn.close()
        except:
            logger.exception("httpserver error")
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
    logger.exception("thread starting Exception Logged")

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))
s.listen(20)
while True:
    try:
        conn, addr = s.accept()
        Qcon.put(conn)
    except:
        logger.exception("socket acception Exception Logged")
        continue

