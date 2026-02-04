import pyfirmata
import inspect
import time

if not hasattr(inspect, 'getargspec'):
        inspect.getargspec = inspect.getfullargspec
        
board = pyfirmata.Arduino('COM4')  
led_pines = [2, 3, 4, 5, 6, 7, 8, 9, 10]


for pin in led_pines:
    board.digital[pin].mode = pyfirmata.OUTPUT

def encender_led(x, y):
    # Enciende el LED correspondiente a la posición (x, y)
    led_index = x * 3 + y
    board.digital[led_pines[led_index]].write(1)

def parpadear():
    for _ in range(5):
        # Enciende todos los LEDs
        for pin in led_pines:
            board.digital[pin].write(1)
        time.sleep(0.5)  # Encendido durante 0.5 segundos

        # Apaga todos los LEDs
        for pin in led_pines:
            board.digital[pin].write(0)
        time.sleep(0.5)  # Apagado durante 0.5 segundos

def close_arduino():
    board.exit()
