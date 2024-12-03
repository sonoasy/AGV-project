# This Python file uses the following encoding: utf-8
import sys
import openai  # openai 라이브러리 임포트
import speech_recognition as sr  # 음성 인식 라이브러리 임포트

from PySide6.QtWidgets import QApplication, QMainWindow
import sys

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer

import paho.mqtt.client as mqtt

from ui_form import Ui_MainWindow
import json
from datetime import datetime
import pytz

# 한국 시간대 (Asia/Seoul)로 설정
korea_timezone = pytz.timezone("Asia/Seoul")

#Broker IP Address 와 Port
#라즈베리파이5 IP 주소 수정 필요
address = "70.22.226.104"
port = 1883

#MQTT command Topic
commandTopic = "AGV/command"

#MQTT sensor Topic
sensingTopic = "AGV/sensing"
# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py

#from ui_form import Ui_MainWindow

def get_response(sentence):
    # 각자 만든 API 키를 사용한다.
    api_key = ""  # API 키를 여기에 입력하십시오.

    # 원하는 동작이 되도록 prompt 를 입력한다.
    content = ("You are an LED controller. I will input a specific sentence about the current situation, "
               "and you need to interpret the sentence and respond with either 'LEDOFF' , 'LEDON' or 'IGNORE'. "
               "Do not provide any explanation, only respond with the specific word. "
               "ex1) I need to buy some groceries after work. -> 'IGNORE', "
               "ex2) I can't see well. -> 'LEDON', "
               "ex3) I don't want any distractions while watching a movie. -> 'LEDOFF'")

    # API 키 설정
    openai.api_key = api_key

    try:
        # ChatGPT API 호출
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # 사용할 모델 (예: gpt-4, gpt-3.5-turbo 등)
            messages=[
                {"role": "system", "content": content},
                {"role": "user", "content": sentence}
            ],
            max_tokens=256,  # 최대 토큰 수
            temperature=1,   # 다양성 설정
            top_p=1.0,       # nucleus sampling
            frequency_penalty=0,  # 빈번한 단어 사용 페널티
            presence_penalty=0    # 새로운 내용 등장 페널티
        )

        # 응답에서 텍스트 내용 추출
        return response['choices'][0]['message']['content']

    except Exception as e:
        print(f"Error: {e}")
        return None

class MainWindow(QMainWindow):

    #MQTT로 들어온 data를 받아줄 list 생성
    sensorData = list()
    #sensorData 중 최신 15개 data만 저장할 list
    sensingDataList = list()

    #MQTT로 보낼 command dict
    commandData = dict()
    #commandData 전체
    commandDataList = list()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init()


    def init(self):
        print('init')
        self.ui.midButton.clicked.connect(self.start_speech_recognition)

        # MQTT 클라이언트 생성
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        # 연결 시 콜백 함수 설정
        self.client.on_connect = self.on_connect
        # 메시지 수신 시 콜백 함수 설정
        self.client.on_message = self.on_message

        # Broker IP, port 연결
        self.client.connect(address, port)
        self.client.subscribe(sensingTopic, qos=1)
        self.client.loop_start()

        # QTimer 설정 (0.5초마다 settingUI 메서드 호출)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.settingUI)
        self.timer.start(500)  # 1000ms = 1초
        print('start')
    def makeCommandData(self, str, arg, finish):
        current_time = datetime.now(korea_timezone)
        self.commandData["time"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
        self.commandData["cmd_string"] = str
        self.commandData["arg_string"] = arg
        self.commandData["is_finish"] = finish
        return self.commandData

    def start(self):
        # MQTT 클라이언트 생성
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        # 연결 시 콜백 함수 설정
        self.client.on_connect = self.on_connect
        # 메시지 수신 시 콜백 함수 설정
        self.client.on_message = self.on_message

        # Broker IP, port 연결
        self.client.connect(address, port)
        self.client.subscribe(sensingTopic, qos=1)
        self.client.loop_start()

        # QTimer 설정 (0.5초마다 settingUI 메서드 호출)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.settingUI)
        self.timer.start(500)  # 1000ms = 1초
        print('start')

    def makeCommandData(self, str, arg, finish):
        current_time = datetime.now(korea_timezone)
        self.commandData["time"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
        self.commandData["cmd_string"] = str
        self.commandData["arg_string"] = arg
        self.commandData["is_finish"] = finish
        return self.commandData

    def stop(self):
        self.commandData = self.makeCommandData("stop", 100, 1)
        self.client.publish(commandTopic, json.dumps(self.commandData), qos=1)
        self.commandDataList.append(self.commandData)
        self.commandData = dict()

        self.client.loop_stop()
        print(self.commandDataList)

    def settingUI(self):
        self.ui.logText.clear()
        for i in range(len(self.commandDataList)):
            msg = "%3d | %s | %6s | %3d | %3d" % (
                i, self.commandDataList[i]["time"], self.commandDataList[i]["cmd_string"], self.commandDataList[i]["arg_string"],
                self.commandDataList[i]["is_finish"])
            self.ui.logText.appendPlainText(msg)

            self.ui.sensingText.clear()
        for i in range(len(self.sensingDataList)):
            self.sensingData = self.sensingDataList[i]

            msg = "%3d | %s | %3.2f | %3.2f | %3d | %3s" % (
                i+1, self.sensingData["time"], self.sensingData["num1"], self.sensingData["num2"], self.sensingData["is_finish"], self.sensingData["manual_mode"])
            self.ui.sensingText.appendPlainText(msg)

    def go(self):
        self.commandData = self.makeCommandData("go", 100, 1)
        self.client.publish(commandTopic, json.dumps(self.commandData), qos=1)
        self.commandDataList.append(self.commandData)
        self.commandData = dict()
        print(self.commandDataList)

    def mid(self):
        self.commandData = self.makeCommandData("mid", 100, 1)
        self.client.publish(commandTopic, json.dumps(self.commandData), qos=1)
        self.commandDataList.append(self.commandData)
        self.commandData = dict()
        print(self.commandDataList)

    def back(self):
        self.commandData = self.makeCommandData("back", 100, 1)
        self.client.publish(commandTopic, json.dumps(self.commandData), qos=1)
        self.commandDataList.append(self.commandData)
        self.commandData = dict()
        print(self.commandDataList)

    def left(self):
        self.commandData = self.makeCommandData("left", 100, 1)
        self.client.publish(commandTopic, json.dumps(self.commandData), qos=1)
        self.commandDataList.append(self.commandData)
        self.commandData = dict()
        print(self.commandDataList)

    def right(self):
        self.commandData = self.makeCommandData("right", 100, 1)
        self.client.publish(commandTopic, json.dumps(self.commandData), qos=1)
        self.commandDataList.append(self.commandData)
        self.commandData = dict()
        print(self.commandDataList)

    def closeEvent(self, event):
        self.commandData = self.makeCommandData("exit", 100, 1)
        self.client.publish(commandTopic, json.dumps(self.commandData), qos=1)
        self.commandDataList.append(self.commandData)
        self.commandData = dict()
        print(self.commandDataList)
        self.client.disconnect()
        current_time = datetime.now(korea_timezone)
        file_name = current_time.strftime("%Y-%m-%d") + ".txt"
        with open(file_name, "w") as file:
            for value in self.sensorData:
                file.write(str(value) + "\n")
        print("save data")
        event.accept()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("connected OK")
        else:
            print("Bad connection Returned code=", reason_code)

    def on_message(self, client, userdata, msg):
        message = json.loads(msg.payload.decode("utf-8"))

        self.sensorData.append(message)
        self.sensingDataList = self.sensorData[-15:]

    def enter(self):

        self.msg = self.ui.promptText.toPlainText()  # UI에서 입력받은 텍스트
        print(get_response(self.msg))  # get_response 함수로 응답 출력

    def closeEvent(self, event):
        event.accept()
    def start_speech_recognition(self):
                recognizer = sr.Recognizer()  # Recognizer 객체 생성
                with sr.Microphone() as source:  # 마이크 사용
                    print("음성을 인식 중입니다... 말하세요.")
                    recognizer.adjust_for_ambient_noise(source)  # 주변 소음에 맞춰서 마이크 설정
                    audio = recognizer.listen(source)  # 음성 듣기

                try:
                    # 음성을 텍스트로 변환
                    speech_text = recognizer.recognize_google(audio, language="ko-KR")  # 한국어로 변환
                    print(f"음성 인식 결과: {speech_text}")

                    # 음성 인식한 텍스트로 ChatGPT 응답 받기
                    response = get_response(speech_text)
                    print(f"ChatGPT 응답: {response}")

                    # 텍스트 박스에 응답 출력 (UI에서 결과 보여주기)
                    self.ui.promptText.setPlainText(response)

                except sr.UnknownValueError:
                    print("음성을 이해할 수 없습니다.")
                except sr.RequestError as e:
                    print(f"음성 인식 서비스 오류: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
