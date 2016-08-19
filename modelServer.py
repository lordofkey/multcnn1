#coding:utf-8
import socket
import cv2
import numpy as np
import xml.dom.minidom
import datetime
import os,sys
import struct
import commands



innerhost = "172.1.10.134"
innerport = 9231

SAVE_IMG = 0
picFolder = '0'


class models(object):
    def __init__(self, num = 0):
        self.name = ''
        self.type = ''
        self.labels = []
        self.tf_param = []  #pred, x, keep_prob
        self.initmodel(num)
        self.initlabel()
    def initmodel(self, num):
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
            self.mean = caffe.io.blobproto_to_array(temp_a)[0]
            self.net = caffe.Net(self.model_path + 'deploy.prototxt', self.model_path + 'model.caffemodel', caffe.TEST)
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




m_date = str(datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S"))
mn = int(sys.argv[1])
#mn = int(0)
print mn
m_model = models(mn)
width = 227
height = 227
imglen = width * height

ca_num = 0

s = socket.socket()
s.connect((innerhost,innerport))
name = m_model.name
name_len = len(name)
data = struct.pack('=i'+str(name_len)+'s3i', name_len, name, width, height, 3)
s.sendall(data)
print "send all"
data = s.recv(20)
if(data == 'connect secceed'):
    print 'secceed'


pronum = 0
stime = datetime.datetime.now()
while True:
    pronum += 1
    if pronum >= 10:
        pronum = 0
        fps = 9/((datetime.datetime.now() - stime).total_seconds())
        stime = datetime.datetime.now()
        print 'fps:', fps
    recv_size = 0
    im = []
    while recv_size < imglen:
        if imglen - recv_size > 10240:
            temp_recv = s.recv(10240)
            data = list(struct.unpack(str(len(temp_recv)) + 'B', temp_recv))
            im.extend(data)
        else:
            temp_recv = s.recv(imglen - recv_size)
            data = list(struct.unpack(str(len(temp_recv)) + 'B', temp_recv))
            im.extend(data)
        recv_size += len(data)
    img = np.array(im, np.uint8)
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
        ca_num += 1
    if m_model.type == 'tensorflow':
        img_in = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        img_in = img_in.astype(np.float32)
        img_in /= 255
        predictions = m_model.sess.run(m_model.pred, feed_dict={m_model.x: [img_in], m_model.keep_prob: 1.})
    m_rlt = m_model.labels[np.argmax(predictions)]

    if(0 == ca_num % 2000):
        picFolder = str(ca_num)
    if SAVE_IMG:
        commands.getstatusoutput('mkdir -p pic/' + m_model.name + '/' + m_date + '/' + m_rlt + '/' + picFolder)
        cv2.imwrite('pic/' + m_model.name + '/' + m_date + '/' + m_rlt + '/' + picFolder + '/' + str(ca_num) + '.jpg', img)
s.close()
