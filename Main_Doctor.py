import datetime as dt
import sys
import csv
import sqlite3
from PyQt5.QtGui import QPixmap, QImage, QColor, QTransform, qRgb, QFont
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QFileDialog, QAction, QWidget, \
    QTableWidgetItem, QAbstractItemView
from PyQt5 import uic, QtCore, QtGui
from PyQt5.QtCore import Qt, QTimer, QTime
import time


class Doctor(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('Doctor_main_design.ui', self)
        self.con = sqlite3.connect("Appointments.db")
        self.cur = self.con.cursor()

        self.app_started = False
        self.app_stopped = False

        self.cabinet_num = '24'
        self.patient_num = 1
        self.current_patient_num = 1
        self.current_time = QTime.currentTime().toString('hh:mm')
        self.last_time_for_app = 60 * 10
        self.target_of_app = 'Первичный осмотр'
        self.time_for_app = 60 * 10
        self.query = 'SELECT * FROM apps'
        self.button_make_app.clicked.connect(self.make_appointment)

        self.open_table()

        self.patients_num = 0
        self.update_patients_num()

        self.clock = QTimer()
        self.clock.timeout.connect(self.update_time)
        self.clock.start(1)

        self.time_app = 0
        self.time_interval = 1000
        self.timer_up = QTimer()
        self.timer_up.setInterval(self.time_interval)
        self.timer_up.timeout.connect(self.update_uptime)
        self.button_start_finish.clicked.connect(self.appointment_clicked)

        self.average_time = 600
        self.all_time = 600
        self.expected_time = self.average_time
        self.update_average_time()
        self.update_expected_time()

        self.extension_time = 300
        self.button_extend_app.clicked.connect(self.extend_expected_time)

        self.leaving_time = 180
        self.button_leave.clicked.connect(self.leave)

    def color_row(self, row):
        for i in range(self.table_widget.columnCount()):
            self.table_widget.item(row, i).setBackground(QColor(0, 150, 100))

    def update_uptime(self):
        self.time_app += 1
        self.label_timer_app.setText(time.strftime('%M:%S', time.gmtime(self.time_app)))

    def update_time(self):
        self.current_time = QTime.currentTime()
        time_on_display = self.current_time.toString('hh:mm')
        self.label_clock.setText(time_on_display)

    def update_patients_num(self):
        self.label_patients_num.setNum(self.patients_num)

    def add_to_average_time(self):
        self.all_time += self.time_app
        self.average_time = self.all_time // (self.patients_num + 1)
        self.update_average_time()

    def update_average_time(self):
        if self.average_time % 60:
            self.label_average_time.setText(f'{self.average_time // 60} мин {self.average_time % 60} сек')
        else:
            self.label_average_time.setText(f'{self.average_time // 60} мин')

    def update_expected_time(self):
        self.label_expected_time.setText(time.strftime('%M:%S', time.gmtime(self.expected_time)))

    def extend_expected_time(self):
        self.expected_time += self.extension_time
        for elem, elem_2 in self.cur.execute('SELECT Time, Number FROM apps WHERE Type = ?', ('Запись',)).fetchall():
            if not elem[-2]:
                f_time_finding_1 = int(elem[0:2]) + self.average_time
                if f_time_finding_1 % 60 // 10:
                    new_time = f'{f_time_finding_1 // 60}:{f_time_finding_1 % 60}'
                else:
                    new_time = f'{f_time_finding_1 // 60}:0{f_time_finding_1 % 60}'
            else:
                f_time_finding_2 = int(elem[0:2]) + int(elem[3:5]) + self.average_time
                if f_time_finding_2 % 60 // 10:
                    new_time = f'{f_time_finding_2 // 60}:{f_time_finding_2 % 60}'
                else:
                    new_time = f'{f_time_finding_2 // 60}:0{f_time_finding_2 % 60}'
            self.cur.execute('UPDATE apps SET Time = ?', (new_time,))
        self.update_expected_time()

    def appointment_clicked(self):
        if self.app_started:
            self.finish_appointment()
        else:
            self.start_appointment()

    def start_appointment(self):
        self.button_start_finish.setText('Завершить приём')
        self.timer_up.start()
        self.app_started = True
        self.current_patient_num = self.cur.execute('SELECT Number FROM apps ORDER BY Time').fetchone()[0]
        if self.current_patient_num // 10:
            self.current_num = self.cabinet_num + str(self.current_patient_num)
        else:
            self.current_num = self.cabinet_num + '0' + str(self.current_patient_num)
        self.color_row(0)

    def finish_appointment(self):
        self.timer_up.stop()
        self.patients_num += 1
        self.add_to_average_time()
        self.time_app = 0
        self.label_timer_app.setText(time.strftime('%M:%S', time.gmtime(self.time_app)))
        self.update_patients_num()
        self.expected_time = self.average_time
        self.update_expected_time()
        self.button_start_finish.setText('Начать следующий приём')
        self.app_started = False
        self.cur.execute('DELETE FROM apps WHERE Number = ?', (self.current_patient_num,))
        self.open_table()

    def leave(self):
        if self.app_stopped:
            self.timer_up.start()
            self.app_stopped = False
            self.app_started = True
            self.button_leave.setText('Отлучиться (3 мин)')
        elif self.app_started:
            self.timer_up.stop()
            self.app_stopped = True
            self.app_started = False
            self.button_leave.setText('Вернуться к работе')

    def make_appointment(self):
        if self.patient_num // 10 == 0:
            num_for_table = '0' + str(self.patient_num)
        else:
            num_for_table = str(self.patient_num)
        self.time_for_app += self.average_time // 60
        if self.time_for_app % 60 // 10:
            app_time = f'{self.time_for_app // 60}:{self.time_for_app % 60}'
        else:
            app_time = f'{self.time_for_app // 60}:{"0" + str(self.time_for_app % 60)}'
        type_of_app = 'Запись'
        self.target_of_app = 'Первичный осмотр'
        self.add_appointment(num_for_table, app_time, type_of_app, 'Первичный осмотр')

    def add_appointment(self, num_for_table, time_for_patient, type_of_app, target_of_app):
        self.cur.execute('INSERT INTO apps VALUES(?, ?, ?, ?)', (self.cabinet_num + num_for_table,
                                                                 time_for_patient, type_of_app, target_of_app))
        self.open_table()
        self.patient_num += 1
        self.last_time_for_app = time_for_patient

    def open_table(self):
        res = self.con.cursor().execute(self.query).fetchall()
        self.table_widget.setColumnCount(4)
        self.table_widget.setRowCount(0)
        self.table_widget.setHorizontalHeaderLabels(['Номер', 'Время', 'Тип записи', 'Цель приёма'])
        for i, row in enumerate(res[1:]):
            self.table_widget.setRowCount(
                self.table_widget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.table_widget.setItem(
                    i, j, QTableWidgetItem(str(elem)))
        self.table_widget.resizeColumnsToContents()
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def closeEvent(self, event):
        self.connection.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Doctor()
    win.setFixedSize(690, 850)
    win.show()
    sys.exit(app.exec_())
