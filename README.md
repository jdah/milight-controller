## [milight-controller](https://github.com/jdah/milight-controller) 
Controller for MiLight RGB lights. Written for Python.

## Features
* Control RGB MiLight LED lights
* Extensible 'Effect' class for custom effects
* Mutlithreaded, so nothing blocks
* Keeps track of light states so that color, brightness, etc. can be queried

# Installation
```sh
pip install milight-controller
```

# Usage
```python
from milight_controller import milight

# Control fade quality for fade effect
# Nothing above 15 tends to make a difference in quality.
milight.FADE_QUALITY = 15

# Must be done before running any commands
# Specify a port with 'milight.init(<ip>, port=6666)'
milight.init("192.168.1.100")

# ALL commands have the 'light=0' default parameter. 0 means all lights.
# Setting 'light' to 1-4 specifies the group of lights that will be sent the command.

milight.brightness(0.5) # Set all lights to half brightness
milight.brightness(0.75, 1) # Set all lights in group 1 to 3/4 brightness

milight.color("#FF00FF") # Set all lights to pink

# Turn group 1 lights on and off
milight.on(1)
milight.off(1)

# Make all lights white (max color and brightess)
milight.white()

# Party! Specify mode the mode and group
# Available modes (in milight.PARTY MODES):
#   white
#   rainbow_fade
#   white_fade
#   rgbw_fade
#   rainbow_fast
#   random
#   red_flash
#   green_flash
#   blue_flash
milight.party("rainbow_fade")

# Make party effects faster or slower (Doesn't apply to effect threads)
milight.faster()
milight.slower()

# Switches lights into night mode
milight.night()

# Custom effect! This is *not* a part of the standard milight controller command palette.
# Fade from one color to another using linear interpolation of HSV values.
milght.fade_to_color("#FF0000", 10)  # Fade to red and take 10 seconds

# Same as above, but with brightness
milight.fade_to_brightness(0.25, 5)

# Getters! This library keeps track of all light states.
milight.get_color()         # Returns light color in #RRGGBB format
milight.get_brightness()    # Returns light brightness on [0.0, 1.0]
milight.is_on()             # True if light is on
milight.get_party()         # True if light if partying
milight.get_night()         # True if light is in night mode
milight.get_white()         # True if light is in white mode
milight.get_party_mode()    # Party mode string from milight.PARTY_MODES

# Can extend the milight.Effect class for custom effects.
# These effects run on their own threads so as not to interfere with regular application flow

# All effects have only 1 parameter:
#   light - The light group that they apply to. Use '0' for all lights.
class BeatDrop(milight.Effect):
    def __init__(self, light, quality):
        self.light, self.quality = light, quality

    # Override the 'do' method to implement the custom effect
    # This is a generator, so you yield tuples of functions to call and their respective arguments as (function, args, kwargs)
    def do(self):
        for i in range(self.quality * 2):
            yield((brightness, [0.0], {light: self.light}))
            yield((brightness, [1.0], {light: self.light}))

# Now call the BeatDrop effect for 10 seconds with a quality of 20 to get 20 brightness flashes in 10 seconds
milight.run_effect(BeatDrop(0, 20))

# Close the connection to the controller
milight.destroy()
```