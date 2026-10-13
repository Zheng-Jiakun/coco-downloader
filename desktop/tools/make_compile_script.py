#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate resource compilation scripts for the project
"""
import os
import sys

WINDOWS_SCRIPT = """@echo off
REM Compile Qt Resource Files
echo Compiling Qt resources...

python -m PyQt5.pyrcc_main app/resource/resource.qrc -o app/common/resource.py

echo Done!
pause
"""

UNIX_SCRIPT = """#!/bin/bash
# Compile Qt Resource Files
echo "Compiling Qt resources..."

python -m PyQt5.pyrcc_main app/resource/resource.qrc -o app/common/resource.py

echo "Done!"
"""

def create_scripts():
    desktop_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Create Windows batch file
    bat_path = os.path.join(desktop_dir, 'compile_resources.bat')
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(WINDOWS_SCRIPT)
    print(f"Created: {bat_path}")

    # Create Unix shell script
    sh_path = os.path.join(desktop_dir, 'compile_resources.sh')
    with open(sh_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(UNIX_SCRIPT)

    # Make shell script executable on Unix
    if sys.platform != 'win32':
        os.chmod(sh_path, 0o755)

    print(f"Created: {sh_path}")
    print("\nYou can now run:")
    print("  - Windows: compile_resources.bat")
    print("  - Linux/Mac: ./compile_resources.sh")

if __name__ == '__main__':
    create_scripts()
