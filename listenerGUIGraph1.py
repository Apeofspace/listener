import serial
import serial.tools.list_ports
import sys
import time
import threading
import tkinter
from tkinter import scrolledtext, simpledialog
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import numpy as np
import matplotlib

matplotlib.use('TKAgg')
# If you use the use() function, this must be done before importing matplotlib.pyplot. Calling use() after pyplot has been imported will have no effect.
import matplotlib.pyplot as plt
import matplotlib.animation as animation


class readerGUI:
    def __init__(self, toFile=False):
        self.toFile = toFile
        self.reader_thread = None
        self.plotter_thread = None
        self.plotinterval = 0.1
        self._stopflag = True
        """крафтим окно"""
        self.window = tkinter.Tk()
        self.txt = scrolledtext.ScrolledText(self.window, height=6)
        self.txt.grid(column=0, row=0)
        self.frame = tkinter.Frame()
        self.frame.grid()
        self.buttonstart = tkinter.Button(self.window, text="Старт", command=self.run).grid(row=2, column=1)
        self.buttonstop = tkinter.Button(self.window, text="Стоп", command=self.close).grid(row=2, column=2)
        # Добавим изображение
        # self.canvas = tkinter.Canvas(self.frame, height=300, width=300)
        # self.c_image = self.canvas.create_image(0, 0, anchor='nw')
        # self.canvas.grid(row=1, column=0)
        self.fig, self.ax = plt.subplots(1, 1)
        self.ax.set_aspect('equal')
        self.ax.set_xlim(0, 255)
        self.ax.set_ylim(0, 255)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)  # A tk.DrawingArea.
        # self.canvas.grid(row=1, column=0)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

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
                                                "Найдено несколько Arduino \nУкажите номер Arduino, который следует использовать")
                    result = arduinos[i]
                except ValueError:
                    self.txt.insert(tkinter.INSERT, "Введите номер\n")
        if len(arduinos) == 1:
            result = arduinos[0].name
        if len(arduinos) == 0:
            result = None
            if ports:
                kost = True
                while (kost):
                    result = simpledialog.askstring("Арргх",
                                                    "Не найдено Arduino \nУкажите какой порт использовать использовать\nНапример: COM5")
                    if (result[0:3] == 'COM' and result[3].isdigit()):
                        kost = False
        return result

    def run(self):
        """сериал и файл для записи"""
        p = self._checkSerialPorts()
        if p is not None:
            try:
                self.ser = serial.Serial(port=p, baudrate=57600)
                self.txt.insert(tkinter.INSERT, "Подключено к: {}\n".format(self.ser.portstr))
            except serial.SerialException as e:
                self.txt.insert(tkinter.INSERT, 'Could not open serial port: {}\n'.format(e))
            if self.toFile:
                try:
                    f = open("Data_{}.txt".format(time.strftime("%Y_%m_%d-%H%M%S")), "w")
                    self.txt.insert(tkinter.INSERT, "Запись в файл {} ...\n".format(f.name))
                except OSError as e:
                    self.txt.insert(tkinter.INSERT, 'open() or file.__enter__() failed \n', e)
        else:
            self.txt.insert(tkinter.INSERT, "Не найдено arduino\n")
            # self.buttonstart.config(state = tkinter.DISABLED)
            # self.buttonstart.configure()

        self.txt.insert(tkinter.INSERT, "\nОткрыть потоки")
        self.databuffer = []
        if self.reader_thread == None:
            """крафтим тред"""
            self._stopflag = False
            self.reader_thread = threading.Thread(target=self._worker, daemon=True, name="reader_thread")
            self.reader_thread.start()
            self.txt.insert(tkinter.INSERT, "\nОткрыт поток  ридера")
        if self.plotter_thread == None:
            """крафтим тред"""
            self.plotter_thread = threading.Thread(target=self._plot, daemon=True, name="plotter_thread")
            self.plotter_thread.start()
            self.txt.insert(tkinter.INSERT, "\nОткрыт поток плоттера")
            # # Block till we start receiving values
            # while self.isReceiving != True:
            #     time.sleep(0.1)

    def pause(self):
        # может неправильно приходить сигнал
        self._stopflag = True

    def close(self):
        self.txt.insert(tkinter.INSERT, "\nЗакрыть поток")
        self._stopflag = True
        self.reader_thread.join()
        self.txt.insert(tkinter.INSERT, "\nЗакрыт поток")
        # self.ser.close()

    def _worker(self):
        '''не особо проверенная на дурака функция'''
        linebuffer = ''
        while True:
            while not self._stopflag:
                ch = ''
                while (ch != "\n" and ch != "\r"):
                    for ch in self.ser.read(1):
                        ch = chr(ch)
                        # self.txt.insert(tkinter.INSERT, ch)
                        if (ch != "\n" and ch != "\r"):
                            linebuffer += ch
                linebuffer = ''.join(i for i in linebuffer if i.isdigit())
                # linebuffer = linebuffer/360
                self.txt.insert(tkinter.INSERT, linebuffer)
                self.databuffer.append((time.time(), linebuffer))  # тут тоже хорошо бы кьюшки использоваться а не лист
                linebuffer = ''

    def _plot(self):
        ...
        # pltInterval = 50  # Period at which the plot animation updates [ms]
        # xmin = 0
        # xmax = 100
        # ymin = -(1)
        # ymax = 1
        # fig = plt.figure()
        # ax = plt.axes(xlim=(xmin, xmax), ylim=(float(ymin - (ymax - ymin) / 10), float(ymax + (ymax - ymin) / 10)))
        # ax.set_title('Arduino Analog Read')
        # ax.set_xlabel("time")
        # ax.set_ylabel("AnalogRead Value")
        #
        # lineLabel = 'Potentiometer Value'
        # timeText = ax.text(0.50, 0.95, '', transform=ax.transAxes)
        # lines = ax.plot([], [], label=lineLabel)[0]
        # lineValueText = ax.text(0.50, 0.90, '', transform=ax.transAxes)
        # anim = animation.FuncAnimation(fig, s.getSerialData, fargs=(lines, lineValueText, lineLabel, timeText),
        #                                interval=pltInterval)  # fargs has to be a tuple
        #
        # plt.legend(loc="upper left")
        # plt.show()
        while True:
            while not self._stopflag:
                time.sleep(self.plotinterval)
                background = self.fig.canvas.copy_from_bbox(self.ax.bbox)  # cache the background
                if len(self.databuffer) != 0:
                    for i in range(len(self.databuffer)):
                        x, y = self.databuffer[i]
                        points = self.ax.plot(x, y, 'o')[0]
                        self.fig.canvas.restore_region(background)  # restore background
                        self.ax.draw_artist(points)  # redraw just the points
                        self.fig.canvas.blit(self.ax.bbox)  # fill in the axes rectangle
                    self.databuffer.clear()

    def on_closing(self):
        self.window.quit()
        self.window.destroy()


reader = readerGUI()
