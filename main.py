import uasyncio as asyncio
from threadsafe import ThreadSafeQueue
from machine import Pin
from ir_rx.nec import NEC_16
import time
import network
from wifiinfo import SSID, PWD
from phew import server, connect_to_wifi
import rp2

class Cx50:
    def __init__(self):
        rp2.country('DE')
        self.led = Pin("LED", Pin.OUT)
        network.hostname("cx50")
        connect_to_wifi(SSID, PWD)
        self.blinken = True
        self.last_command = ""
        self.volume = 63

    def ir_callback(self, data, addr, ctrl, qu):  # Runs in ISR context
        if not qu.full():
            qu.put_sync((data, addr))

    async def ir_receiver(self, q):
        async for data in q:  # Task pauses here until data arrives
            if data[0] >= 0:
            #if True:
                #print(f"Received data {data[0]} address {data[1]}")
                #print('Data {:02x} Addr {:04x}'.format(data[0], data[1]))
                #print(data[0])
                if int(data[0]) == 26 and int(data[1]) == 122:
                    self.last_command = "vol_up"
                    await self.set_volume(-1)
                elif int(data[0]) == 27 and int(data[1]) == 122:
                    self.last_command = "vol_down"
                    await self.set_volume(1)
                else:
                    self.last_command = ""
            else:
                #print(f"Received data {data[0]} address {data[1]}")
                if self.last_command == "vol_up":
                    await self.set_volume(-1)
                elif self.last_command == "vol_down":
                    await self.set_volume(1)

    async def set_volume(self, vol):
        self.volume = self.volume + vol
        print(self.volume)

    async def ir_remote(self):
        q = ThreadSafeQueue([0 for _ in range(20)])
        ir = NEC_16(Pin(16, Pin.IN), self.ir_callback, q)
        await self.ir_receiver(q)

    async def blinki(self):
        while True:
            if self.blinken == True:
                self.led.toggle()
            await asyncio.sleep(1)

    async def restapi(self):
        server.run()




async def app() -> None:
    cx50 = Cx50()
    @server.route("/on", methods=["GET"])
    def led_on(request):
        cx50.blinken = False
        cx50.led.on()
        return "on"

    @server.route("/off", methods=["GET"])
    def led_off(request):
        cx50.blinken = False
        cx50.led.off()
        return "off"

    @server.route("/blinken", methods=["GET"])
    def led_blinken(request):
        cx50.blinken = True
        return "blinken"

    @server.catchall()
    def catchall(self, request):
        return "Not found", 404
    try:
        await asyncio.gather(cx50.blinki(), cx50.ir_remote(), cx50.restapi())
    except KeyboardInterrupt:
        print("Terminating. CU!")
        network.close()

if __name__ == "__main__":
    asyncio.run(app())

