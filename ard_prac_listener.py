import serial
import serial.tools.list_ports
import threading
import datetime
from time import sleep, perf_counter
from tkinter import  simpledialog, messagebox

class listener:
    def __init__(self, toFile=True, tograph=False, baud=230400):
        self.serialThread = None
        self._stopflag = True
        self.toFile = toFile
        self.tograph = tograph
        self.baud = baud
        self.file = None

    def checkSerialPorts(self):
        stms =[]
        ports = list(serial.tools.list_ports.comports())
        print("Поиск COM портов")
        for p in ports:
            print(" - " +p.description)
            if "Uno" in p.description:
                stms.append(p)
        if len(stms)==1:
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
        # Подключить СОМ
        p = self.checkSerialPorts()
        if p is not None:
            try:
                self.ser = serial.Serial(port=p, baudrate=self.baud)
                print("Подключено к: {}".format(self.ser.portstr))
            except serial.SerialException as e:
                print('Не удалось подключиться к порту: {}\n'.format(e))
                return
        # Открыть файл для записи
        if self.toFile:
            try:
                self.file = open("Data_{}.txt".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S")), "w")
                self.file.write(__file__ + '\n')
                # self.file.write('sdfsd')
                print("Запись в файл {} ...\n".format(self.file.name))
            except OSError as e:
                print('open() or file.__enter__() failed \n', e)
                self.toFile = False
        # Запустить поток
        try:
            #Проверка не запущено ли уже
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
        self.file.close()
        self.ser.close()
        #дописать проверку сериал через вайл и закрыть его когда тред закрыт, и файл тоже
        # возвращать 0 или 1 и по 1 закрывать всю прогу

    def _serialThread(self):
        # Просто читаю ВКОМ последовательно и пишу в файл без буферов и тп
        self._stopflag = False
        line = ''
        count = 0
        starttime = 0
        previoustime = 0
        currenttime =0
        deltat = 0
        deltatthou = 0
        while True:
            if self._stopflag:
                break
            try:
                line = self.ser.readline()
                curtime = perf_counter()
                if count == 0:
                    starttime = curtime
                deltat = curtime-previoustime
                previoustime = curtime
                count += 1
                line = line.decode('ascii')
                line = str(count) + ": DeltaT "+ str(deltat)+ "  " +line
                # print(line)
                self.buffer(line)
                if count > 999:
                    deltatthou = curtime - starttime
                    count = 0
                    starttime = 0
                    self.buffer("************ "+ str(deltatthou)+" ************\n\n")
            except Exception as e:
                print('Error reading/decoding line: ', e)


    def buffer(self,line):
        self.write(line)

    def write(self, line):
        try:
            self.file.write(line)
        except Exception as e:
            print('Error writing to file: ', e)


listener = listener(True, False, 115200)
listener.run()
curt = 0
# for i in range(1000):
#     prt = curt
#     sleep(1)
#     curt = perf_counter()
#     print((curt-prt))
input()
listener.stop()
