import queue

import serial
import serial.tools.list_ports
from queue import Queue
import threading
import datetime
from time import perf_counter

class listener:
    def __init__(self, queue, baud=500000, test = True):
        self.test = test
        self.queue = queue
        self.serialThread = None
        self._stopflag = True
        self.baud = baud

    def checkSerialPorts(self):
        stms = []
        ports = list(serial.tools.list_ports.comports())
        print("Поиск COM портов")
        for p in ports:
            print(" - " + p.description)
            if "STMicroelectronics Virtual COM Port" in p.description:
                stms.append(p)
        if len(stms) == 1:
            print("Автоподключение " + stms[0].name)
            return stms[0].name
        if ports:
            while (True):
                result = input("Укажите какой порт использовать использовать\nНапример: COM5\n")
                if (result[0:3] == 'COM' and result[3].isdigit()):
                    return result
        print('Не найдено COM')
        return 0

    def run(self):
        # Connect to COM
        p = self.checkSerialPorts()
        if p is not None:
            try:
                self.ser = serial.Serial(port=p, baudrate=self.baud)
                print("Подключено к: {}".format(self.ser.portstr))
            except serial.SerialException as e:
                print('Не удалось подключиться к порту: {}\n'.format(e))
                return
        #Start thread
        try:
            # Does thread exist already?
            if self.serialThread == None or not self.serialThread.is_alive():
                self.serialThread = threading.Thread(target=self._serialThread, daemon=True, name="reader_thread")
                self.serialThread.start()
                print("Поток запущен")
        except Exception as e:
            print('Невозможно запустить поток: ', e)

    def stop(self):
        self._stopflag = True
        while (self.serialThread.is_alive()):
            pass
        self.ser.close()

    def _serialThread(self):
        # Read COM, put to Queue
        self._stopflag = False
        previoustime = perf_counter()
        while True:
            if self._stopflag:
                break
            try:
                line = self.ser.read_until(size=12, expected=b'\xfa\xfb\xfc\xfd')
                # timestamp
                curtime = perf_counter()
                deltat = curtime - previoustime
                previoustime = curtime
                #Order: count, time, value
                data = [(int.from_bytes(line[:2], "little")), (int.from_bytes(line[4:8], "little")), (int.from_bytes(line[4:8], "little"))]
                self.queue.put(data)
            except Exception as e:
                print('Error reading/decoding line: ', e)


class exporterExcel:
    

q = Queue()
