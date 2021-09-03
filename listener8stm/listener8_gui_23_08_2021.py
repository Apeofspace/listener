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
    def __init__(self, msgqueue, max_lines=100):
        self.messagequeue = msgqueue
        self.max_lines = max_lines
        self._stopflag = False
        # ткинтер
        self.root = tkinter.Tk()
        self.root.title("LIR Listener")
        # лейбл
        self.label = tkinter.Label(self.root, text="360", font=("Arial Bold", 50))
        self.label.pack()
        # текст
        self.frametxt = tkinter.Frame(self.root)
        self.frametxt.pack(expand=True, fill='both', side='left')
        self.txt = scrolledtext.ScrolledText(self.frametxt, height=20, width=100)
        self.txt.pack(fill='both', expand=True)
        self.txt.configure(state='disabled')
        # кнопки
        self.framebuttons = tkinter.Frame(self.root)
        self.framebuttons.pack(side='right')
        self.buttonstart = tkinter.Button(self.framebuttons, text="Старт")
        self.buttonstart.pack(side='top')
        self.buttonstart.bind('<Button-1>', self.start)
        self.buttonstart.bind('<Return>', self.start)  # что бы ентер работал тоже
        self.buttonstart.focus_set()
        # self.buttonpause = tkinter.Button(self.framebuttons, text="Пауза", command=self.pause)
        # self.buttonpause.pack(side='top')
        # self.buttonstop = tkinter.Button(self.framebuttons, text="Стоп", command=self.close)
        # self.buttonstop.pack(side='top')
        # пуск
        self.guithread = Thread(target=self._guithread, daemon=True, name='gui_thread')
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # self.root.mainloop()

    def start(self, event):
        try:
            if not self.guithread.is_alive():
                self.guithread.start()
                # костыльно
                exporter.start()
                listener.start()
        except Exception as e:
            self.messagequeue.put("MSG", e)
        # while not self.guithread.is_alive():
        #     pass

    def stop(self):
        self._stopflag = True

    def _guithread(self):
        lines = 0
        while True:
            if self._stopflag:
                break
            msg = self.messagequeue.get()
            if msg is not None:
                try:
                    keys = msg.keys()
                    self.txt.configure(state='normal')
                    if "MSG" in keys:
                        self.txt.insert(tkinter.END, msg["MSG"])
                        self.txt.insert(tkinter.END, '\n')
                        lines += 1
                    if "VAL" in keys:
                        self.label.configure(text=msg["VAL"][2])
                    if "ERR" in keys:
                        self.txt.insert(tkinter.END, msg["ERR"])
                        self.txt.insert(tkinter.END, '\n')
                        lines += 1
                    if lines > self.max_lines:
                        self.txt.delete(1.0, tkinter.END)
                        lines = 0
                    self.txt.configure(state='disabled')
                except Exception as e:
                    self.txt.insert(tkinter.END, e)
                    self.txt.insert(tkinter.END, '\n')
                finally:
                    self.txt.configure(state='disabled')
                    self.messagequeue.task_done()

    def on_closing(self):
        self.messagequeue.put("MSG", 'Остановка...')
        self.stop()
        listener.stop()
        exporter.stop()
        # while exporter.is_alive() or listener.is_alive():
        #     pass
        self.root.quit()
        self.root.destroy()


class listenerThread(Thread):
    # Можно сделать, чтобы он принимал не одну queue, а список. и писал в каждую из них,
    # для того, чтобы можно было сделать такое же количество тредов для записи
    def __init__(self, queue, msgqueue, updateperiod=500, baud=500000):
        self.queue = queue
        self.updateperiod = updateperiod
        self.messagequeue = msgqueue
        self._stopflag = True
        self.baud = baud  # doesn't matter for vCOM
        # Connect to COM
        p = self.autoFindSerialPort()
        if p is not None and p != 0:
            try:
                self.ser = serial.Serial(port=p, baudrate=self.baud)
                self.messagequeue.put({"MSG": "Подключено к: {}".format(self.ser.portstr)})
                # Start thread
                super().__init__(daemon=True, name='listener_thread')
            except serial.SerialException as e:
                self.messagequeue.put({"ERR": 'Не удалось подключиться к порту: {}\n'.format(e)})
                return

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
                result = simpledialog.askstring("Подключение COM",
                                                "Укажите какой порт использовать использовать\nНапример: COM5\n",
                                                initialvalue=ports[0])
                if result == None:
                    self.messagequeue.put({"ERR": 'Отмена...'})
                    return 0
                if result[0:3] == 'COM' and result[3].isdigit():
                    return result
        self.messagequeue.put({"ERR": 'Не найдено COM'})
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
                    counter += 1
                    if counter > self.updateperiod:
                        # self.messagequeue.put({"VAL": data})
                        # костыльно
                        guiwrap.label.configure(text=data[2])
                except Full:
                    self.messagequeue.put({"ERR": "Очередь полна, что-то пошло не так! Закрыть поток!"})
                    self.stop()
            except Exception as e:
                self.messagequeue.put({"ERR": 'Error reading/decoding line: {}'.format(e)})


class exportThread(Thread):
    # Parent class
    def __init__(self, queue, msgq):
        self.queue = queue
        self.messagequeue = msgq
        self._stopflag = False
        # Start thread
        super().__init__(daemon=True, name='export_thread')

    def stop(self):
        self._stopflag = True


class exportExcelThread(exportThread):
    def __init__(self, queue, msgq):
        self.filename = "Data_{}.xlsx".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S"))
        self.workbook = xlsxwriter.Workbook(self.filename)
        self.worksheet = self.workbook.add_worksheet()
        self.worksheet.write('A1', 'Count')
        self.worksheet.write('B1', 'Time (microseconds)')
        self.worksheet.write('C1', 'Value')
        super().__init__(queue, msgq)

    def run(self):
        self.messagequeue.put({"MSG": 'Запись в файл: {}'.format(self.filename)})
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
msgq = Queue()
guiwrap = GUIwrap(msgq)
listener = listenerThread(q, msgq, updateperiod=100)
exporter = exportExcelThread(q, msgq)
guiwrap.root.mainloop()
