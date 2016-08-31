#coding:utf-8
import socket
import cv2
import numpy as np
import xml.dom.minidom
import datetime
import sys
import struct
import commands
import os


workdir = os.getcwd()
innerhost = "172.1.10.134"
innerport = 9233

SAVE_IMG = 1

width = 227
height = 227
channel = 3

class CycCheck(Exception):
    def __init__(self):
        Exception.__init__(self)


class models(object):
    def __init__(self, num = 0):
        self.name = ''
        self.type = ''
        self.labels = []
        self.tf_param = []  #pred, x, keep_prob
        self.initmodel(num)
        self.initlabel()
    def initmodel(self, num):
        global width, height, channel
        dom = xml.dom.minidom.parse('config.xml')
        root = dom.documentElement
        m_mdlnum = root.getElementsByTagName('modelnum')
        itemlist = root.getElementsByTagName('model')
        model_content = itemlist[num]
        self.name = str(model_content.getAttribute("name"))
        self.type = str(model_content.getAttribute("type"))
        self.model_path = str(model_content.getAttribute("path"))
        if self.type == 'caffe':
            import caffe
            caffe.set_mode_gpu()
            proto_data = open(self.model_path + 'mean.binaryproto', 'rb').read()
            temp_a = caffe.io.caffe_pb2.BlobProto.FromString(proto_data)
            img_mean = caffe.io.blobproto_to_array(temp_a)[0]
            self.net = caffe.Net(self.model_path + 'deploy.prototxt', self.model_path + 'model.caffemodel', caffe.TEST)
            tm1, channel, width, height = self.net.blobs['data'].data.shape
 
            img_mean = np.transpose(img_mean, [1, 2, 0])
            img_mean = cv2.resize(img_mean, (width, height))
            self.mean = np.transpose(img_mean, [2, 0, 1])                  
            print 'caffe done!'
        elif self.type == 'tensorflow':
            import tensorflow as tf
            ckpt = tf.train.get_checkpoint_state(self.model_path)
            saver = tf.train.import_meta_graph(ckpt.model_checkpoint_path + '.meta')
            self.pred = tf.get_collection("pred")[0]
            self.x = tf.get_collection("x")[0]
            self.keep_prob = tf.get_collection("keep_prob")[0]
            gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction = 0.1)
            self.sess = tf.Session(config = tf.ConfigProto(gpu_options = gpu_options))
            saver.restore(self.sess, ckpt.model_checkpoint_path)
            print 'tf done!'
        else:
            print 'can not recognized the frame!'
    def initlabel(self):
        f = open(self.model_path + 'labels.txt', 'r')
        while True:
            line = f.readline()
            line = line.strip('\n')
            # if SAVE_IMG:
                # commands.getstatusoutput('mkdir -p pic/' + model.name + '/' + m_date + '/' + line)
            if line:
                self.labels.append(line)
            else:
                break
        f.close()


def receiveimg(s, imglen):
    data = ''
    recv_size = 0
    while recv_size < imglen:
        if imglen - recv_size > 10240:
            temp_recv = s.recv(10240)
            data += temp_recv
        else:
            temp_recv = s.recv(imglen - recv_size)
            data += temp_recv
        recv_size = len(data)
        if recv_size == 14:
            if data == 'are you there?':
                s.sendall('yes')
                raise CycCheck
    return data


class FpsCheck(object):
    def __init__(self, tickt=10):
        self.stime = datetime.datetime.now()
        self.pronum = 0
        self.tick = tickt

    def process(self):
        self.pronum += 1
        if self.pronum >= self.tick:
            fps = (self.tick)/((datetime.datetime.now() - self.stime).total_seconds())
            self.pronum = 0
            self.stime = datetime.datetime.now()
            print 'fps:', fps

m_date = str(datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S"))
mn = int(sys.argv[1])

print mn
m_model = models(mn)
imglen = width * height

ca_num = 0
picFolder = ''

s = socket.socket()
s.connect((innerhost, innerport))
name = m_model.name
name_len = len(name)
data = struct.pack('=i'+str(name_len)+'s3i', name_len, name, width, height, channel)
s.sendall(data)
data = s.recv(20)
if data == 'connect secceed':
    print 'secceed'

fps = FpsCheck()
while True:
    try:
        data = receiveimg(s, imglen)
    except CycCheck:
        continue
    except:
        break
    img = np.fromstring(data, dtype=np.uint8)
    img = img.reshape(height, width)
    m_rlt = ''
    if m_model.type == 'caffe':
        img_in = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        img_in = np.transpose(img_in, [2, 0, 1])
        img_in = img_in.astype(np.float32)
        img_in -= m_model.mean
        m_model.net.blobs['data'].data[...] = [img_in]
        output = m_model.net.forward()
        predictions = output['prob']
    if m_model.type == 'tensorflow':
        img_in = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        img_in = img_in.astype(np.float32)
        img_in /= 255
        predictions = m_model.sess.run(m_model.pred, feed_dict={m_model.x: [img_in], m_model.keep_prob: 1.})
    m_rlt = m_model.labels[np.argmax(predictions)]
    fps.process()
    if(0 == ca_num % 2000):
        picFolder = str(ca_num)
    filename = workdir + '/pic/' + m_model.name + '/' + m_date + '/' + m_rlt + '/' + picFolder + '/' + str(ca_num) + '.jpg'
    if SAVE_IMG:
        commands.getstatusoutput('mkdir -p pic/' + m_model.name + '/' + m_date + '/' + m_rlt + '/' + picFolder)
        cv2.imwrite(filename, img)
    len_m_rlt = len(m_rlt)
    len_filename = len(filename)
    data = struct.pack('=2i' + str(len_m_rlt) + 's' + str(len_filename) + 's', len_m_rlt, len_filename, m_rlt, filename)
    s.send(data)
    ca_num += 1
s.close()
