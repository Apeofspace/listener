# import multiprocessing
import serial
import serial.tools.list_ports
from multiprocessing import Process
import datetime
import time
from time import perf_counter


class listenerSerial(Process):
    def __init__(self, baudrate=500000):
        self.stopflag = False
        self.i = 0
        try:
            self.serial = serial.Serial(port=self.autoFindSerialPort(), baudrate=baudrate)
            print("Подключено к: {}".format(self.serial.portstr))
        except serial.SerialException as e:
            print('Не удалось подключиться к COM: {}\n'.format(e))
            return
        super().__init__(target=self.loop, daemon=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.serial.close()
        except Exception as e:
            print('Не удалось закрыть COM: {}\n'.format(e))

    def autoFindSerialPort(self, auto=True):
        stms = []
        ports = list(serial.tools.list_ports.comports())
        print("Поиск COM портов")
        for p in ports:
            print(" - " + p.description)
            if "STMicroelectronics Virtual COM Port" in p.description:
                stms.append(p)
        if (len(stms) == 1 and auto):
            print("Автоподключение " + stms[0].name)
            return stms[0].name
        if ports:
            while (True):
                result = input("Укажите какой порт использовать использовать\nНапример: COM5\n")
                if (result[0:3] == 'COM' and result[3].isdigit()):
                    return result
        print('Не найдено COM')
        return 0

    def loop(self):
        while (self.stopflag == False):
            self.i += 1
            print(self.i)
            time.sleep(0.25)

    def stop(self):
        self.stopflag = True


if __name__ == '__main__':
    # with listenerSerial() as listener1:
    #     listener1.start()
    #     pass
    l1 = listenerSerial()
    l1.start()

# def loop():
#     i = 0
#     while (True):
#         i+= 1
#         print(i)
#         time.sleep(0.25)

# listener1 = listenerSerial()
# listener1.start()
# input()
# listener1.stop()
# print("sucks")

# if __name__ == '__main__':
#     multiprocessing.freeze_support()
#     test1= Process(target = loop, daemon=True)
#     test2= Process(target = loop, daemon=True)
#     print(test1, test1.is_alive())
#     test1.start()
#     test1.join()
#     # time.sleep(0.5)
#     test2.start()
#     test2.join()
#     print(test1, test1.is_alive())
#     input()
#     print(test1, test1.is_alive())
