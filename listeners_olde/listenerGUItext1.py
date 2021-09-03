import serial
import serial.tools.list_ports
import sys
import time
import threading
import tkinter
from tkinter import scrolledtext, simpledialog


class readerGUI:
    def __init__(self, toFile=False):
        """крафтим окно"""
        self.window = tkinter.Tk()
        self.frame = tkinter.Frame(self.window, height=500, width=500).grid()
        self.txt = scrolledtext.ScrolledText(self.frame)
        self.txt.grid(column=0, row=0)
        self.buttonstart = tkinter.Button(self.window, text="Старт", command=self.run).grid(row=1, column=0)
        self.buttonstop = tkinter.Button(self.window, text="Стоп", command=self.pause).grid(row=2, column=0)

        """сериал и файл для записи"""
        p = self._checkSerialPorts()
        if p is not None:
            try:
                self.ser = serial.Serial(port=p, baudrate=115200)
                self.txt.insert(tkinter.INSERT, "\nПодключено к: {}\n".format(self.ser.portstr))
            except serial.SerialException as e:
                self.txt.insert(tkinter.INSERT, 'Could not open serial port {}: {}\n'.format(self.ser.name, e))
                sys.exit(1)
            if toFile:
                try:
                    f = open("Data_{}.txt".format(time.strftime("%Y_%m_%d-%H%M%S")), "w")
                    print("Запись в файл {} ...".format(f.name))
                except OSError as e:
                    print('open() or file.__enter__() failed ', e)

        """крафтим тред"""
        self._stopflag = True
        self.reader_thread = threading.Thread(target=self._run_event, daemon=True, name="reader_thread")
        self.reader_thread.start()

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
                    result =  simpledialog.askstring("Арргх", "Не найдено Arduino \nУкажите какой порт использовать использовать\nНапример: COM5")
                    if (result[0:3] == 'COM' and result[3].isdigit()):
                        kost = False
        return result

    def run(self):
        self.txt.insert(tkinter.INSERT, "poehalee")
        self._stopflag = False

    def pause(self):
        self._stopflag = True

    def _run_event(self):
        while True:
            while not self._stopflag:
                for line in self.ser.read(14):
                    self.txt.insert(tkinter.INSERT, line)
                    self.txt.insert(tkinter.INSERT, '\ncom')


reader = readerGUI()
