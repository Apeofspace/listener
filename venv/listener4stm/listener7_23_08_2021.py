import serial
import serial.tools.list_ports
from queue import Queue
from threading import Thread
# import datetime
from time import perf_counter


class listenerThread(Thread):
    def __init__(self, queue, baud=500000):
        self.queue = queue
        self._stopflag = True
        self.baud = baud #doesn't matter for vCOM
        # Connect to COM
        p = self.autoFindSerialPort()
        if p is not None:
            try:
                self.ser = serial.Serial(port=p, baudrate=self.baud)
                print("Подключено к: {}".format(self.ser.portstr))
            except serial.SerialException as e:
                print('Не удалось подключиться к порту: {}\n'.format(e))
                return
        # Start thread
        super().__init__(target=self.loop, daemon=True, name='listener_thread')

    def autoFindSerialPort(self):
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

    def stop(self):
        self._stopflag = True

    def loop(self):
        # Read COM, put to Queue
        self._stopflag = False
        previoustime = perf_counter()
        while True:
            if self._stopflag:
                self.ser.close()
                break
            try:
                line = self.ser.read_until(size=12, expected=b'\xfa\xfb\xfc\xfd')
                # timestamp
                # curtime = perf_counter()
                # deltat = curtime - previoustime
                # previoustime = curtime
                # Order: count, time, value
                data = [(int.from_bytes(line[:2], "little")), (int.from_bytes(line[4:8], "little")),
                        (int.from_bytes(line[2:4], "little"))]
                self.queue.put(data)
            except Exception as e:
                print('Error reading/decoding line: ', e)


class exportThread(Thread):
    #Parent class
    def __init__(self, queue):
        self.queue = queue
        self._stopflag = False
        # Start thread
        super().__init__(target=self.loop, daemon=True, name='listener_thread')

    def loop(self):
        pass
         #Overwrite this in children

    def stop(self):
        self._stopflag = True


class exportExcelThread(exportThread):
    def loop(self):
        while True:
            if self._stopflag:
                break
            print(self.queue.get())
            self.queue.task_done()




q = Queue()
listener = listenerThread(q)
exporter = exportExcelThread(q)
listener.start()
exporter.start()
input()
