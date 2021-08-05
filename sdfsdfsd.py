from time import sleep, perf_counter

t1 = perf_counter()
t2 = 0
dt = 0
for i in range(10000):
    sleep(0.0001)
    t2 = perf_counter()
    dt = t2-t1
    t1 = t2
    print(dt)
