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
The genetic algorithm is devoleped in the `main.py` file and should use the
model in the file `models/radio_tower/radio_tower2_final.blend`. Open the model
file in blender and go the _scripting_ tab. There you should open the `main.py`
file and click the _run script_ button. This will show you the demolition tab
in the scene window.

The demolition tab has 8 options/buttons. The first 4 options do not need to be
changed. But you may wish to alter the configurations.

- Breaking threshold : this defines the breaking threshold of the hinges in the
simulation.
- Substeps Per Frame : this defines the number of delta T time steps considered
in each simulation frame. Higher values make the simulation more accurate but
it also takes more time to compute.
- Solver Iterations : this defines the number of constraint solver iterations
made per simulation step. Higher values make the simulation more accurate but
it also takes more time to compute.
- Speed : this defines the speed up. 1 defines regular time, 2 defines a speed
up of 2.

The second 4 buttons perform the following actions:

- Genetic algorithm : this button will run 10 generation of the genetic
algorithm to see what is happening we advise you to open the Blender console.
- Genetic Round : this button will run a single generation of the genetic
algorithm  to see what is happening we advise you to open the Blender console.
- Run best model : this button will compute the simulation of the best model
in the current generation and thereafter start the simulation. _Note that_
_nothing will happen if you haven't executed at least one genetic round yet._
- Stop : this will freeze the simulation at the current point in time. Pressing
the 'Run best model' button again will continue the simulation.
