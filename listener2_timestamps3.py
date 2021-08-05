import serial
import serial.tools.list_ports
import sys
import datetime
import time
import threading
import tkinter
from tkinter import scrolledtext, simpledialog, messagebox
import queue


class listener:
    def __init__(self, toFile=False, toField=True, baud=230400):
        self.serialThread = None
        self._stopFlag = True
        self.toFile = toFile
        self.toField = toField
        self.baud = baud
        self.file = None
        self.q = queue.Queue(600)

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
        self.buttonstart.bind('<Return>', self.run)  # что бы ентер работал тоже
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
        timeoutMultiplier = 100
        period = 0

        prevTime = time.time()
        curTime = prevTime
        curDelta = curTime - prevTime
        prevDelta = curTime - prevTime
        startTime = prevTime
        endTime = prevTime

        while True:
            if self._killFlag:
                break
            while not self._stopFlag:
                try:
                    curTime = time.perf_counter()
                    curDelta = curTime - prevTime
                    prevTime = curTime

                    line = self.ser.readline()
                    line = line.decode('ascii')

                    # self.l = len(self.databuffer)

                    if self.q.empty():
                        self.startTime = curTime

                    if curDelta > (prevDelta * timeoutMultiplier):
                        if not self.q.empty():
                            # обнаружен длинный разрыв между транзакциями
                            try:
                                # записываем весь буфер
                                endTime = prevTime
                                self.write(endTime, startTime)

                                # начинаем новый период
                                self.q.queue.clear()  # вот тут может происходить боль
                                self.q.put(line)
                                startTime = curTime
                            except ZeroDivisionError as e:
                                print("length: {}, period: {}, Error: {}".format(self.q.qsize(), period, e))
                    else:
                        try:
                            self.q.put(line)
                        except queue.Full:
                            print("Очередь заполнена")

                    prevDelta = curDelta
                except Exception as e:
                    print('Error reading/decoding line: ', e)

    def write(self, endTime, startTime):
        period = (endTime - startTime) / self.q.qsize()
        stampTime = startTime

        while not self.q.full():
            line = self.q.get()  # тут будут проблемы с локингом треда который нельзя локать
            stampTime += period
            line = str(stampTime) + " " + line
            line = line.rstrip() + '\n'
            # в поле
            if self.toField:
                self.txt.insert(tkinter.INSERT, line)
                self.txt.see(tkinter.END)  # перемотка в конец
            # в файл
            if self.toFile:
                try:
                    self.file.write(line)
                except Exception as e:
                    print('Error writing to file: ', e)
        # для дебага
        if self.toFile:
            try:
                self.file.write("\n***********_{}_**********\n".format(self.l))
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
                                                "Найдено несколько Arduino \nУкажите номер Arduino, который следует использовать",
                                                initialvalue=0)
                    result = arduinos[i]
                except ValueError:
                    messagebox.showerror("Ошибка", "Должно быть введено число")
        if len(arduinos) == 1:
            result = arduinos[0].name
        if len(arduinos) == 0:
            result = None
            if ports:
                crutch = True
                while (crutch):
                    result = simpledialog.askstring("Арргх",
                                                    "Укажите какой порт использовать использовать\nНапример: COM5",
                                                    initialvalue=ports[0])
                    if (result[0:3] == 'COM' and result[3].isdigit()):
                        crutch = False
        return result

    def run(self, event):
        p = self._checkSerialPorts()
        if p is not None:
            try:
                self.ser = serial.Serial(port=p, baudrate=self.baud)
                self.txt.insert(tkinter.INSERT, "\nПодключено к: {}\n".format(self.ser.portstr))
            except serial.SerialException as e:
                self.txt.insert(tkinter.INSERT, 'Could not open serial port: {}\n'.format(e))
                return
            if self.toFile:
                try:
                    self.file = open("Data_{}.txt".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S")), "w")
                    self.file.write(__file__ + '\n')
                    self.txt.insert(tkinter.INSERT, "Запись в файл {} ...\n".format(self.file.name))

                except OSError as e:
                    self.txt.insert(tkinter.INSERT, 'open() or file.__enter__() failed \n', e)
                    self.toFile = False
                self.q.queue.clear()

            # а жив ли поточек?
            thread_alive = True
            if self.serialThread == None:
                thread_alive = False
            elif not self.serialThread.is_alive():
                thread_alive = False

            if thread_alive == False:
                """крафтим тред"""
                try:
                    self._stopFlag = False
                    self.serialThread = threading.Thread(target=self._serialThread, daemon=True, name="reader_thread")
                    self.serialThread.start()
                    self.txt.insert(tkinter.INSERT, "\nОткрыт поток\n")
                    self.buttonstart.config(state=tkinter.DISABLED)
                except Exception as e:
                    self.txt.insert(tkinter.INSERT, 'Невозможно запустить поток \n', e)
        else:
            self.txt.insert(tkinter.INSERT, "Не найдено arduino\n")
        self.txt.see(tkinter.END)  # перемотка в конец

    def stopThread(self):
        self._stopFlag = True
        self._killFlag = True

    def close(self):
        self._stopFlag = True
        self.buttonstart.config(state=tkinter.NORMAL)
        try:
            self.stopThread()
            self.file = None
            self.txt.insert(tkinter.INSERT, "\nЗакрыт поток")
        except:
            self.txt.insert(tkinter.INSERT, "\nНет потока")
        try:
            self.ser.close()
            self.txt.insert(tkinter.INSERT, "\nЗакрыт слушатель\n")
        except:
            self.txt.insert(tkinter.INSERT, "\nНет слушателя")

    def pause(self):
        self.toField = not self.toField

    def on_closing(self):
        self.close()
        self.root.quit()
        self.root.destroy()


listener = listener(True, False)
