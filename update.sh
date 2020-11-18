#!/usr/bin/env bash
git fetch --all && git reset --hard origin/dev && git pull origin dev
chmod +x main.py v2ray -R
