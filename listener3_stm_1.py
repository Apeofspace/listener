import serial
import serial.tools.list_ports
import sys
import datetime
import threading
import tkinter
from tkinter import scrolledtext, simpledialog, messagebox
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import numpy as np
import matplotlib

matplotlib.use('TKAgg')
# If you use the use() function, this must be done before importing matplotlib.pyplot. Calling use() after pyplot has been imported will have no effect.
import matplotlib.pyplot as plt
import matplotlib.animation as animation


class listener:
    def __init__(self, toFile=False, baud=230400):
        self.serialThread = None
        self._stopflag = True
        self.toFile = toFile
        self.baud = baud
        self.file = None
        self.databuffer = []

        """Tkinter"""
        self.root = tkinter.Tk()
        self.root.title("Listener")
        # текст
        self.frametxt = tkinter.Frame(self.root)
        self.frametxt.pack(expand=True, fill='both', side='left')
        self.txt = scrolledtext.ScrolledText(self.frametxt, height=20, width=100)
        self.txt.pack(fill='both', expand=True)
        # кнопки
        self.framebuttons = tkinter.Frame(self.root)
        self.framebuttons.pack(side='right')
        self.buttonstart = tkinter.Button(self.framebuttons, text="Старт")
        self.buttonstart.pack(side='top')
        self.buttonstart.bind('<Button-1>', self.run)
        self.buttonstart.bind('<Return>', self.run) #что бы ентер работал тоже
        self.buttonstart.focus_set()

        self.buttonpause = tkinter.Button(self.framebuttons, text="Пауза", command=self.pause)
        self.buttonpause.pack(side='top')
        self.buttonstop = tkinter.Button(self.framebuttons, text="Стоп", command=self.close)
        self.buttonstop.pack(side='top')
        # пуск
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def _serialThread(self):
        self._killFlag = False
        line = ''
        zaztest=0

        while True:
            if self._killFlag:
                break
            while not self._stopflag:
                try:
                    line = self.ser.read(10)
                    # line = line.decode('ascii')
                    stamp = datetime.datetime.now()
                    # line = int.from_bytes(line, byteorder=sys.byteorder)
                    # line = line&0x3FFF
                    # line = str(stamp) +' ' + str(line) +'\n'
                except Exception as e:
                    print('Error reading/decoding line: ', e)

                #в поле
                for l in line:
                    l = bin(l)
                    l+= '\n'
                    self.txt.insert(tkinter.INSERT, l)
                self.txt.insert(tkinter.INSERT, '\n')
                self.txt.see(tkinter.END)  # перемотка в конец
                zaztest+=1
                if zaztest == 20:
                    zaztest=0
                    self.file.write("\n*********test*********\n")

                #в файл
                if self.toFile:
                    try:
                        line = line.rstrip() +'\n'
                        self.file.write(line)
                    except Exception as e:
                        print('Error writing to file: ', e)



    def _checkSerialPorts(self):
        arduinos = []
        result = None
        ports = list(serial.tools.list_ports.comports())
        self.txt.insert(tkinter.INSERT, "Поиск COM портов\n")
        for p in ports:
            self.txt.insert(tkinter.INSERT, p)
            if "Arduino" in p.description:
                arduinos.append(p)
        if len(arduinos) > 1:
            while result is None:
                try:
                    i = simpledialog.askinteger("Арргх",
                                                "Найдено несколько Arduino \nУкажите номер Arduino, который следует использовать",initialvalue=ports[0])
                    result = arduinos[i]
                except ValueError:
                    messagebox.showerror("Ошибка", "Должно быть введено число")
        if len(arduinos) == 1:
            result = arduinos[0].name
        if len(arduinos) == 0:
            result = None
            if ports:
                kost = True
                while (kost):
                    result = simpledialog.askstring("Арргх",
                                                    "Не найдено Arduino \nУкажите какой порт использовать использовать\nНапример: COM5", initialvalue="COM5")
                    if (result[0:3] == 'COM' and result[3].isdigit()):
                        kost = False
        return result

    def run(self, event):
        p = self._checkSerialPorts()
        if p is not None:
            try:
                self.ser = serial.Serial(port=p, baudrate=self.baud)
                self.txt.insert(tkinter.INSERT, "\nПодключено к: {}\n".format(self.ser.portstr))
            except serial.SerialException as e:
                self.txt.insert(tkinter.INSERT, 'Could not open serial port: {}\n'.format(e))

            if self.toFile:
                try:
                    self.file = open("Data_{}.txt".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S")), "w")
                    self.txt.insert(tkinter.INSERT, "Запись в файл {} ...\n".format(self.file.name))
                except OSError as e:
                    self.txt.insert(tkinter.INSERT, 'open() or file.__enter__() failed \n', e)
                    self.toFile = False
            self.databuffer = []

            #а жив ли поточек?
            thread_alive = True
            if self.serialThread == None:
                thread_alive = False
            elif not self.serialThread.is_alive():
                thread_alive = False

            if thread_alive == False:
                """крафтим тред"""
                try:
                    self._stopflag = False
                    self.serialThread = threading.Thread(target=self._serialThread, daemon=True, name="reader_thread")
                    self.serialThread.start()
                    self.txt.insert(tkinter.INSERT, "\nОткрыт поток\n")
                    self.buttonstart.config(state=tkinter.DISABLED)
                except Exception as e:
                    self.txt.insert(tkinter.INSERT, 'Невозможно запустить поток \n', e)
        else:
            self.txt.insert(tkinter.INSERT, "Не найдено arduino\n")

        # self.txt.insert(tkinter.INSERT, "\nОткрыть потоки")

        self.txt.see(tkinter.END)  # перемотка в конец

    def stopThread(self):
        self._killFlag = True

    def close(self):
        self._stopflag = True
        self.buttonstart.config(state=tkinter.NORMAL)
        try:
            self.stopThread()
            self.file = None
            self.txt.insert(tkinter.INSERT, "\nЗакрыт поток")
        except:
            self.txt.insert(tkinter.INSERT, "\nНет потока")
        try:
            self.ser.close()
            self.txt.insert(tkinter.INSERT, "\nЗакрыт слушатель")
        except:
            self.txt.insert(tkinter.INSERT, "\nНет слушателя")

    def pause(self):
        # может неправильно приходить сигнал
        self._stopflag = not self._stopflag

    def on_closing(self):
        self.close()
        self.root.quit()
        self.root.destroy()


listener = listener(True)
