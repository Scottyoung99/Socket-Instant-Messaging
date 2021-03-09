import os,io,socket,json,cv2,threading,time
import numpy as np 
import tkinter as tk 
import tkinter.scrolledtext as tst
import tkinter.messagebox
import tkinter.filedialog
import zlib,struct,pickle,pyaudio


class Application(tk.Frame):

    def __init__(self, master,sessionManage):  
        tk.Frame.__init__(self, master)
        self.root = master
        self.createWidgets()
        self.sessionManage = sessionManage
        self.clientReceiveThread = ClientReceiveThread(self.sessionManage.message_conn,self)
        self.clientReceiveThread.start()

    def createWidgets(self):
        self.chatRecord = tst.ScrolledText(self.root, width=80, height=20)
        self.chatRecord.place(x=1,y=30)

        self.sendBtn = tk.Button(root,text="发送文件",width=8,command=self.sendFile)
        self.sendBtn.place(x=400,y=300)

        self.sendBtn = tk.Button(root,text="视频聊天",width=8,command = self.videoChatApply)
        self.sendBtn.place(x=500 ,y=300)

        self.chatMessage = tst.ScrolledText(self.root, width=80, height=10)
        self.chatMessage.place(x=1,y=340)

        self.sendBtn = tk.Button(root,text="发送",width=8,command=self.sendMessage)
        self.sendBtn.place(x=500,y=480)

        
    def sendMessage(self): 
        content = self.chatMessage.get(1.0, tk.END).strip()  
        if  content =="":
            return
        self.sessionManage.message_conn.send(json.dumps({
                        'type': 'Message',
                        'content': content,
                    }).encode("utf-8") )
        self.chatMessage.delete(1.0,tk.END)
        Message = "我:\n"+content+"\n\n"
        self.chatRecord.insert("insert", Message)
        self.chatRecord.see(tk.END)

    def sendFile(self):   
        filePath = tk.filedialog.askopenfilename(filetypes=[('文本文件','.txt'),('所有文件','.*')])
        Message = "我:\n 发送文件"+filePath+"\n\n"
        self.chatRecord.insert("insert", Message)
        self.chatRecord.see(tk.END)
        jsDict = {'type': 'FileTransfer'}
        js = json.dumps(jsDict)
        self.sessionManage.message_conn.sendall( bytes(js,'utf-8'))
        threading.Thread(target=self.sendFileThread,args=(filePath,)).start()
            
    def sendFileThread(self,filePath):
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
    

    def __init__(self,sessionManage):  
        self.ip_port = "LAPTOP-LUEGMEJJ"
        self.local_ip = "LAPTOP-JGMJSJHI"
        self.video_port = (self.local_ip, 8002)
        self.videoReceive_port = (self.ip_port,8002)
        self.audio_port = (self.local_ip, 8003)
        self.audioReceive_port = (self.ip_port,8004)

        self.interval = 1
        self.fx = 0.5
        self.video_conn = sessionManage.video_conn
        self.videoReceive_conn = sessionManage.videoReceive_conn
        self.audio_conn = sessionManage.audio_conn
        self.audioReceive_conn = sessionManage.audioReceive_conn
        self.camera = cv2.VideoCapture(0)   
        self.p=pyaudio.PyAudio()
        self.p1=pyaudio.PyAudio()
        self.stream=None
        self.stream1=None
        threading.Thread(target=self.sendVideo,args=(self.video_conn,)).start()
        threading.Thread(target=self.sendAudio,args=(self.audio_conn,)).start()
        threading.Thread(target=self.receiveVideo,args=(self.videoReceive_conn,)).start()
        threading.Thread(target=self.receiveAudio,args=(self.audioReceive_conn,)).start()

       

    def s_destroy(self):
        self.camera.release()
        cv2.destroyAllWindows()
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()


    def receiveAudio(self,audio_conn):
        print("Audio client starts...\n")
        while True:
            try:
                audio_conn.bind(self.audio_port)
                audio_conn.listen(10)
                conn,addr = audio_conn.accept()
                break
            except:
                time.sleep(3)
                continue
        print("Audio client connected...\n")


        data="".encode("utf-8")
        payload_size=struct.calcsize("L")
        self.stream=self.p.open(format=FORMAT,
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
                self.stream.write(frame,CHUNK)

    def sendAudio(self,audio_conn):
        audio_conn.connect(self.audioReceive_port)
        self.stream1=self.p1.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                input=True,
                                frames_per_buffer=CHUNK
                                )
        while self.stream1.is_active():
            frames=[]
            for i in range(0,int(RATE/CHUNK*RECORD_SECONDS)):
                data=self.stream1.read(CHUNK)
                frames.append(data)
            senddate=pickle.dumps(frames)
            try:
                audio_conn.sendall(struct.pack("L",len(senddate))+senddate)
            except:
                break


    def receiveVideo(self,video_conn):
        print("VIDEO client starts...\n")
        while True:
            try:
                video_conn.bind(self.video_port)
                video_conn.listen(10)
                conn,addr = video_conn.accept()
                break
            except:
                time.sleep(3)
                continue
        print("VEDIO client connected...\n")
        
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
        video_conn.connect(self.videoReceive_port)
        print("remote VIDEO client successfully connected...\n")
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


    def __init__(self):
        self.video_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.videoReceive_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.audio_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.audioReceive_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.Mainsock1 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.Mainsock2 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        ip_port = "LAPTOP-LUEGMEJJ"
        local_ip = "LAPTOP-JGMJSJHI"
        self.message_port = (local_ip, 8000)
        self.file_port = (local_ip, 8001)

        self.Mainsock1.bind(self.message_port)
        self.Mainsock1.listen(10)
        self.message_conn,addr=self.Mainsock1.accept()

        print("Running1")

        self.Mainsock2.bind(self.file_port)
        self.Mainsock2.listen(10)
        self.file_conn,addr=self.Mainsock2.accept()

        print("Running2")

        print("成功连接\n")
        

    def sendFile(self,filePath):

        size = os.stat(filePath).st_size 
        fileName = os.path.basename(filePath)
        fileInfo = fileName +"|"+str(size)
        self.file_conn.send(fileInfo.encode("utf-8")) 
        
        self.file_conn.recv(1024) 

        f = open(filePath, "rb")
        have_sent = 0
        while have_sent!= size :
            data = f.read(1024)
            self.file_conn.sendall(data)  
            have_sent+=len(data)

        f.close()

    def receiveFile(self):
        server_response = self.file_conn.recv(1024)
        fileInfo = server_response.decode("utf-8").split("|")
        filename = fileInfo[0]
        file_size = (int)(fileInfo[1])

        self.file_conn.send("ready".encode("utf-8"))  
        filePath = "D:\\Python\\"+ filename
        f = open(filePath, "wb")
        received_size = 0

        while received_size < file_size:
            size = 0  
            if file_size - received_size > 1024: 
                    size = 1024
            else:  
                    size = file_size - received_size

            data = self.file_conn.recv(size)  
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
            message = "对方打开视频通讯:\n"
            self.application.chatRecord.insert("insert",message)
            self.application.videoChat()


        self.application.chatRecord.see(tk.END)
           

if __name__ == "__main__":
    root = tk.Tk()                 
    root.title('Socket即时通讯')    
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    ww = 600
    wh = 510
    x = (sw-ww) / 2
    y = (sh-wh) / 2
    root.geometry("%dx%d+%d+%d" %(ww,wh,x,y))

    sessionManage = SessionManage()
    app = Application(root,sessionManage)  
    app.mainloop()                

