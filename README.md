# TCG Pocket Tracker

Simple project to track the collection inside TCG Pocket.
Works with:
- A3a. Extradimensional Crisis
- A3. Celestial Guardians
- A2b. Shining Revelry
- A2a. Triumphant Light
- A2. Space-Time Smackdown
- A1a. Mythical Island
- A1. Genetic Apex

## Roadmap

- Tool to update new sets into the format required
- Porting GUI to PySide6 including:
    - Dark Mode
    - Better Plotting
- Profile account for saves
    - Create a tool that puts previous saves in a profile for retro-compatibility
- Improve img fetching:
    - Make local image fetch consistent after pyinstaller
    - Implement web fetching that doesn't crash due to overload

### Done

- Changing from Pandas to **Polars**
- Getting to plot images 
    - Plot in black and white if it's unchecked, color otherwise. (Last release not working for some reason)
- ~~Tabs working properly.~~ Change tabs for checkbox
- Refined the probability function (Now works with all sets).
- Implement new sets.
