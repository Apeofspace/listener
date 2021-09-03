import serial
import serial.tools.list_ports
from queue import Queue, Full
from threading import Thread
from time import perf_counter
import xlsxwriter
import datetime


class listenerThread(Thread):
    # Можно сделать, чтобы он принимал не одну queue, а список. и писал в каждую из них,
    # для того, чтобы можно было сделать такое же количество тредов для записи,
    # хотя это немного костыльно
    def __init__(self, queue, baud=500000):
        self.queue = queue
        self._stopflag = True
        self.baud = baud  # doesn't matter for vCOM
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
        super().__init__(daemon=True, name='listener_thread')

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

    def run(self):
        # Read COM, put to Queue
        self._stopflag = False
        # previoustime = perf_counter()
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
                try:
                    self.queue.put(data, block=True, timeout=0.5)
                except Full:
                    print("Очередь полна, что-то пошло не так! Закрыть поток!")
                    self.stop()
            except Exception as e:
                print('Error reading/decoding line: ', e)


class exportThread(Thread):
    # Parent class
    def __init__(self, queue):
        self.queue = queue
        self._stopflag = False
        self.filename = None
        # Start thread
        super().__init__(daemon=True, name='export_thread')

    def stop(self):
        self._stopflag = True

    # def filename(self):
    #     return self.filename()


class exportExcelThread(exportThread):
    def run(self):
        self.filename = "Data_{}.xlsx".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S"))
        self.workbook = xlsxwriter.Workbook(self.filename)
        self.worksheet = self.workbook.add_worksheet()
        self.worksheet.write('A1', 'Count')
        self.worksheet.write('B1', 'Time (microseconds)')
        self.worksheet.write('C1', 'Value')
        row = 1
        while True:
            if self._stopflag:
                break
            column = 0
            for item in self.queue.get():
                self.worksheet.write(row, column, item)
                column += 1
            row += 1  # не возникнет ли проблем при больших числах?
            self.queue.task_done()

    def stop(self):
        super().stop()
        self.workbook.close()


q = Queue(maxsize=100000)
listener = listenerThread(q)
exporter = exportExcelThread(q)
listener.start()
exporter.start()
print('Запись в файл: {}'.format(exporter.filename))
print('Потоки запущены. Нажмите любую клавишу для остановки...')
input()
print('Остановка...')
listener.stop()
exporter.stop()
while (exporter.is_alive() or listener.is_alive()):
    pass
