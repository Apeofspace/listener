from tkinter import simpledialog, scrolledtext

import serial
import serial.tools.list_ports
from queue import Queue, Full
from threading import Thread
from time import perf_counter
import xlsxwriter
import datetime
import tkinter


class GUIwrap:
    def __init__(self, msgqueue):
        self.messagequeue = msgqueue

        self.root = tkinter.Tk()
        self.root.title("LIR Listener")

        #лейбл
        self.label = tkinter.Label(self.root, text="360",font=("Arial Bold", 50)).pack()

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

        # self.buttonpause = tkinter.Button(self.framebuttons, text="Пауза", command=self.pause)
        # self.buttonpause.pack(side='top')
        # self.buttonstop = tkinter.Button(self.framebuttons, text="Стоп", command=self.close)
        # self.buttonstop.pack(side='top')
        # пуск
        self.guithread = Thread(target=self._guithread, daemon=True, name='gui_thread')
        # self.guithread.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def run(self, event):
        self.guithread.start()
        while not self.guithread.is_alive():
            pass
        exporter.start()
        listener.start()


    def _guithread(self):
        while True:
            msg = self.messagequeue.get()
            self.txt.insert(tkinter.INSERT, msg)
            self.txt.insert(tkinter.INSERT, '\n')
            self.messagequeue.task_done()

    def on_closing(self):
        self.messagequeue.put('Остановка...')
        listener.stop()
        exporter.stop()
        while exporter.is_alive() or listener.is_alive():
            pass
        self.root.quit()
        self.root.destroy()


class listenerThread(Thread):
    # Можно сделать, чтобы он принимал не одну queue, а список. и писал в каждую из них,
    # для того, чтобы можно было сделать такое же количество тредов для записи,
    # хотя это немного костыльно
    def __init__(self, queue, msgqueue, baud=500000):
        self.queue = queue
        self.messagequeue = msgqueue
        self._stopflag = True
        self.baud = baud  # doesn't matter for vCOM
        # Connect to COM
        p = self.autoFindSerialPort()
        if p is not None:
            try:
                self.ser = serial.Serial(port=p, baudrate=self.baud)
                self.messagequeue.put({"MSG": "Подключено к: {}".format(self.ser.portstr)})
            except serial.SerialException as e:
                self.messagequeue.put({"MSG": 'Не удалось подключиться к порту: {}\n'.format(e)})
                return
        # Start thread
        super().__init__(daemon=True, name='listener_thread')

    def autoFindSerialPort(self):
        stms = []
        ports = list(serial.tools.list_ports.comports())
        self.messagequeue.put({"MSG": "Поиск COM портов"})
        for p in ports:
            self.messagequeue.put({"MSG": " - {}".format(p.description)})
            if "STMicroelectronics Virtual COM Port" in p.description:
                stms.append(p)
        if len(stms) == 1:
            self.messagequeue.put({"MSG": "Автоподключение {}".format(stms[0].name)})
            return stms[0].name
        if ports:
            while True:
                result = simpledialog.askinteger("Подключение COM",
                                                 "Укажите какой порт использовать использовать\nНапример: COM5\n",
                                                 initialvalue=ports[0])
                if result[0:3] == 'COM' and result[3].isdigit():
                    return result
        self.messagequeue.put({"MSG": 'Не найдено COM'})
        return 0

    def stop(self):
        self._stopflag = True

    def run(self):
        # Read COM, put to Queue
        self._stopflag = False
        # previoustime = perf_counter()
        counter = 0
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
                    counter+=1
                    if counter > 500:
                        self.messagequeue.put({"VAL": data})
                except Full:
                    self.messagequeue.put({"ERR": "Очередь полна, что-то пошло не так! Закрыть поток!"})
                    self.stop()
            except Exception as e:
                self.messagequeue.put({"MSG":'Error reading/decoding line: {}'.format(e)})


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
    def __init__(self, queue):
        self.filename = "Data_{}.xlsx".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S"))
        self.workbook = xlsxwriter.Workbook(self.filename)
        self.worksheet = self.workbook.add_worksheet()
        self.worksheet.write('A1', 'Count')
        self.worksheet.write('B1', 'Time (microseconds)')
        self.worksheet.write('C1', 'Value')
        super().__init__(queue)

    def run(self):
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


# root = tk.Tk()
# root.title("LIR listener")
# label = tk.Label(root, text="360 00 00", font=("Arial Bold", 50)).grid()
# txt = scrolledtext.ScrolledText(root)
# txt.grid()


q = Queue(maxsize=100000)
msgq = Queue()
listener = listenerThread(q, msgq)
exporter = exportExcelThread(q)
guiwrap = GUIwrap(msgq)
listener.start()
exporter.start()
msgq.put({"MSG":'Запись в файл: {}'.format(exporter.filename)})
msgq.put({"MSG":'Потоки запущены. Нажмите любую клавишу для остановки...'})
# input()
# msgq.put('Остановка...')
# # print('Остановка...')
# listener.stop()
# exporter.stop()
# while(exporter.is_alive() or listener.is_alive()):
#     pass
