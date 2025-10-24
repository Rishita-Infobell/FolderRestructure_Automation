#  Folder Restructure Automation
## Overview

This project automates the process of converting unstructured raw data folders into a clean, well-defined structured directory format.
It’s built in Python and designed to help organize datasets or experiment outputs into a consistent hierarchy for easier access, analysis, or model training.

## Features

* Automatically identifies and categorizes files based on naming patterns and metadata
* Handles multiple SUT (System Under Test) or VM folders (e.g., VM1, VM2, etc.)
* Creates consistent folder hierarchies: Platform Profile, Workload Profile, Logs, Results, etc.
* Keeps a log of file assignments for transparency and debugging
* Works entirely offline — no external dependencies except Python standard libraries