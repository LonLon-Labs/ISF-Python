"""dirtools: a pure-Python re-implementation of the parts of ProjectorRays and Director Cast Ripper that the
I SPY port needs, so the first-run setup works anywhere Python and pygame do (Windows x86_64/ARM, macOS Intel and
Apple Silicon, Linux) instead of needing the Windows-only tools.

    dirtools.stream      binary reader
    dirtools.container   Director movie / cast file reader (RIFX / XFIR, memory map and Afterburner)
    dirtools.lingo_*     Lingo bytecode decompiler (port of ProjectorRays' lingodec)
    dirtools.media       bitmap -> PNG and sound -> WAV conversion
    dirtools.ripper      the export driver (what Cast Ripper + ProjectorRays did for the launcher)

container.py and lingo_*.py are translations of ProjectorRays source files (Mozilla Public License 2.0), so they
stay under that license. Director Cast Ripper (MIT) was only used as a behavioural reference for file naming
and the CSV formats.
"""
