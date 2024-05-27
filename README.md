PCを効果的に使って動画や画像を撮影するためのユーティリティプログラムCamera Recorderを作ってみました。専門のビデオカメラやレコーダーを使わずに、気軽に現場の状況を記録することができます。

1.	Camera Recorderの紹介

PCを使って動画や画像を保存するためのソフトウェアです。USBカメラ(Webカメラ)やカメラ付きマイコン等をカメラとして使用します。
以下の機能を有します。

①	USBカメラを使用すると高品質（高解像度、高FPS）な録画が可能です。

②	ネットワークカメラ（カメラ付マイコン：ESP32_S3_WROOM)を使用するとWiFi経由で画像を収集できます。

③	複数のカメラを接続できます。

④	保存形式として、動画（avi）と静止画（jpg）の選択ができます。

⑤	録画解像度、表示解像度、FPS(フレーム毎秒)、録画時間を指定できます。

⑥	常時録画、差分録画、距離センサ連携録画ができます。

⑦	LINE notify機能で撮影開始時の画像を自動通知させることができます。

⑧	OneDriveやGoogle Driveといったクラウドストレージサービスを併用すると、手元のPCにて遠隔地で撮影した動画や画像を即座に確認することが可能です。


2.	PythonとCamera Recorderのインストール

Windows10/11の左下の虫眼鏡をクリックして、pythonと打ち込むとMicrosoft Storeが起動して、python最新版の3.12のインストールを促されるので、入手をクリックします。

![image](https://github.com/ymizu/cameraRecorder/assets/22882526/759134d0-3983-4331-8cb7-ca9193e19eb2)

Chrome等のブラウザでhttps://github.com/ymizu/cameraRecorder にアクセスして、Code→Download ZIPで、cameraRecorder-main.zipをダウンロードします。

![image](https://github.com/ymizu/cameraRecorder/assets/22882526/63636ed8-8627-401d-a144-3473ba732b2a)

cameraRecorder-main.zipをデスクトップ等の適当な場所に解凍すると、フォルダcameraRecorder-main 内にcameraRecorder.pyというファイルとdistanceSensorというフォルダを見つけることができます。前者はカメラで撮影した動画や画像を保存するためのプログラムです。後者は、距離センサ連携録画（後述）時に用いるマイコン（アルデュイーノ）に書き込むコード群が収められています。エクスプローラーでcameraRecorder-mainに移動して、[CTRL]+右クリックでPowerShellまたはコマンドプロンプトを起動してください。cameraRecorder.pyを実行する前に一度だけ以下のコマンド群を使用してください。

pip install python-opencv

pip install requests

pip install pyserial

3.	Camera Recorderの使い方

PowerShellまたはコマンドプロンプト上で、

python cameraRecorder.py

と打ち込みます。黄色の画面が立ち上がりますが、しばらくするとカメラからの映像が表示されます。終了するには画面上でqを押してください。
cameraRecorder.pyの最初に記載されているパラメータを修正することで、状況に即した動作をさせることができます。以下、パラメータの詳細について説明します。

isRecordedAsVideo  	ビデオとして記録するかどうかのフラグ：Trueの場合にはビデオ(avi)として記録、Falseの場合には画像(jpg)として記録する。

diff_rate_threshold	差分率の閾値：0の場合には常時録画、1の場合には超音波距離センサに近接した時に録画開始（距離センサ連携録画）、0から1の間は差分率が閾値を超えた場合に録画開始（差分録画）。

diff_level_threshold	差分レベルの閾値：差分レベルが閾値を超えた場合に差分レベルが閾値を下回ったら録画を開始する。

rec_fps	記録時のフレーム毎秒

rec_time	記録時間（秒）

cameras	カメラの指定：カメラが1台の場合は[0]、カメラが2台の場合は[0,1]、2台目がネットワークカメラ（ESP32_S3_WROOM）の場合は [ 0, 'http://192.168.11.10:81/stream'] という風に指定。

record_resolution	記録解像度（例：'SVGA'）

display_resolution	表示解像度（例：'VGA'）

serial_port	シリアルポートの設定：マイコン経由で超音波センサを接続したポートを指定する（例：’COM11’）。未接続の場合は’’またはNoneを指定する。

distance_threshold	距離の閾値（例：30）:超音波距離センサに近接した時に録画開始する(単位：cm)。

line_access_token	例：'x2mY8Koizz27DXY79AHP7zwCFuKvcqjUkM8tLi9t4St'

パラメータの設定例をいくつか提示します。

【設定例1】1台のUSBカメラでFPS:30フレーム毎秒で常時録画する。録画形式は動画（avi）として、10秒毎に個別のファイルを生成する（録画時間：10秒）。録画解像度はSVGA、表示解像度はVGAとする。OneDriveやGoogle Driveを介して現場で取得した動画（や画像）をオフィスのPCに自動転送することもできる。

isRecordedAsVideo = True

diff_rate_threshold = 0

diff_level_threshold = 30 # don’t care

rec_fps = 30

rec_time = 10

cameras =[0]

record_resolution =’SVGA’

display_resolution=’VGA’

serial_port = ‘’

distance_threshold = 30 #don’t care

line_access_token = ‘’

![image](https://github.com/ymizu/cameraRecorder/assets/22882526/8ff43c93-3105-4bd8-9caf-a8ee62afee80)

【設定例2】2台のESP32-S3-WROOMをネットワークカメラとして用いて差分録画を実施する。それらのURLがそれぞれ ('http://192.168.11.10:81/stream', 'http://192.168.11.11:81/stream') とする。録画解像度はSVGA、表示解像度はVGAとする。画素値256段階中30以上変化している箇所が全体の5%を超えている場合に、差分録画を開始する。録画開始後に5秒間、1FPSで画像を保存する。

isRecordedAsVideo = False

diff_rate_threshold = 0.05

diff_level_threshold = 30

rec_fps = 1

rec_time = 5

cameras =['http://192.168.11.10:81/stream', 'http://192.168.11.11:81/stream']

record_resolution =’SVGA’

display_resolution=’VGA’

serial_port = ‘’

distance_threshold = 30 #don’t care

line_access_token = ‘’

![image](https://github.com/ymizu/cameraRecorder/assets/22882526/423d5a6a-9e7b-47fd-8209-c6d3df85a8a5)

なお、ネットワークカメラとして用いるESP32-S3-WROOMには https://github.com/Freenove/Freenove_ESP32_S3_WROOM_Board/tree/main/C/Sketches/Sketch_07.2_As_VideoWebServer にあるinoファイルを書き込んでおいてください。書き込み手順および使い方は同レポジトリのC_Tutorial.pdfに記載されています。
line_access_tokenを設定すると手元のLINEアプリに録画開始時の画像を送信します。例えば、https://qiita.com/grundtein/items/fd51f5ba1e40994b8254に具体的なアクセストークンの取得方法が記載されています。

【設定例3】1台のUSBカメラで距離センサ連携録画を実施する。超音波距離センサの前方30cm以内に侵入物があった場合に録画を開始する。録画形式は動画として、録画開始後に5秒間、1FPSで動画を保存する。録画解像度、表示解像度はVGAとする。超音波距離センサを仲介するマイコン（アルデュイーノ）はCOM8に接続されているとする。

isRecordedAsVideo = True

diff_rate_threshold =1

diff_level_threshold = 30 # don’t care

rec_fps = 1

rec_time = 5

cameras = [0]

record_resolution = 'VGA'

display_resolution = 'VGA'

serial_port = 'COM11'

distance_threshold = 30

line_access_token = ‘’

![image](https://github.com/ymizu/cameraRecorder/assets/22882526/418754d3-551f-4570-bf76-eeb3fa1f147a)

アルデュイーノにはdistanceSensorに保存されているinoファイルを書き込んでおく。Digital I/Oピンの2と3に、超音波距離センサHC-SR04のtrig端子およびecho端子を接続しておく（参照：https://qiita.com/maominionbsk54/items/e5fbdc52f51b11abbea3）。
