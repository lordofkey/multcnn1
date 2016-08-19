# _*_coding:utf-8_*_
import socket
import threading
import struct
import cv2
import time
import Queue

QMAX = 500

class ModelPro:
    def __init__(self, conn):
        self.conn = conn
        self.initconnect(conn)
        self.qimpro = Queue.Queue()
        self.flag = 1
        sthread = threading.Thread(target=self.imgpro)
        sthread.setDaemon(True)
        sthread.start()
    def initconnect(self, conn):
        data = conn.recv(4)
        num = struct.unpack('i', data)[0]  # 字符字节数
        data = conn.recv(num)
        self.name = struct.unpack(str(num) + 's', data)[0]
        data = conn.recv(12)
        self.width, self.height, self.chanel = struct.unpack('3i', data)

    def imgpro(self):
        self.conn.sendall("connect secceed")
        while True:
            try:
                tmp = self.qimpro.get()
                img_in = tmp[0]
                img_in = cv2.resize(img_in, (self.width, self.height))
                self.conn.sendall(img_in.data.__str__())
            except:
                break
        self.conn.close()
        self.flag = 0
        return


class ModelManage:
    def __init__(self, host='0.0.0.0', port=9231):
        self.host = host
        self.port = port
        self.listmutex = threading.Lock()
        self.modellist = list()
        sthread = threading.Thread(target=self.cnn_add)
        sthread.setDaemon(True)
        sthread.start()
        sthread = threading.Thread(target=self.cnn_destroy)
        sthread.setDaemon(True)
        sthread.start()

    def cnn_add(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(1)
        while True:
            conn, addr = s.accept()
            try:
                self.modellist.append(ModelPro(conn))
            except:
                continue

    def cnn_destroy(self):
        while True:
            time.sleep(1)
            self.listmutex.acquire()
            for model in self.modellist:
                if model.flag == 0:
                    self.modellist.remove(model)
                    break
            self.listmutex.release()

    def put(self, model_name, img, process_num):
        self.listmutex.acquire()
        for model in self.modellist:
            if model.name[:4] == model_name[:4]:
                if model.qimpro.qsize() < QMAX:
                    model.qimpro.put((img, process_num))
                    self.listmutex.release()
                    return True
        self.listmutex.release()
        return False


