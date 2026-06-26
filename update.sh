#!/bin/bash
# Script to automate git updates
git add .
git commit -m "Auto-update: $(date)"
git push -u origin main
