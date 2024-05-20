import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

import threading
import cv2
import numpy as np
import time
import datetime
import requests
import serial

# ====(パラメータ設定：ここから)====

isRecordedAsVideo = True   # ビデオとして記録するかどうかのフラグ：Trueの場合にはビデオ(avi)として記録、Falseの場合には画像(jpg)として記録する。
diff_rate_threshold = 0    # 差分率の閾値：0の場合には常時録画、1の場合には超音波距離センサに近接した時に録画開始、0から1の間は差分率が閾値を超えた場合に録画開始。
diff_level_threshold = 30  # 差分レベルの閾値：差分レベルが閾値を超えた場合に差分レベルが閾値を下回ったら録画を開始する。
rec_fps = 30                # 記録するフレームレート
rec_time = 10 #1分の場合は60 # 記録時間（秒）
cameras = [0] #['http://192.168.115.57:81/stream'] #, 'http://192.168.115.110:81/stream']              # カメラの指定：カメラが2台の時は[0,1]、一方がネットワークカメラ（ESP32_S3_WROOM）の場合は [ 0, 'http://192.168.11.10:81/stream'] という風に指定する。
record_resolution = 'SVGA' # 記録解像度
display_resolution = 'VGA' # 表示解像度
serial_port = ''      # シリアルポートの設定：マイコン経由で超音波センサを接続したポート（例：’COM11’）を指定する。未接続の場合は’’’またはNoneを指定する。
distance_threshold = 30    # 距離の閾値:超音波距離センサに近接した時に録画開始する(cm)。
line_access_token = ''  # LINE Notifyのアクセストークン

# ====(パラメータ設定：ここまで)====

resolution_list = {
    'QVGA': {'w':320 ,'h': 240},
    'VGA': {'w':640 ,'h': 480},
    'SVGA': {'w':800 ,'h': 600},
    'XGA': {'w':1024,'h': 768},
    'HD': {'w':1280,'h': 720},
    'SXGA': {'w':1280,'h':1024},
    'Full HD': {'w':1920,'h':1080},
    'WUXGA': {'w':1920,'h':1200},
    'QHD': {'w':2560,'h':1440},
    '4K UHD': {'w':3840,'h':2160},
}


line_url = "https://notify-api.line.me/api/notify" # LINE NotifyのURL
record_width = resolution_list[record_resolution]['w']
record_height = resolution_list[record_resolution]['h']
display_width = resolution_list[display_resolution]['w']
display_height = resolution_list[display_resolution]['h']

stop_thread = False
frames = [ None for cam in cameras]
frame_counters = [ None for cam in cameras]

diff_frames = [ None for cam in cameras]
diff_rates = [ 0 for cam in cameras]
fpss = {cam_idx: 0 for cam_idx in range(len(cameras))}

recordings = [ False for cam in cameras]
record_start_times = [ 0 for cam in cameras]
record_end_times = [ 0 for cam in cameras]
recordings = {cam_idx: False for cam_idx in range(len(cameras))}
outs = {cam_idx: None for cam_idx in range(len(cameras))}
filenames = {cam_idx: 0 for cam_idx in range(len(cameras))}
locks = {cam_idx: threading.Lock() for cam_idx in range(len(cameras))}  

distance = distance_threshold

class LineSender:
    url = ""
    access_token = ""
    headers = ""
    def __init__(self, url, access_token):
        self.url = url
        self.access_token = access_token
        self.headers = {'Authorization': 'Bearer ' + access_token}

    def message(self, message):
        payload = {'message': message}
        try:
            r = requests.post(self.url, headers=self.headers, params=payload,)
        except:
            print("lineSender.message had a problem: " + message)
    def image(self, message, filename):
        payload = {'message': message}
        try:
            files = {'imageFile': open(filename, "rb")}  # バイナリファイルオープン
            requests.post(self.url, data=payload, headers=self.headers, files=files)
        except:
            print("lineSender.message had a problem: " + message + " file " + filename)


def check_serial_input():
    global stop_thread, distance, distance_threshold
    ser = serial.Serial(serial_port, 9600)  # COMポートとボーレートを設定
    ser.readline()
    while not stop_thread:
        if ser.in_waiting > 0:
            val_arduino = ser.readline()
            str = ''.join(chr(byte) for byte in val_arduino if chr(byte).isdigit() or chr(byte) == '.')
            distance = float(str)
            if distance < distance_threshold:
                for cam_idx in range(len(cameras)):
                    if recordings[cam_idx] == False:
                        record_start_times[cam_idx] = time.time()
                        recordings[cam_idx] = True
                    record_end_times[cam_idx] = time.time() + rec_time


def capture_frames(cam_idx):
    global frames, stop_thread, recordings, record_end_times
    cap = cv2.VideoCapture(cameras[cam_idx])
    print("checking the the resolution of the camera " + str(cam_idx) )
    current_resolution_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH) 
    current_resolution_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) 
    if(current_resolution_w != resolution_list[record_resolution]['w'] or current_resolution_h != resolution_list[record_resolution]['h']):
        print("The resolution (" + str(current_resolution_w) + " and " + str(current_resolution_h) + ") differs from the specified record resolution (" + str(resolution_list[record_resolution]['w']) + " and " + str(resolution_list[record_resolution]['h']) + ").")
        print("The camera resolution is being set to " + str(resolution_list[record_resolution]['w']) + " and " + str(resolution_list[record_resolution]['h']))
        if(cap.set(cv2.CAP_PROP_FRAME_WIDTH,resolution_list[record_resolution]['w']) == False or cap.set(cv2.CAP_PROP_FRAME_HEIGHT,resolution_list[record_resolution]['h']) == False):
            print("Error: Could not set camera resolution.")
            return
        else:
            print("Now the camera resolution is " + str(resolution_list[record_resolution]['w']) + " and " + str(resolution_list[record_resolution]['h']))
    else:
        print("OK. The camera resolution is " + str(resolution_list[record_resolution]['w']) + " and " + str(resolution_list[record_resolution]['h']))
    frame_counter = 0
    start_time = time.time()
    last_frame = None
    while not stop_thread:
        #print(f"cam_idx: {cam_idx}")
        while not cap.isOpened():
            print("Error: Could not open video stream.")
            cap.release()
            time.sleep(1)
            cap = cv2.VideoCapture(cameras[cam_idx])

        ret, frame = cap.read()
        if frame is not None:
            frame_counter += 1
            if frame.shape[1] != record_width or frame.shape[0] != record_height:
                frame = cv2.resize(frame, (record_width, record_height))
            if diff_rate_threshold == 0:
                if recordings[cam_idx] == False:
                    recordings[cam_idx] = True
                    record_start_times[cam_idx] = time.time()
                    if(record_end_times[cam_idx] == 0):
                        record_end_times[cam_idx] = time.time()
                    record_end_times[cam_idx] =  record_end_times[cam_idx]+ rec_time
            else:
                if last_frame is None:
                    last_frame = frame.copy()
                diff = cv2.absdiff(last_frame, frame)
                diff_frames[cam_idx] = np.where(diff > diff_level_threshold, [0, 0, 255], [255, 0, 0]).astype(np.uint8)   
                significant_diff = np.sum(diff > diff_level_threshold)
                total_pixels = diff.size
                diff_rates[cam_idx  ] = significant_diff / total_pixels
                if diff_rates[cam_idx  ] > diff_rate_threshold:
                    if recordings[cam_idx] == False:
                        record_start_times[cam_idx] = time.time()
                        recordings[cam_idx] = True
                    record_end_times[cam_idx] = time.time() + rec_time
                last_frame = frame.copy()
            frames[cam_idx] = frame.copy()
            elapsed_time = time.time() - start_time
            current_datetime = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            if elapsed_time >= 1.0:
                fpss[cam_idx] = frame_counter / elapsed_time
                frame_counter = 0
                start_time = time.time()
            cv2.putText(frames[cam_idx] , current_datetime + " SOURCE: " + str(cam_idx) , (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(frames[cam_idx] , current_datetime + " SOURCE: " + str(cam_idx) , (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1, cv2.LINE_AA)
        else:
            print("failed to grab frame")

if line_access_token != "" and line_access_token != None:
    lineSender = LineSender(line_url, line_access_token)
threads = []
for cam_idx in range(len(cameras)):
    thread = threading.Thread(target=capture_frames, args=(cam_idx,))
    threads.append(thread)
    thread.start()
if serial_port != None and serial_port != "":
    serial_input_thread = threading.Thread(target=check_serial_input)
    serial_input_thread.start()

fourcc = cv2.VideoWriter_fourcc(*'XVID')

last_time = time.time()
display_counter = 0  
display_start_time = time.time()  

while True:
    current_time = time.time()
    if current_time - last_time >= 1.0/rec_fps:
        last_time = current_time
        combined_frame = np.full((display_height, 1, 3), (0, 0, 0), dtype=np.uint8)
        for cam_idx in range(len(cameras)):
            if frames[cam_idx] is None:
                frame = np.full((display_height, display_width, 3), (0,255,255), dtype=np.uint8)
            else:
                frame = cv2.resize(frames[cam_idx], (display_width, display_height))
            balance = "<" if diff_rates[cam_idx] < diff_rate_threshold else ">"
            if diff_rate_threshold == 0:
                cv2.putText(frame, f"fps: {fpss[cam_idx]:2.1f}", (100, display_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 3, cv2.LINE_AA)
                cv2.putText(frame, f"fps: {fpss[cam_idx]:2.1f}", (100, display_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
            elif diff_rate_threshold == 1:
                cv2.putText(frame, f"fps: {fpss[cam_idx]:2.1f} distance: {distance} < {distance_threshold}", (100, display_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 3, cv2.LINE_AA)
                cv2.putText(frame, f"fps: {fpss[cam_idx]:2.1f} distance: {distance} < {distance_threshold}", (100, display_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
            else:   
                cv2.putText(frame, f"fps: {fpss[cam_idx]:2.1f} diff_rate: {diff_rates[cam_idx]:.2f} {balance} {diff_rate_threshold:.2f}", (100, display_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 3, cv2.LINE_AA)
                cv2.putText(frame, f"fps: {fpss[cam_idx]:2.1f} diff_rate: {diff_rates[cam_idx]:.2f} {balance} {diff_rate_threshold:.2f}", (100, display_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
            if recordings[cam_idx]:
                cv2.circle(frame, (50, display_height - 40), 30, (0, 0, 255), -1)  
                start_datetime = datetime.datetime.fromtimestamp(record_start_times[cam_idx]).strftime("%Y/%m/%d %H:%M:%S")
                end_datetime = datetime.datetime.fromtimestamp(record_end_times[cam_idx]).strftime("%Y/%m/%d %H:%M:%S")
                start_end_datetime = start_datetime + " - " + end_datetime
                cv2.putText(frame, start_end_datetime, (100, display_height-50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 3, cv2.LINE_AA)
                cv2.putText(frame, start_end_datetime, (100, display_height-50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
                if current_time <= record_end_times[cam_idx]:
                    if isRecordedAsVideo and outs[cam_idx] is None:
                        start_datetime = datetime.datetime.fromtimestamp(record_start_times[cam_idx]).strftime("%Y%m%d%H%M%S")
                        filenames[cam_idx] = f"{cam_idx}_{start_datetime}"
                        outs[cam_idx] = cv2.VideoWriter("video_"+filenames[cam_idx]+".avi", fourcc, rec_fps, (record_width, record_height))
                        if line_access_token != "" and line_access_token != None:
                          cv2.imwrite('___tmp.jpg', frames[cam_idx])
                          lineSender.image(filenames[cam_idx], '___tmp.jpg')
                          os.remove('___tmp.jpg')

                    if isRecordedAsVideo == False and frame_counters[cam_idx] == None:
                        start_datetime = datetime.datetime.fromtimestamp(record_start_times[cam_idx]).strftime("%Y%m%d%H%M%S")
                        filenames[cam_idx] = f"{cam_idx}_{start_datetime}"   
                        frame_counters[cam_idx] = 0                     
                        if line_access_token != "" and line_access_token != None:
                          cv2.imwrite('___tmp.jpg', frames[cam_idx])
                          lineSender.image(filenames[cam_idx], '___tmp.jpg')
                          os.remove('___tmp.jpg')

                    locks[cam_idx].acquire() 
                    if isRecordedAsVideo:
                        outs[cam_idx].write(frames[cam_idx])
                    else:
                        cv2.imwrite('image_'+filenames[cam_idx]+f'_{frame_counters[cam_idx]:03d}'+'.jpg', frames[cam_idx])
                        frame_counters[cam_idx] += 1
                    locks[cam_idx].release() 
                else:
                    recordings[cam_idx] = False
                    if isRecordedAsVideo:
                        #print(outs[cam_idx])
                        if outs[cam_idx] != None:
                            outs[cam_idx].release()
                            outs[cam_idx] = None

                    else:
                        frame_counters[cam_idx] = None
            else:
                cv2.rectangle(frame, (50-30, display_height - 40-30), (50-10, display_height - 40+30), (0, 255, 0), -1)  
                cv2.rectangle(frame, (50+10, display_height - 40-30), (50+30, display_height - 40+30), (0, 255, 0), -1)     
            combined_frame = np.hstack((combined_frame, frame  ))
        cv2.imshow('Live Stream', combined_frame)
            
        display_counter += 1  
        if current_time - display_start_time >= 1.0:
            display_counter = 0
            display_start_time = time.time()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_thread = True  
            for thread in threads:
                thread.join()  
            break
    else:
        time.sleep(0.01)

cv2.destroyAllWindows() 

