import serial
import serial.tools.list_ports
import threading
import datetime
from time import perf_counter


class listener:
    def __init__(self, toFile=True, tograph=False, baud=500000, test=False):
        self.serialThread = None
        self._stopflag = True
        self.toFile = toFile
        self.tograph = tograph
        self.baud = baud
        self.file = None
        self.test = test

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
            # Проверка не запущено ли уже
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
        # дописать проверку сериал через вайл и закрыть его когда тред закрыт, и файл тоже
        # возвращать 0 или 1 и по 1 закрывать всю прогу

    def _serialThread(self):
        # Просто читаю ВКОМ последовательно и пишу в файл без буферов и тп
        self._stopflag = False
        line = ''
        count = 0
        starttime = 0
        previoustime = 0
        while True:
            if self._stopflag:
                break
            try:
                line2 = ''
                line = self.ser.read_until(size=12, expected=b'\xfa\xfb\xfc\xfd')
                if self.test:
                    curtime = perf_counter()
                    if count == 0:
                        starttime = curtime
                    deltat = curtime - previoustime
                    previoustime = curtime
                    count += 1
                    # line2 = str(count) + ": Calculated deltaT : " +str(deltat)+ "  "
                    line2 = " ".join([str(count), ": Calculated deltaT :", str(deltat), " "])
                    # line2 = f"{str(count)} : Calculated deltaT : {str(deltat)} "
                    if count > 999:
                        deltatthou = curtime - starttime
                        count = 0
                        starttime = 0
                        # line3 = "****1000**** " + str(deltatthou) + " ************\n\n"
                        line3 = " ".join(["****1000****", str(deltatthou), "************\n\n"])
                        print(line3)
                        if self.toFile:
                            try:
                                self.write(line3)
                            except Exception as e:
                                print('Error writing to file: ', e)
                # line2 = ":".join("{:02x}".format(c) for c in line)
                # print(line2)
                # line2 = line2+ str(int.from_bytes(line[:2], "little")) + ": Time (us): " + str(int.from_bytes(line[4:8], "little")) + " Value: " + str(
                #     int.from_bytes(line[2:4], "little")) + "\n"  # вот это вот может сломаться
                line2 = " ".join([line2, str(int.from_bytes(line[:2], "little")), ": Time (us):", str(int.from_bytes(line[4:8], "little")), "Value:", str(int.from_bytes(line[2:4], "little")), "\n"])
                # line2 = f"{line2} {str(int.from_bytes(line[:2], 'little'))} : Time (us): {str(int.from_bytes(line[4:8], 'little'))} Value: {str(int.from_bytes(line[2:4], 'little'))} \n"
                # print(line2)
                if self.toFile:
                    try:
                        self.write(line2)
                    except Exception as e:
                        print('Error writing to file: ', e)
            except Exception as e:
                print('Error reading/decoding line: ', e)

    def write(self, line):
        try:
            self.file.write(line)
        except Exception as e:
            print('Error writing to file: ', e)


listener = listener(test=True)
listener.run()
input()
