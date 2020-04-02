from cam_vid import Camera_control
from multiprocessing import Process, Pipe
import cv2
import numpy as np
import sys
import time 

class MovieThread():
    def __init__(self):
        self.expconf = " "
        self.img_idx = 0
        pass
    
    def rebin(self,arr, new_shape):
        shape = (new_shape[0], arr.shape[0] // new_shape[0],
                 new_shape[1], arr.shape[1] // new_shape[1])
        return arr.reshape(shape).sum(-1).sum(1)
    
    def config_exposure(self, expconf):
        file1 = open(expconf, 'r')
        lines = file1.readlines()
        file1.close()
#        last_line = lines[-1]
#        exp_val = int(last_line.split(',')[0])
        line_pos = len(lines)
        return line_pos

    def get_frame(self, parent_conn, state, expconf):
        self.expconf = expconf
        if state ==0:
            while True:
                frame = parent_conn.recv()
    #                return self.value
    #                print(id(frame))
                print(frame[500,500])

        if state ==1:
            cv2.namedWindow('Camera feed', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('Camera feed',660,722) 

            print(" press the 4 arrow keys to move ROI box")
            print(" press '4' or '6' to decrease or increase the ROI box size")
            print(" press '5' to resete the ROI box size and its position")
            print(" press '1' to set the window size to smallest")
            print(" press '2' to set the window size to medium (default)")
            print(" press '3' to set the window size to biggest")
            print(" press 'z' to to pop up a zoomed window displaying ROI")
            print(" press 'r' to reload the config file")
            print(" press 'q' to quit")
            print(" press 's' to save the raw file")
            
            xlt, xrt, yup, ydn = [10, 10, 40, 200 ]

            picx = 482
            picy = 640

            ylst = picx + yup + ydn
            xlst = xlt + picy + xrt

            scl = 100
            x1 = 320+ xlt - scl
            y1 = 241+ yup - scl
            x2 = 320+ xlt + scl
            y2 = 241+ yup + scl

            xdat = xlt + np.arange(0,640,2)
            ydat = [1324]*len(xdat)
        
            count = 0
            time0 = time.time()
            time1 = time.time()
            zoomed = -1
            while True:
                images = parent_conn.recv()
                imgbin = self.rebin(images,(picx,picy))

                img8 = np.uint8(imgbin/64)
                img8 = cv2.flip(img8, 1)

                img8 = cv2.copyMakeBorder( img8, yup, ydn, xlt, xrt, cv2.BORDER_CONSTANT)
                cv2.rectangle(img8, (x1,y1), (x2,y2), (255,0,0), 1,cv2.LINE_AA) 

                mean_val = np.mean(imgbin[y1-yup:y2-yup , picy - x2+xlt: picy - x1+xlt])
                text_val = "Mean value in ROI {:.2f}".format(mean_val)
                cv2.putText(img8,text_val,(10,30), cv2.FONT_HERSHEY_SIMPLEX, 1,(255,255,255),2)

#
                ydat.append( int( ylst - np.mean(mean_val/82) ) )
                ydat.pop(0)
#
                cv2.line(img8, (xlt ,ylst ),      (xlst - xrt ,ylst ), (255, 255, 255), 1, cv2.LINE_AA)
                cv2.line(img8, (xlt ,ylst - 50 ), (xlst - xrt ,ylst -50), (255, 255, 255), 1, cv2.LINE_AA)
                cv2.line(img8, (xlt ,ylst - 100 ), (xlst - xrt ,ylst -100 ), (255, 255, 255), 1, cv2.LINE_AA)
                cv2.line(img8, (xlt ,ylst - 150 ), (xlst - xrt ,ylst -150), (255, 255, 255), 1, cv2.LINE_AA)
                
                points = np.array([xdat, np.array(ydat)])
                points = points.T
                cv2.polylines(img8, [points],0, (255,255,255), 2,cv2.LINE_AA)

                cv2.imshow("Camera feed",img8)
                
                time1 = time.time()
                if time1 - time0 >= 1:
#                    print("%s %d %s\n"%("display fps:",count,"/s"))
                    count = 0
                    time0 = time1
                count += 1
                
                key = cv2.waitKeyEx(1)                
                if key == ord('z'): # press q to quit
                    zoomed = -zoomed
                    if zoomed==1:
                        cv2.namedWindow('zoomed window', cv2.WINDOW_NORMAL)
                        cv2.resizeWindow('zoomed window',600,600) 
                    else:
                        cv2.destroyWindow('zoomed window')
                if zoomed == 1:
                    img8zoomed = cv2.flip(images, 1) 
                    img8zoomed = np.uint8(img8zoomed[2*(y1-yup):2*(y2-yup), 2*(x1-xlt):2*(x2-xlt)]/16)
#                    img8zoomed = cv2.flip(img8zoomed, 1)
                    cv2.imshow("zoomed window",img8zoomed)

                if key == ord('q'): # press q to quit
                    parent_conn.send('quit')
                    sys.exit()
                    break
                if key == ord('s'):
                    line_pos = self.config_exposure(self.expconf)
                    filestr = "images/image_" + str(line_pos) + "_"+ str(self.img_idx)+".raw"
                    self.img_idx = self.img_idx + 1
                    with open(filestr, 'wb') as f:
                        f.write(images)
                        print(filestr + " saved")
                if key == ord('r'): # reload the config file
                    self.img_idx = 0
                    parent_conn.send(False)

                if key == ord('1'): # make a smaller  window 
                    cv2.namedWindow('Camera feed', cv2.WINDOW_NORMAL)
                    cv2.resizeWindow('Camera feed', 400,438)
                if key == ord('2'): # reset to medium window 
                    cv2.namedWindow('Camera feed', cv2.WINDOW_NORMAL)
                    cv2.resizeWindow('Camera feed', 660,722)
                if key == ord('3'): # make a larger window
                    cv2.namedWindow('Camera feed', cv2.WINDOW_NORMAL)
                    cv2.resizeWindow('Camera feed', 858,939)
                    
                if key == ord('4'): # make the box smaller
                    if (x1 < x2-10) & (y1 < y2-10):
                        if scl > 5:
                            scl = scl - 5
                        x1,y1,x2,y2 = [x1+5, y1+5, x2-5, y2-5]
                if key == ord('5'): # reset the ROI box 
                    scl = 100
                    x1,y1,x2,y2 = [int(picy/2)+ xlt - scl, int(picx/2)+ yup - scl, int(picy/2)+ xlt + scl, int(picx/2)+ yup + scl ]
                if key == ord('6'): # make the box larger
#                    if (x1 > xlt) & (y1 > yup) & (y2 < xlt+picx) & (x2 < yup+picy):
                    if scl < min(picx/2, picy/2):
                        scl = scl + 5
                    x1,y1,x2,y2 = [x1-5, y1-5, x2+5, y2+5]
                    if (x1 < xlt) or (y1< yup) or (x2>xlt+picy) or(y2>yup+picx):
                        x1,y1,x2,y2 = [x1+5, y1+5, x2-5, y2-5]

                if key == 2621440: # arrow down key, move down
                    y1, y2 = [y1 + int(scl/4), y2 + int(scl/4)]
                    if y2 > yup+picx:
                        y1, y2 = [yup+picx - 2*scl, yup+picx]
                if key == 2490368: # arrow up key, move up
                    y1, y2= [y1 - int(scl/4), y2 - int(scl/4)]
                    if y1 < yup:
                        y1, y2 = [yup, yup+2*scl]
                if key == 2555904: # arrow right key, move right
                    x1, x2 =[ x1 + int(scl/4), x2 + int(scl/4)]
                    if x2 > xlt + picy:
                        x1, x2 = [xlt + picy - 2*scl, xlt + picy]
                if key == 2424832: # arrow left key, move left
                    x1, x2 = [x1 - int(scl/4), x2 - int(scl/4)]
                    if x1 < xlt:
                        x1, x2 = [xlt, xlt + 2*scl]
                                                                                
            cv2.destroyAllWindows()
            sys.exit()


if __name__ == '__main__':
    cam = Camera_control()
    filename ="AR0135_RAW_12b_1280x964_16fps_myconfig.cfg"
    expconf = "confg_exposure.txt"
    parent_conn, child_conn = Pipe()
    p1 = Process(target=cam.cameramain, args=(filename,expconf,child_conn,))
    p1.start()
    
    state = 1
    thrd = MovieThread()
    p2 = Process(target=thrd.get_frame, args=(parent_conn,state,expconf,))
    p2.start()

    p1.join()
    p2.join()
