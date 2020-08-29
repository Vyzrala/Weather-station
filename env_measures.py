#!/usr/bin/env python3

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pandas as pd

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from functools import partial
import sys
import os
import socket
import time
import json
import re
import copy
import datetime as dt
import logging

import Adafruit_DHT
import RPi.GPIO as GPIO

MULTIPLIER = 1000  # variable used to convert milisecs to secs
OUTLIERS = .05  # coefficient of outliers to remove from one side of dataset

WINDOW_RESOLUTION = (800, 480)  # (width, height)
WINDOW_POSITION = (1000, 90)  # (x-position, y-position)

# Tuple used to convert font size in case of window resolution change
# Indexes:
# 0 - humidity/temperature
# 1 - server status
# 2 - Datetime/server_host
# 3 - Graphs_manual/settings_labels
FONT_CONVERSION = (str(WINDOW_RESOLUTION[0]*0.75*0.09), str(WINDOW_RESOLUTION[0]*0.75*0.05), str(WINDOW_RESOLUTION[0]*0.75*0.04), str(WINDOW_RESOLUTION[0]*0.75*0.031))  


class AppLogic():
	DHT_SENSOR = Adafruit_DHT.DHT11
	DHT_PIN = 17

	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	PIR_PIN = 4
	GPIO.setup(PIR_PIN, GPIO.IN)
	
	default_settings = None
	custom_settings = None
	last_time_measure = None
	
	settings_filename = "data/settings.json"
	device_ip = None
	zabbix_ip = None
	zabbix_port = None
	device_ip = None
	
	ipv4_pattern = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
	digits_pattern = "^[0-9]+$"
	validators = [ipv4_pattern,  		# device_ip
				  ipv4_pattern,  		# zabbix_ip
				  digits_pattern,		# zabbix_port
				  digits_pattern, 		# refresh_time
				  digits_pattern] 		# motion_refresh_time

	def __init__(self):
		logging.basicConfig(filename="data/app_info.log", level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%d/%m/%y %I:%M:%S %p')
		self.load_settings()
		self.date_today = str(dt.datetime.today()).split()[0]
		self.temperature_measure_filename = "temperature_" + self.date_today + ".txt"
		self.humidity_measure_filename = "humidity_" + self.date_today + ".txt"
		
		msg = "\nYour settings in use:"
		if self.default_settings == self.custom_settings:
			logging.info("Default settings are in use.")
			msg = "\nDefault settings are in use:"
		print(msg, json.dumps(self.custom_settings, indent=4))

	def get_current_datetime(self):
		# returned format: 
		# dd/mm/yyyy hh:mm:ss
		return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())
	
	def get_temperature_humidity(self):
		humidity, temperature = Adafruit_DHT.read(self.DHT_SENSOR, self.DHT_PIN)
		return temperature, humidity
		
	def get_motion(self):
		motion = False
		if self.last_time_measure is not None:
			if (dt.datetime.now() - self.last_time_measure) > dt.timedelta(seconds=self.motion_refresh_time):
				motion = True if GPIO.input(self.PIR_PIN) else False
				self.last_time_measure = dt.datetime.now()
		else:
			motion = True if GPIO.input(self.PIR_PIN) else False
			self.last_time_measure = dt.datetime.now()
		return motion
	
	def get_sensors_data(self):
		self.date_today = str(dt.datetime.today()).split()[0]
		current_date_time = self.get_current_datetime()
		temp, humidity = self.get_temperature_humidity()
		motion = self.get_motion()
		return [temp, current_date_time, humidity, motion]
	
	def get_server_status(self):
		try:
			host_name = socket.gethostbyaddr(self.zabbix_ip)[0]
		except:
			host_name = self.zabbix_ip
		
		if self.zabbix_ip == "10.0.10.55": host_name = "Zabbix"
		response = os.system("ping -c 1 " + self.zabbix_ip)
		response = True if response == 0 else False
		# return format:
		# [string (host name), string (up or down)]
		return [host_name, response]
	
	def send_to_sever(self, measure):
		# Single measure format: 
		# ["date", "time", "temperature", "humidity"]
		msg = "/usr/bin/zabbix_sender  -z " + str(self.zabbix_ip) + " -p " + str(self.zabbix_port) + " -s " + str(self.device_ip) + " -k "
		tmp_msg = msg + "sensor_temperature -o " + str(measure[2])
		hum_msg = msg + "sensor_humidity -o " + str(measure[3])
		os.popen(tmp_msg)
		os.popen(hum_msg)
		
	def save_measure(self, measure, measure_type):
		if measure_type == "temperature":
			path = "data/measures/temperature_" + self.date_today + ".txt"
		elif measure_type == "humidity":
			path = "data/measures/humidity_" + self.date_today + ".txt"
		
		with open(path, "a+") as mf:
			print(measure, file=mf, flush=True)
		
	def save_settings(self, custom_settings):
		message = QMessageBox()
		save_allowance = False
		if type(custom_settings) == list:
			m = list(map(lambda x:x.text(), custom_settings))
			if "" in m or " " in m:
				message.setText("Error, puste pola")
				message.exec_()		
			else:
				m = copy.deepcopy(self.default_settings)
				for i, key in enumerate(list(m.keys())[1:]):
					m[key] = custom_settings[i].text()
					custom_settings[i].clear()
				custom_settings = m
				print(custom_settings)
				del m
				save_allowance = True
		else:	
			save_allowance = True
			
		if save_allowance:
			to_save = {"default": self.default_settings, "custom": custom_settings}
			with open(self.settings_filename,"w+") as sf:
				print(json.dumps(to_save, indent=4), file=sf, flush=True)

			message.setText("Settings saved")
			message.exec_()	
			logging.info("Application restart -settings change")
			os.execv(__file__, sys.argv)
		
	def load_settings(self):
		with open(self.settings_filename) as jf:
			settings = json.load(jf)
		
		self.custom_settings = settings['custom']
		self.default_settings = settings['default']
		
		con1 = bool(re.match(self.ipv4_pattern, self.custom_settings['device_ip']))
		con2 = bool(re.match(self.ipv4_pattern, self.custom_settings['zabbix_ip']))
		con3 = bool(re.match(self.digits_pattern, str(self.custom_settings['zabbix_port'])))
		con4 = bool(re.match(self.digits_pattern, str(self.custom_settings['refresh_time'])))
		con5 = bool(re.match(self.digits_pattern, str(self.custom_settings['motion_refresh_time'])))

		if not (con1 and con2 and con3 and con4 and con5):
			self.custom_settings = self.default_settings
			msg_box = QMessageBox()
			msg_box.setIcon(QMessageBox.Warning)
			msg_box.setText("Niepoprawne ustawienia użytkownika.\nDomyślne ustawienia w użyciu.")
			msg_box.exec_()
			
		self.device_ip = self.custom_settings['device_ip']
		self.zabbix_ip = self.custom_settings['zabbix_ip']
		self.zabbix_port = self.custom_settings['zabbix_port']
		self.refresh_time = int(self.custom_settings['refresh_time'])
		self.motion_refresh_time = int(self.custom_settings['motion_refresh_time'])
					
	def restore_default(self):
		self.device_ip = self.default_settings['device_ip']
		self.zabbix_ip = self.default_settings['zabbix_ip']
		self.zabbix_port = self.default_settings['zabbix_port']
		self.refresh_time = self.default_settings['refresh_time']
		self.motion_refresh_time = self.default_settings['motion_refresh_time']
		self.save_settings(self.default_settings)
		
	def get_graphs(self, number_of_days):
		try:
			number_of_days = int(number_of_days.text())
		except:
			msg_box = QMessageBox()
			msg_box.setIcon(QMessageBox.Warning)
			msg_box.setText("Nieprawidłowa ilość dni.")
			msg_box.exec_()
			return

		self.graph_window = GraphWindow(self, number_of_days)


class GraphWindow(QMainWindow):
	def __init__(self, app_logic, number_of_days):
		QMainWindow.__init__(self)
		self.app_logic = app_logic
		self.init_UI()
		self.get_data(number_of_days)
		self.process_data()
		self.draw_graph()
		
	def init_UI(self):
		self.setGeometry(WINDOW_POSITION[0]+35, WINDOW_POSITION[1]+35, WINDOW_RESOLUTION[0], WINDOW_RESOLUTION[1])
		# ~ self.showMaximized()  # show maximized window
		self.setWindowTitle("Wykres średniej wilgotności i temperatury")
		self.central_wid = QWidget()
		self.setCentralWidget(self.central_wid)
		self.layout = QGridLayout()
		self.central_wid.setLayout(self.layout)
		self.show()
	
	def get_data(self, number_of_days):
		end_date = str(dt.datetime.today()).split()[0]
		datetime_obj = dt.datetime.strptime(end_date, "%Y-%m-%d")
		days = [datetime_obj - dt.timedelta(days=i) for i in range(number_of_days)]
		days = list(map(lambda x: str(x).split()[0], days))
		temperature_files = list(map(lambda x: "data/measures/temperature_" + x + ".txt", days))
		humidity_files = list(map(lambda x: "data/measures/humidity_" + x + ".txt", days))
		temperature_data = self.load_data(temperature_files, "Temperature")
		humidity_data = self.load_data(humidity_files, "Humidity")
		humidity_data["Temperature"] = temperature_data.Temperature
		self.data = humidity_data
		self.graph_title = "Dane od {} do {}".format(days[-1], days[0])
		if days[-1] == days[0]:
			self.graph_title = "Dane z dzisiejszego dnia"
	
	def load_data(self, files, column_title):
		dfs = []
		for data_piece in files:
			if os.path.isfile(data_piece):
				df = pd.read_csv(data_piece, sep=";", header=None)
				dfs.append(df)
		dfs = pd.concat(dfs, axis=0, ignore_index=True)
		dfs.columns = ["Date", "Time", column_title.capitalize()]
		return dfs
		
	def process_data(self):
		self.data.Time = self.data.Time.apply(lambda x: x.split(":")[0])
		self.data = self.data.rename(columns={"Time": "Hour"})
		# removal of outliers
		result = self.data[self.data.Humidity.between(self.data.Humidity.quantile(OUTLIERS), self.data.Humidity.quantile(1-OUTLIERS))]
		self.data = result
		self.day_hour_groupped = self.data.groupby(['Date','Hour']).mean()
		self.hour_groupped = self.data.groupby(['Hour']).mean()
		
		tmp = copy.deepcopy(self.hour_groupped)
		self.humidity = tmp.drop(["Temperature"], axis=1)
		self.temperature = tmp.drop(["Humidity"], axis=1)
		del tmp, result
	
	def draw_graph(self):
		sc = MplCanvas(self, width=5, height=4, dpi=100)
		ax1 = self.humidity.plot(ax=sc.axes, title=self.graph_title, x_compat=True)
		ax2 = self.temperature.plot(ax=sc.axes, secondary_y=True, x_compat=True)
		ax1.xaxis.set_minor_locator(ticker.MultipleLocator(1))
		ax1.set_xlabel("Godzina")
		ax1.set_ylabel("Wilgotność (%)")
		ax2.set_ylabel("Temperatura ("+chr(176)+"C)")
		h1, l1 = ax1.get_legend_handles_labels()
		h2, l2 = ax2.get_legend_handles_labels()
		ax1.legend(h1+h2, ["Wilgotność", "Temperatura (right)"], loc='best')
		# ~ print(self.hour_groupped, "\nRecords -", self.data.shape[0])
		print("Number of rows:", self.data.shape[0])
		self.layout.addWidget(sc,0,0)
		

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        fig.subplots_adjust(0.10, 0.10, 0.90, 0.90)  # left, bottom, right, top (clock wise)
        super(MplCanvas, self).__init__(fig)
		

class GUI(QMainWindow):
	def __init__(self):
		QMainWindow.__init__(self)
		self.init_class_varaibles()
		self.update_data()
		self.init_UI()
		self.update_UI()
	
	def init_UI(self):
		self.setGeometry(WINDOW_POSITION[0], WINDOW_POSITION[1], WINDOW_RESOLUTION[0], WINDOW_RESOLUTION[1])
		self.setWindowTitle("Pomiary środowiskowe")
		self.show()
		# tabs
		self.tab_widget = QTabWidget()
		self.setCentralWidget(self.tab_widget)
		style = "QTabBar {font-size: "+FONT_CONVERSION[3]+"pt; left: 5px; top: 5px} QTabWidget::tab-bar {left: 5px; top: 5px}"
		self.tab_widget.setStyleSheet(style)
		# TAB 1 - Measures (Pomiary)
		self.tab1 = self.measures_tab()
		self.tab_widget.addTab(self.tab1, "Pomiary")
		# TAB 2 - Settings (Ustawienia)
		self.tab2 = self.settings_tab()
		self.tab_widget.addTab(self.tab2, "Ustawienia")
		# TAB 3 - Graphs
		self.tab3 = self.graphs_tab()
		self.tab_widget.addTab(self.tab3, "Wykresy")
	
	def init_class_varaibles(self):
		self.app_logic = AppLogic()
		self.refresh_time = self.app_logic.refresh_time
		self.motion_refresh_time = self.app_logic.refresh_time
		
		# status bar
		self.status_bar = QStatusBar()
		self.setStatusBar(self.status_bar)
		self.status_bar_label = QLabel()
		self.status_bar_label.setAlignment(Qt.AlignCenter)
		self.status_bar.addWidget(self.status_bar_label,1)
		self.status_bar.show()
		
		self.temperature_text = None
		self.humidity_text = None
		self.motion_text = None
		self.current_date_text = None
		self.current_time_text = None
		self.server_status_text = None	
		self.server_host_text = None
				
		self.temperature_label = QLabel(self.temperature_text)
		self.humidity_label = QLabel(self.humidity_text)
		self.motion_label = QLabel(self.motion_text)
		self.current_date_label = QLabel(self.current_date_text)
		self.current_time_label = QLabel(self.current_time_text)
		self.server_status_label = QLabel(self.server_status_text)
		self.server_host_label = QLabel(self.server_host_text)
		self.server_host_label.setWordWrap(True)
		
	def update_UI(self):
		self.qtimer = QTimer()
		self.qtimer.setInterval(self.refresh_time*MULTIPLIER)
		self.qtimer.timeout.connect(self.update_data)
		self.qtimer.start()
	
	def settings_tab(self):
		# ~ "IP urządzenia: "
		settings_labels = ["Zabbix IP: ", "Zabbix port: ", "Czas odświeżania", "Czas detekcji ruchu: "]
		settings_labels = [QLabel(label) for label in settings_labels]
		style = "font: "+FONT_CONVERSION[3]+"pt Calibri"
		settings_default_text = ["", "", "w sekundach", "w sekundach"]
		settings_data = [QLineEdit() for _ in range(len(settings_labels))]
		validators = self.app_logic.validators[1:]

		form_layout = QFormLayout()
		form_layout.addRow(QLabel(""))
		for i in range(len(settings_labels)):
			settings_data[i].setText(settings_default_text[i])
			settings_data[i].setValidator(QRegExpValidator(QRegExp(validators[i]), settings_data[i]))
			settings_labels[i].setStyleSheet(style)
			form_layout.addRow(settings_labels[i], settings_data[i])
		
		save_button = QPushButton("Zapisz")
		save_button_action = partial(self.app_logic.save_settings, settings_data)
		save_button.clicked.connect(save_button_action)
		
		restore_default_button = QPushButton("Przywróć domyślne")
		restore_default_button.clicked.connect(self.app_logic.restore_default)
		
		# Horizontal line
		horizontal_line = QFrame()
		horizontal_line.setFrameShape(QFrame.HLine)
		horizontal_line.setFrameShadow(QFrame.Sunken)
		form_layout.addRow(horizontal_line)

		form_layout.addRow(save_button, restore_default_button)
		settings_tab_widget = QWidget()
		settings_tab_widget.setLayout(form_layout)
		return settings_tab_widget
	
	def measures_tab(self):
		tab = QWidget()
		grid = QGridLayout()
		grid.addWidget(self.make_box("Temperatura", self.temperature_label), 0, 0)
		grid.addWidget(self.make_box("Data i czas", (self.current_date_label, self.current_time_label)), 0, 1)
		grid.addWidget(self.make_box("Wilgotność", self.humidity_label), 1, 0)
		grid.addWidget(self.make_box("Status serwera", (self.server_host_label, self.server_status_label)), 1, 1)
		tab.setLayout(grid)
		return tab
	
	def make_box(self, title, label):
		group_box = QGroupBox(title)
		# Style of titles of tiles on the "Pomiary" tab
		style = "QGroupBox::title {subcontrol-origin: margin; subcontrol-position: top right; padding-right: 7px} QGroupBox {font-size: "+FONT_CONVERSION[2]+"pt; font-weight: bold; border: 2px solid gray; border-radius: 5px; margin-top: 1ex}"
		group_box.setStyleSheet(style)
		grid = QGridLayout()
		if type(label) == tuple:  # Labels (texts) of datetime and server status
			style = "qproperty-alignment: AlignCenter; font: "+FONT_CONVERSION[2]+"pt Calibri"
			pad = "; padding-top: "+str(int(WINDOW_RESOLUTION[0]*0.032))+"px"  # getting proportion of the screen from pixels
			label[0].setStyleSheet(style+pad)
			label[1].setStyleSheet(style)
			grid.addWidget(label[0])  # date label or name of host
			grid.addWidget(label[1])  # time label or server status
		else:  # Labels (digits) of temperature and humidity
			if title == "Wilgotność":
				style = "color: rgb(30,210,255); qproperty-alignment: AlignCenter; font: "+FONT_CONVERSION[0]+"pt Calibri"
				label.setStyleSheet(style)
			elif title == "Temperatura":
				style = "color: rgb(230,161,65); qproperty-alignment: AlignCenter; font: "+FONT_CONVERSION[0]+"pt Calibri"
				label.setStyleSheet(style)
			grid.addWidget(label)

		group_box.setLayout(grid)
		return group_box
	
	def graphs_tab(self):
		data_from_x_days = QLineEdit()
		data_from_x_days.setText("ilość dni")
		form_layout = QFormLayout()
		
		style = "font: "+FONT_CONVERSION[3]+"pt Calibri"
		hint = QLabel("Z ilu dni sporządzić wykres? ")
		hint.setStyleSheet(style)
		form_layout.addRow(QLabel(""))
		form_layout.addRow(hint, data_from_x_days)

		graphs_button = QPushButton("Generuj wykres")
		graphs_button_action = partial(self.app_logic.get_graphs, data_from_x_days)
		graphs_button.clicked.connect(graphs_button_action)
		
		form_layout.addRow(graphs_button)
		
		legend_labels_texts= ["","Instrukcja:", "1 dzień - Dane z dzisiejszego dnia od godziny 00:00 do teraz", "2 dni - Dane z wczorajszego dnia od godziny 00:00 do teraz", "etc."]
		legend_labels = [QLabel(text) for text in legend_labels_texts]
		for label in legend_labels:
			label.setStyleSheet(style)
			form_layout.addRow(label)
		
		graphs_tab_widget = QWidget()
		graphs_tab_widget.setLayout(form_layout)
		return graphs_tab_widget
	
	def update_data(self):
		sensors_data = self.app_logic.get_sensors_data()
		if sensors_data[0] is not None and sensors_data[2] is not None:  # temperature and humidity cannot be None
			ping_status = self.app_logic.get_server_status()
			# ~ ping_status = ["Debugg mode", True]
			self.server_host_text = ping_status[0]
			self.server_status_text = "Aktywny" if ping_status[1] == True else "Brak połączenia"
			date, time = sensors_data[1].split()
			self.current_date_text = date
			self.current_time_text = time
			self.temperature_text = str(sensors_data[0]) + " " + chr(176) + "C"
			self.humidity_text = str(sensors_data[2]) + " %"
			self.motion_text = "Wykryto" if sensors_data[3] else "Brak"
			# ["date", "time", "temperature", "humidity"]
			single_measure = [date, time, str(sensors_data[0]), str(sensors_data[2])]
			if self.server_status_text == "Aktywny":  # if server is up send measure to server
				self.app_logic.send_to_sever(single_measure)
			else:
				logging.info("No connection with server")
			self.app_logic.save_measure(";".join([date, time, str(sensors_data[0])]), "temperature")
			self.app_logic.save_measure(";".join([date, time, str(sensors_data[2])]), "humidity")
			self.update_labels()
		else:
			# ~ self.app_logic.send_to_sever([None, None, "0", "0"])  # send zeros to zabbix if measures are None
			self.update_data()  # get another measure
		
	def update_labels(self):
		self.current_date_label.setText("Data: "+self.current_date_text)
		self.current_time_label.setText("Czas: " + self.current_time_text)
		self.temperature_label.setText(self.temperature_text)
		self.humidity_label.setText(self.humidity_text)
		self.motion_label.setText(self.motion_text)
		
		self.status_bar_label.setText("IP urządzenia: {} \t\t Ruch: {}".format(self.app_logic.device_ip, self.motion_text))
		
		self.server_status_label.setText(self.server_status_text)
		self.server_host_label.setText("Host: "+self.server_host_text)
		self.update_server_status()
	
	def update_server_status(self):
		if self.server_status_text == "Aktywny":
			style = "color: green; font: bold "+FONT_CONVERSION[1]+"pt Calibri"
			self.server_status_label.setStyleSheet(style)
		else:
			style = "color: red; font: bold "+FONT_CONVERSION[1]+"pt Calibri"
			self.server_status_label.setStyleSheet(style)
	
	def screen_wake_up(self, motion):
		if motion == "Wykryto":
			# TODO
			pass


def main():
	# ~ try:
	app = QApplication(sys.argv)
	main_window = GUI()
	sys.exit(app.exec_())
	# ~ except:
		# ~ print("\nError:\n", sys.exc_info()[0])
		# ~ os.execv(__file__, sys.argv)  # auto script	restart 
		
if __name__ == "__main__":
	main()

