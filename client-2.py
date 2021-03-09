import os,io,socket,json,cv2,threading,time
import numpy as np 
import tkinter as tk 
import tkinter.scrolledtext as tst
import tkinter.messagebox
import tkinter.filedialog
import zlib,struct,pickle,pyaudio


class Application(tk.Frame):
    #定义GUI应用程序类，派生于Frame类

    def __init__(self, master,sessionManage):  #构造函数，master为父窗口
        tk.Frame.__init__(self, master)#调用父类的构造函数
        self.root = master
        self.createWidgets()
        self.sessionManage = sessionManage
        self.clientReceiveThread = ClientReceiveThread(self.sessionManage.message_conn,self)
        self.clientReceiveThread.start()

    def createWidgets(self):
        self.chatRecord = tst.ScrolledText(self.root, width=80, height=20)#创建Text组件
        self.chatRecord.place(x=1,y=30)

        self.sendBtn = tk.Button(root,text="发送文件",width=8,command=self.sendFile)
        self.sendBtn.place(x=400,y=300)

        self.sendBtn = tk.Button(root,text="视频聊天",width=8,command = self.videoChatApply)
        self.sendBtn.place(x=500 ,y=300)

        self.chatMessage = tst.ScrolledText(self.root, width=80, height=10)#创建Text组件
        self.chatMessage.place(x=1,y=340)

        self.sendBtn = tk.Button(root,text="发送",width=8,command=self.sendMessage)
        self.sendBtn.place(x=500,y=480)

        
    def sendMessage(self): #发送消息
        content = self.chatMessage.get(1.0, tk.END).strip()  
        if  content =="":
            return
        self.sessionManage.message_conn.send(json.dumps({
                        'type': 'Message',
                        'content': content,
                    }).encode("utf-8") )#
        self.chatMessage.delete(1.0,tk.END)
        Message = "我:\n"+content+"\n\n"
        self.chatRecord.insert("insert", Message)
        self.chatRecord.see(tk.END)

    def sendFile(self):     #发送文件
        filePath = tk.filedialog.askopenfilename(filetypes=[('文本文件','.txt'),('所有文件','.*')])
        Message = "我:\n 发送文件"+filePath+"\n\n"
        self.chatRecord.insert("insert", Message)
        self.chatRecord.see(tk.END)
        jsDict = {'type': 'FileTransfer'}
        js = json.dumps(jsDict)
        self.sessionManage.message_conn.sendall( bytes(js,'utf-8'))
        threading.Thread(target=self.sendFileThread,args=(filePath,)).start()
            
    def sendFileThread(self,filePath): #文件发送的线程
        sendResult = self.sessionManage.sendFile(filePath)
    
    def receiveFile(self):
        threading.Thread(target=self.receiveFileThread,args=()).start()

    def receiveFileThread(self):
        filePath = self.sessionManage.receiveFile()
        fileName = os.path.basename(filePath)
        Message = "通知:\n 已成功接受文件"+fileName+"，存放在D:\Python\n\n"
        self.chatRecord.insert("insert", Message)
        self.chatRecord.see(tk.END)

    def videoChatApply(self):
        Message = "我:\n 发送视频通话请求\n\n"
        self.chatRecord.insert("insert", Message)
        self.chatRecord.see(tk.END)
        jsDict = {'type': 'videoChat'}
        js = json.dumps(jsDict)
        self.sessionManage.message_conn.sendall( bytes(js,'utf-8'))
        self.videoChat()

    def videoChat(self):
        videoFrame(self.sessionManage)


CHUNK=882
FORMAT=pyaudio.paInt16
CHANNELS=1
RATE=16000
RECORD_SECONDS = 1

class videoFrame():
    #定义GUI应用程序类，派生于Frame类
    local_ip = "LAPTOP-LUEGMEJJ"
    ip_port = "LAPTOP-JGMJSJHI"

    video_port = (ip_port, 8002)
    videoReceive_port = (local_ip,8002)
    audio_port = (ip_port, 8003)
    audioReceive_port = (local_ip,8004)
    def __init__(self,sessionManage):  #构造函数，master为父窗口

        self.interval = 1
        self.fx = 0.5
        self.video_conn = sessionManage.video_conn
        self.videoReceive_conn = sessionManage.videoReceive_conn
        self.audio_conn = sessionManage.audio_conn
        self.audioReceive_conn = sessionManage.audioReceive_conn
        self.camera = cv2.VideoCapture(0)    #摄像头
        self.p1=pyaudio.PyAudio()
        self.p2=pyaudio.PyAudio()
        self.stream1=None
        self.stream2=None
        threading.Thread(target=self.sendVideo,args=(self.video_conn,)).start()
        threading.Thread(target=self.sendAudio,args=(self.audio_conn,)).start()
        threading.Thread(target=self.receiveVideo,args=(self.videoReceive_conn,)).start()
        threading.Thread(target=self.receiveAudio,args=(self.audioReceive_conn,)).start()

       

    def s_destroy(self):
        self.camera.release()
        cv2.destroyAllWindows()
        if self.stream1 is not None:
            self.stream1.stop_stream()
            self.stream1.close()
        if self.stream2 is not None:
            self.stream2.stop_stream()
            self.stream2.close()
        self.p1.terminate()
        self.p2.terminate()


    def receiveAudio(self,audio_conn):
        audio_conn.bind(self.audioReceive_port)
        audio_conn.listen(10)
        conn,addr=audio_conn.accept()
        print("remote AUDIO client successfully connected...\n")

        data="".encode("utf-8")
        payload_size=struct.calcsize("L")
        self.stream1=self.p1.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            output=True,
                            frames_per_buffer=CHUNK
                            )
        while True:
            while len(data)<payload_size:
                data+=conn.recv(81920)
            packed_size=data[:payload_size]
            data=data[payload_size:]
            msg_size=struct.unpack("L",packed_size)[0]
            while len(data)<msg_size:
                data+=conn.recv(81920)
            frame_data=data[:msg_size]
            data=data[msg_size:]
            frames=pickle.loads(frame_data)
            for frame in frames:
                self.stream1.write(frame,CHUNK)

    def sendAudio(self,audio_conn):
        print("AUDIO client starts...\n")
        while True:
            try:
                audio_conn.connect(self.audio_port)
                break
            except:
                time.sleep(3)
                continue
        print("AUDIO client connected...\n")

        self.stream2=self.p2.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                input=True,
                                frames_per_buffer=CHUNK
                                )

        while self.stream2.is_active():
            frames=[]
            for i in range(0,int(RATE/CHUNK*RECORD_SECONDS)):
                data=self.stream2.read(CHUNK)
                frames.append(data)
            senddate=pickle.dumps(frames)
            try:
                audio_conn.sendall(struct.pack("L",len(senddate))+senddate)
            except:
                break


    def receiveVideo(self,video_conn):
        video_conn.bind(self.videoReceive_port)
        video_conn.listen(10)
        conn,addr=video_conn.accept()
        print("remote VIDEO client successfully connected...\n")

        data = "".encode("utf-8")
        payload_size = struct.calcsize("L")
        cv2.namedWindow('Remote', cv2.WINDOW_NORMAL)
        while True:
            while len(data) < payload_size:
                data += conn.recv(81920)
            packed_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("L", packed_size)[0]
            while len(data) < msg_size:
                data += conn.recv(81920)
            zframe_data = data[:msg_size]
            data = data[msg_size:]
            frame_data = zlib.decompress(zframe_data)
            frame = pickle.loads(frame_data)
            cv2.imshow('Remote', frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break


    def sendVideo(self,video_conn):
        print("VIDEO client starts...\n")
        while True:
            try:
                video_conn.connect(self.video_port)
                break
            except:
                time.sleep(3)
                continue
        print("VEDIO client connected...\n")

        while self.camera.isOpened():
            ret, frame = self.camera.read()
            sframe = cv2.resize(frame, (0,0), fx=self.fx, fy=self.fx)
            data = pickle.dumps(sframe)
            zdata = zlib.compress(data, zlib.Z_BEST_COMPRESSION)
            try:
                video_conn.sendall(struct.pack("L", len(zdata)) + zdata)
            except:
                break
            for i in range(self.interval):
                self.camera.read()




class SessionManage:
    message_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    file_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    video_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    videoReceive_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    audio_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    audioReceive_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    Mainsock1 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    Mainsock2 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    def __init__(self):
        local_ip = "LAPTOP-LUEGMEJJ"
        ip_port = "LAPTOP-JGMJSJHI"
        message_port = (ip_port, 8000)
        file_port = (ip_port, 8001)

        self.message_conn.connect(message_port)
        self.file_conn.connect(file_port)

        print("成功连接\n")
        

    def sendFile(self,filePath):

        size = os.stat(filePath).st_size  #获取文件大小
        fileName = os.path.basename(filePath)
        fileInfo = fileName +"|"+str(size)
        self.file_conn.send(fileInfo.encode("utf-8")) 
        
        # 2.发送文件内容
        self.file_conn.recv(1024)  # 接收确认
       
        f = open(filePath, "rb")
        have_sent = 0
        while have_sent!= size :
            data = f.read(1024)
            self.file_conn.sendall(data)  # 发送数据
            have_sent+=len(data)

        f.close()

    def receiveFile(self):
        server_response = self.file_conn.recv(1024)
        fileInfo = server_response.decode("utf-8").split("|")
        filename = fileInfo[0]
        file_size = (int)(fileInfo[1])

        # 2.接收文件内容
        self.file_conn.send("ready".encode("utf-8"))  # 回复就绪信号
        filePath = "D:\\Python\\"+ filename
        f = open(filePath, "wb")
        received_size = 0

        while received_size < file_size:
            size = 0  
            if file_size - received_size > 1024: # 每次只接收 1024
                    size = 1024
            else:  # 最后一次接收
                    size = file_size - received_size

            data = self.file_conn.recv(size)  #多次接收内容
            data_len = len(data)
            received_size += data_len
            f.write(data)

        f.close()
        return filename
        


class ClientReceiveThread(threading.Thread):
    def __init__(self,message_conn,application):
        super(ClientReceiveThread, self).__init__()
        self.message_conn = message_conn
        self.application = application
    def run(self):
        self.receive_msg()
    def receive_msg(self):
        while True:
            msg = self.message_conn.recv(1024).decode('utf-8')
            if not msg:
                break
            js = json.loads(msg)
            self.msgHandle(js)
    def msgHandle(self,js):
        if js["type"] == "Message":
            Message = "对方:\n"+js["content"]+"\n\n"
            self.application.chatRecord.insert("insert", Message)

        if js["type"] == "FileTransfer":
            self.application.receiveFile()

        if js["type"] == "videoChat":
            message = "对方打开视频通话:\n"
            self.application.chatRecord.insert("insert",message)
            self.application.videoChat()
        self.application.chatRecord.see(tk.END)
           

if __name__ == "__main__":
    root = tk.Tk()                 #创建1个Tk根窗口组件root
    root.title('Socket即时通信')     #设置窗口标题
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    ww = 600
    wh = 510
    x = (sw-ww) / 2
    y = (sh-wh) / 2
    root.geometry("%dx%d+%d+%d" %(ww,wh,x,y))

    sessionManage = SessionManage()
    app = Application(root,sessionManage)   #创建Application的对象实例
    app.mainloop()                #调用组件的mainloop方法，进入事件循环

