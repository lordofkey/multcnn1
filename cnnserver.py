#coding:utf-8
import socket
import cv2
import numpy as np
import struct
import xml.dom.minidom
import caffe
import commands
import datetime
import Queue
import threading
import os
import time

Qcon = Queue.Queue(30)
listmutex = threading.Lock()


innerhost = '0.0.0.0'
innerport = 9231

addr = ''


def imgpro(conn, model):
    conn.sendall("connect secceed")
    while True:
        try:
            tmp = model.qimpro.get()
            img_in = tmp[0]
            img_in = cv2.resize(img_in, (model.width, model.height))
            conn.sendall(img_in.data.__str__())
        except:
            conn.close()
            listmutex.acquire()
            modellist.remove(model)
            listmutex.release()
            time.sleep(1)
            del model
            return

class modelpro():
    def __init__(self,conn):
        self.initconnect(conn)
        self.qimpro = Queue.Queue()
        sthread = threading.Thread(target=imgpro, args=(conn, self))
        sthread.setDaemon(True)
        sthread.start()
        self.flag = 1
    def initconnect(self,conn):
        data = conn.recv(4)
        num = struct.unpack('i',data)[0]  #字符字节数
        data = conn.recv(num)
        self.name = struct.unpack(str(num) + 's', data)[0]
        data = conn.recv(12)
        self.width, self.height, self.chanel = struct.unpack('3i',data)


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
            width = struct.unpack('L', conn.recv(8))[0]
            height = struct.unpack('L', conn.recv(8))[0]
            file_size = width * height
            recv_size = 0
            data = ''
        except:
            continue
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
        img = np.fromstring(data,dtype=np.uint8)
        img = img.reshape(height,width)

        listmutex.acquire()
        for model in modellist:
            if(model.name[:4] == param[:4]):
                model.qimpro.put((img, process_num))
                break
        listmutex.release()
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
        print '#        客户机地址：', addr


HOST = '0.0.0.0'
PORT = 8145
PARAM_LEN = 128

SAVE_IMG = 1
picFolder = ''
modellist = list()

m_date = str(datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S"))

def cnnadd():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((innerhost,innerport))
    s.listen(1)
    while True:
        conn,addr = s.accept()
        try:
            tmp = modelpro(conn)
            modellist.append(tmp)
        except:
            continue



sthread = threading.Thread(target=cnnadd)
sthread.setDaemon(True)
sthread.start()

#sthread = threading.Thread(target=updateshow)
#sthread.setDaemon(True)
#sthread.start()


for i in range(10):
    sthread = threading.Thread(target=receivedata)
    sthread.setDaemon(True)
    sthread.start()


s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))
s.listen(1)
model_index = 0
process_num = 0
while True:
    conn, addr = s.accept()
    Qcon.put((conn, process_num))
    process_num += 1






