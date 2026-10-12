# I Spy Fantasy: Python port

A port of the decompiled Lingo (Director 7) to Python + pygame. Parent scripts keep
their Lingo names (`mInit`, `mShow`, `mPlayDone`, ...) so each Python class can be diffed against its `.ls`.

This repo started as the I Spy Spooky Mansion Deluxe port and is being converted. The shared engine (runtime, sprites,
ink modes, audio, video, save system, launcher, extraction tools) carries over; the game logic is being re-ported from
I Spy Fantasy's own scripts.

## Run

### Automatically
Download the executable for your Operating System and CPU architecture in the [releases](/releases) tab.

Run the executable and select your legally obtained ISO file (first run only).

The game will automatically start.

### Manually
```
pip install pygame pycdlib
python -m launcher
```
Saves go to `%LOCALAPPDATA%\ISpyFantasyPort\SAVED GAMES\<player>\`.

## Status
Full game should be able to be completed.




## Legal Disclaimer
This project is a Python port of the original Lingo scripts from I Spy Fantasy.
It is intended strictly for educational, preservation, and compatibility purposes.
This repository does not contain any copyrighted game assets (art, audio, video, or data files),
which must be legally sourced by the user from an original ISO.

The authors of this port claim no ownership over the original game logic, scripts, or intellectual property.
All rights belong to their respective copyright holders.
