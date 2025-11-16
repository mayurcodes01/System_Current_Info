# FullInfo -- System Information Inspector (GUI)

FullInfo is a desktop application that displays detailed system
information through a clean and simple graphical interface. It can show
CPU, memory, disk, GPU, network data, uptime, and top processes. You can
also export the full system report to a text file.

The tool uses CustomTkinter when available and automatically falls back
to standard Tkinter if required.

## Key Features

### Complete System Overview

-   Username and hostname
-   Operating system and version
-   System architecture
-   Processor information
-   Python version
-   Boot time and system uptime

### CPU Details

-   CPU brand and architecture
-   Logical and physical core counts
-   Maximum frequency
-   Total CPU usage
-   Per-core usage

### Memory Information

-   Total, used, and available memory
-   Swap usage

### Disk Summary

-   Mounted partitions
-   Total, used, and free space
-   File system type
-   Disk I/O statistics

### Network

-   Local IP address
-   Network interfaces with details
-   Total data sent and received

### GPU (optional)

-   GPU name
-   Memory usage
-   Load percentage
-   Temperature (Available only if GPUtil is installed and supported
    GPUs are detected.)

### Top Processes

-   Lists the processes using the most CPU resources

### Export System Report

-   Save the complete report as a `.txt` file

## Requirements

Install the required Python packages before running the application:

    pip install psutil cpuinfo GPUtil customtkinter

## How to Run

1.  Save the script as `FullInfo.py`.
2.  Open a terminal in the script directory.
3.  Run:

```
    python FullInfo.py

## Notes

-   Works on Windows, Linux, and macOS.
-   CustomTkinter provides a modern UI, but the script also supports
    standard Tkinter.
-   GPU information requires GPUtil.
