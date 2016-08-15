import socket, time, colorsys, math
from collections import namedtuple
from enum import Enum
from threading import Thread

FADE_QUALITY = 15

# Tuple (ip, port)
CONTROLLER = None

class Command():
    def __init__(self, values):
        if type(values) is list or type(values) is tuple:
            self.values = values
        else:
            self.values = [values]

COMMANDS = {
    "ON": (
            Command(0x42),
            Command(0x45),
            Command(0x47),
            Command(0x49),
            Command(0x4B)
        ),
    "OFF": (
            Command(0x41),
            Command(0x46),
            Command(0x48),
            Command(0x4A),
            Command(0x4C)
    ),
    "WHITE": (
            Command(0xC2),
            Command(0xC5),
            Command(0xC7),
            Command(0xC9),
            Command(0xCB)
    ),
    "NIGHT": (
            Command(0xC1),
            Command(0xC6),
            Command(0xC8),
            Command(0xCA),
            Command(0xCC),
    ),
    "PARTY": Command(0x4D),
    "SLOWER": Command(0x43),
    "FASTER": Command(0x44),
}

PARTY_MODES = {
    "white": 0,
    "rainbow_fade": 1,
    "white_fade": 2,
    "rgbw_fade": 3,
    "rainbow_fast": 4,
    "random": 5,
    "red_flash": 6,
    "green_flash": 7,
    "blue_flash": 8
}

class LightState(Enum):
    color, white, night, party = range(4)

class Light():
    def __init__(self, on, state, color, brightness, partyMode, effectThread):
        self.on = on
        self.state = state
        self.color = color
        self.brightness = brightness
        self.partyMode = partyMode
        self.effectThread = effectThread

# A light where when one of its attributes is set, it sets that same attribute value for all lights
class AllLight(Light):
    def __setattr__(self, name, value):
        self.__dict__[name] = value
        for l in lights:
            if not l is self:
                setattr(l, name, value)

Color = namedtuple("Color", "r g b")
def _lerp(t, a, b):
    return (1 - t) * a + t * b

def _lerp_color(t, a, b):
    return Color(*[((1 - t) * a[i] + t * b[i]) for i in range(0, 3)])

def _color_from_hex(string):
    if "#" in string:
        string = string[1:]
    return Color(*[c for c in bytes.fromhex(string)])

def _hex_from_color(color):
    return "#{0:02x}{1:02x}{2:02x}".format(int(color.r), int(color.g), int(color.b))

class EffectThread():
    commandLock = False

    def __init__(self):
        self.stop = False

    def wait_and_lock(self):
        while EffectThread.commandLock:
            time.sleep(.05)
        if not EffectThread.commandLock:
            EffectThread.commandLock = True

    def unlock(self):
        EffectThread.commandLock = False

    def start(self, effect, effectTime):
        for (f, args, kwargs) in effect.do():
            self.wait_and_lock()
            f(*args, **kwargs)
            self.unlock()
            time.sleep(effectTime / len(effect))

            if self.stop:
                break

# The Effect's 'do' method is a generator that will generate tuples of (function, args, kwargs)
class Effect():
    def __init__(self, light):
        self.light = light

    def do(self):
        raise NotImplementedError("Implement this in a subclass!")

class Fade(Effect):
    def __init__(self, light, initial, to, quality):
        self.light, self.initial, self.to, self.quality = light, initial, to, quality

    def __len__(self):
        return self.quality

class FadeToColor(Fade):
    def do(self):
        self.initial = _color_from_hex(self.initial)
        self.to = _color_from_hex(self.to)
        for i in range(self.quality):
            yield((color, [_hex_from_color(_lerp_color(i / self.quality, self.initial, self.to))], {"light": self.light}))
        yield((color, [_hex_from_color(self.to)], {"light": self.light}))

class FadeToBrightness(Fade):
    def do(self):
        for i in range(self.quality):
            yield((brightness, [_lerp(i / self.quality, self.initial, self.to)], {"light": self.light}))
        yield((brightness, [self.to], {"light": self.light}))    

def __start_effect(effect, effectTime):
    # Stop any effects currently running on this light
    if not lights[effect.light].effectThread is None:
        lights[effect.light].effectThread.stop = True

    e = EffectThread()
    lights[effect.light].effectThread = e
    Thread(target=e.start, args=(effect, effectTime)).start()

def __send_data(data):
    global lastCommand

    # Ensure that there have been at least 100ms between this command and the last one sent
    if time.time() - .1 < lastCommand: 
        time.sleep(.1 - (time.time() - lastCommand))
    lastCommand = time.time()

    controllerSocket.sendto(data, CONTROLLER)

def __get_extension(commandLen):
    return [0x00, 0x55] if commandLen == 1 else [0x55]

def __select_light(light):
    global selectedLight
    if selectedLight == light:
        return

    selectedLight = light
    __send_data(bytes((COMMANDS["ON"][light].values[0], 0x00, 0x55)))

def __send_command(light, command):
    # The select command is the on command, so if we're turning on a light then we just select it
    if command in COMMANDS["ON"]:
        __select_light(light)
        return

    __send_data(bytes((*command.values, *__get_extension(len(command.values)))))

# rgb should be in the format "#xxxxxx"
def __rgb_to_hue(rgb):
    if "#" in rgb:
        rgb = rgb[1:]

    # Convert the hex string to RGB values to HLS values
    hls = colorsys.rgb_to_hls(*[c / 255.0 for c in bytes.fromhex(rgb)])

    # The light color wheel is an inverted color wheel translated by 2/3 with degrees 0-255
    # Take colors that are very bright or very dark and turn the light on or off respectively
    if hls[1] > 0.95:
        return 256
    elif hls[1] < 0.05:
        return -1
    else:
        return int(math.floor(((-hls[0] + 1 + (2.0 / 3.0)) % 1) * 256))

def brightness(brightness, light=0):
    if brightness < 0.0 or brightness > 1.0:
        raise Exception("Brightness must be between 0.0 and 1.0")

    # Brightness ranges between 0x02 and 0x27, so scale (0, 1) to (2, 27)
    __select_light(light)
    __send_data(bytes((0x4E, 2 + int(25 * brightness), *__get_extension(2))))
    lights[light].brightness = brightness

# Color should be in the format "#xxxxxx"
def color(color, light=0):
    hue = __rgb_to_hue(color)
    if hue == 256:
        white(light)
    elif hue == -1:
        off(light)
    else:
        __select_light(light)
        __send_data(bytes((0x40, __rgb_to_hue(color), *__get_extension(2))))
        lights[light].color = color
        lights[light].state = LightState.color
        lights[light].on = True

def on(light=0):
    __send_command(light, COMMANDS["ON"][light])
    lights[light].on = True

def off(light=0):
    __send_command(light, COMMANDS["OFF"][light])
    lights[light].on = False

def white(light=0):
    __send_command(light, COMMANDS["WHITE"][light])
    lights[light].state = LightState.white
    lights[light].color = "#FFFFFF"
    lights[light].brightness = 1.0
    lights[light].on = True

def party(mode, light=0):
    if not mode in PARTY_MODES:
        raise Exception("{} is not a valid party mode!".format(mode))

    # To select a specific party mode, it has to be selected from the order of modes
    # Also start with white or else previous party offsets will affect new parties
    white(light)
    for i in range(0, PARTY_MODES[mode]):
        __send_command(light, COMMANDS["PARTY"])
    lights[light].state = LightState.party
    lights[light].on = True
    lights[light].partyMode = mode

def faster(light=0):
    __send_command(light, COMMANDS["FASTER"])

def slower(light=0):
    __send_command(light, COMMANDS["SLOWER"])

def night(light=0):
    off(light)
    __send_data(bytes((COMMANDS["NIGHT"][light].values[0], *__get_extension(1))))
    lights[light].state = LightState.night
    lights[light].on = True

def run_effect(effect, time):
    __start_effect(effect, time)

def fade_to_color(color, time, light=0):
    __start_effect(FadeToColor(light, get_color(light), color, time * FADE_QUALITY), time)

def fade_to_brightness(brightness, time, light=0):
    __start_effect(FadeToBrightness(light, get_brightness(light), brightness, time * FADE_QUALITY), time)

def get_color(light=0):
    return lights[light].color

def get_brightness(light=0):
    return lights[light].brightness

def is_on(light=0):
    return lights[light].on

def get_party(light=0):
    return lights[light].state == LightState.party

def get_night(light=0):
    return lights[light].state == LightState.night

def get_white(light=0):
    return lights[light].state == LightState.white

def get_party_mode(light=0):
    return lights[light].partyMode

def init(ip, port=8899):
    global CONTROLLER, controllerSocket, selectedLight, lastCommand, lights
    CONTROLLER = (ip, port)
    controllerSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    selectedLight = -1
    lastCommand = time.time()

    lights = list()
    lights.append(AllLight(True, LightState.white, "#FFFFFF", 1.0, "white", None))
    lights.extend([Light(True, LightState.white, "#FFFFFF", 1.0, "white", None) for i in range(4)])

def destroy():
    controllerSocket.close()