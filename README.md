# demolition
This is a python project that simulates the demolition of a radiotower by imploding a certain configuration of hinges. 
The project has a manual mode (main_basic.py) and a genetic algorithm mode (main.py).
You may freely test these scripts on the `models/radio_tower/radio_tower2_final.blend` file.

## Usage
### Manual demolition
To simulate the manual demolitions as depicted in the report, you can open any of the `.blend` files in the `models/radio_tower/manual_demolitions` folder.
You should see 5 `.blend` files. Each of these correspond to the 5 manual simulated demolitions in the report.

To start the simulation, go to the Demolition tab on the toolbar at the left on the scene window (next to `Tool`, `View` and `Create`).
If it isn't there, go to the `scripting` tab, open `main_basic.py` and click `run script`. The demolition tab should now be visible.

In the demolition tab, click the button `Initialize`. This will assign  all the necessary physics properties to the objects in the scene.
After the script has finished running, and the button is no longer blue, click `start`. This will bake the physics for the next 100 frames and start the animation automatically when finished.
To view the output of the evaluation function, click `Stop` and go to `Window -> Toggle System Console`. This should show a console window with the radius, height, removed clusters and evaluation score printed on it.

### Genetic algorithm
...