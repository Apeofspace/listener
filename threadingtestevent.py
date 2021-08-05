import threading


def worker(i):
    print(i)
    event.wait()
    print(i)

event = threading.Event()
tat = []
for z in range(4):
    # t = threading.Thread(target= (lambda: worker(z)), daemon=True
    t = threading.Thread(target=worker(z), daemon=True)
    # t = threading.Thread(target=worker, args = (4), daemon=True)
    # t = threading.Thread(target=(lambda a: worker(a)), args=(z), daemon=True)
    t.start()
    tat.append(t)
event.set()
