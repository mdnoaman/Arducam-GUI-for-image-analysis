import sys
import os
import time
import cv2
import threading
import numpy as np
import arducam_config_parser
import ArducamSDK
from multiprocessing import Process, Pipe


class Camera_control():
    
    def __init__(self):
        self.running = True
        self.loading = True
        self.fileName = ''
        self.expconf = ''
        pass
    
    def config_exposure(self, expconf):
        file1 = open(expconf, 'r')
        lines = file1.readlines()
        file1.close()
        last_line = lines[-1]
        exp_val = int(last_line.split(',')[0])
#        line_pos = len(lines)
        return exp_val
        
    def configBoard(self, config):
        ArducamSDK.Py_ArduCam_setboardConfig(self.handle, config.params[0], \
            config.params[1], config.params[2], config.params[3], \
                config.params[4:config.params_length])

    def camera_initFromFile(self,mainconf, expconf):
        self.expconf = expconf
        self.fileName = mainconf
        config = arducam_config_parser.LoadConfigFile(self.fileName)
    
        camera_parameter = config.camera_param.getdict()
        self.Width = camera_parameter["WIDTH"]
        self.Height = camera_parameter["HEIGHT"]
    
        self.BitWidth = camera_parameter["BIT_WIDTH"]
        self.ByteLength = 1
        if self.BitWidth > 8 and self.BitWidth <= 16:
            self.ByteLength = 2
        self.FmtMode = camera_parameter["FORMAT"][0]
        self.color_mode = camera_parameter["FORMAT"][1]
#        print("color mode",self.color_mode)
    
        self.I2CMode = camera_parameter["I2C_MODE"]
        self.I2cAddr = camera_parameter["I2C_ADDR"]
        self.TransLvl = camera_parameter["TRANS_LVL"]
        self.cfg = {"u32CameraType":0x00,
                "u32Width":self.Width,"u32Height":self.Height,
                "usbType":0,
                "u8PixelBytes":self.ByteLength,
                "u16Vid":0,
                "u32Size":0,
                "u8PixelBits":self.BitWidth,
                "u32I2cAddr":self.I2cAddr,
                "emI2cMode":self.I2CMode,
                "emImageFmtMode":self.FmtMode,
                "u32TransLvl":self.TransLvl }
    
        ret,self.handle,self.rtn_cfg = ArducamSDK.Py_ArduCam_autoopen(self.cfg)
        if ret == 0:
           
            usb_version = self.rtn_cfg['usbType']
            configs = config.configs
            configs_length = config.configs_length
            for i in range(configs_length):
#                print(configs[i].params[0])
                type = configs[i].type
                if ((type >> 16) & 0xFF) != 0 and ((type >> 16) & 0xFF) != usb_version:
                    continue
                if type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_REG:
                    if configs[i].params[0] == 12306:
                        configs[i].params[1] = self.config_exposure(self.expconf)
                    ArducamSDK.Py_ArduCam_writeSensorReg(self.handle, configs[i].params[0], configs[i].params[1])
                elif type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_DELAY:
                    time.sleep(float(configs[i].params[0])/1000)
                elif type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_VRCMD:
                    self.configBoard(configs[i])
    
            rtn_val,datas = ArducamSDK.Py_ArduCam_readUserData(self.handle,0x400-16, 16)
            print("Serial: %c%c%c%c-%c%c%c%c-%c%c%c%c"%(datas[0],datas[1],datas[2],datas[3],
                                                        datas[4],datas[5],datas[6],datas[7],
                                                        datas[8],datas[9],datas[10],datas[11]))
    
            return True
        else:
            print("open fail,rtn_val = ",ret)
            return False
        
        
    
    def captureImage_thread(self):
        rtn_val = ArducamSDK.Py_ArduCam_beginCaptureImage(self.handle)
        if rtn_val != 0:
            print("Error beginning capture, rtn_val = ",rtn_val)
            self.running = False
            return
        else:
            print("Capture began, rtn_val = ",rtn_val)
        while self.running:
            if self.loading:
                rtn_val = ArducamSDK.Py_ArduCam_captureImage(self.handle)
                if rtn_val > 255:
#                    print("Error capture image, rtn_val = ",rtn_val)
                    if rtn_val == ArducamSDK.USB_CAMERA_USB_TASK_ERROR:
                        break
            else:
                print("restarting camera...")
#                time.sleep(1)
                ArducamSDK.Py_ArduCam_endCaptureImage(self.handle)
                self.camera_initFromFile(self.fileName, self.expconf)
                ArducamSDK.Py_ArduCam_beginCaptureImage(self.handle)
                self.loading = True
                
        self.running = False
        ArducamSDK.Py_ArduCam_endCaptureImage(self.handle)

    
    def dBytesToMat(self, data,BitWidth,Width,Height):
#        global image
        if BitWidth > 8:
            arr = np.frombuffer(data,dtype=np.uint16)
        else: 
            arr = np.frombuffer(data,dtype=np.uint8)
        image = arr.reshape(Height,Width)
        return image
    
    def readImage_thread(self, child_conn):
        count = 0
        time0 = time.time()
        time1 = time.time()
        data = {}
        while self.running:
            if ArducamSDK.Py_ArduCam_availableImage(self.handle) > 0:		
                rtn_val,data,rtn_cfg = ArducamSDK.Py_ArduCam_readImage(self.handle)
                datasize = rtn_cfg['u32Size']
                if rtn_val != 0 or datasize == 0:
                    self.ArducamSDK.Py_ArduCam_del(self.handle)
                    print("read data fail!")
                    continue
                image_data = self.dBytesToMat(data,self.BitWidth,self.Width,self.Height)
                child_conn.send(image_data)
    
                time1 = time.time()
                if time1 - time0 >= 1:
#                    print("%s %d %s\n"%("camera fps:",count,"/s"))
                    count = 0
                    time0 = time1
                count += 1
                ArducamSDK.Py_ArduCam_del(self.handle)
    #            time.sleep(.01)
            else:
                time.sleep(0.005)

        child_conn.close()
    
    
    def cameramain(self, config_file_name,expconf, child_conn):
        if self.camera_initFromFile(config_file_name, expconf):
            ArducamSDK.Py_ArduCam_setMode(self.handle,ArducamSDK.CONTINUOUS_MODE)
            ct = threading.Thread(target=self.captureImage_thread)
            rt = threading.Thread(target=self.readImage_thread, args=(child_conn,))
            ct.start()
            rt.start()
            while True:
                reload = child_conn.recv()
                print("reloading configuration file")
                if reload == False:
                    self.loading = False
                if reload == 'quit':
                    self.running = False
                    sys.exit()
                    break
                
            ct.join()
            rt.join()
            
            rtn_val = ArducamSDK.Py_ArduCam_close(self.handle)

            if rtn_val == 0:
                print("device close success!")
            else:
                print("device close fail!")
    
    
    def get_frame(self, parent_conn, state ):
        if state == 0:
            while True:
                frame = parent_conn.recv()
                print(frame[500,500])
 
        if state == 1:
            cv2.namedWindow('Camera feed', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('Camera feed', 640,480)
            while True:
                images = parent_conn.recv()
                img8 = np.uint8(images/16)
                cv2.imshow("Camera feed",img8)
        
                key = cv2.waitKeyEx(1)

                if key == ord('r'):
                    parent_conn.send(False)

                if key == ord('q'):
                    parent_conn.send('quit')
                    break
            cv2.destroyAllWindows()
            sys.exit()

#%%
   
if __name__ == '__main__':
    cam = Camera_control()
    mainconf ="AR0135_RAW_12b_1280x964_16fps_myconfig.cfg"
    expconf ="confg_exposure.txt"
    parent_conn, child_conn = Pipe()

    p1 = Process(target=cam.cameramain, args=(mainconf,expconf,child_conn,))
    p1.start()
    
    state = 1
    p2 = Process(target=cam.get_frame, args=(parent_conn, state,))
    p2.start()
    
    p1.join()
    p2.join()    
