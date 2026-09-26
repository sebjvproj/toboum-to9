#!/bin/sh
# Construit TOBOUM.BIN et la disquette TOBOUM.fd
# Il faut python3 + Pillow et lwasm (lwtools). Décor au choix : sh build.sh rome
set -e
cd "$(dirname "$0")"
python3 donnees.py ${1:-egypte}
lwasm --6809 --decb -o TOBOUM.BIN --list=toboum.lst --symbols toboum.asm
python3 make_fd.py TOBOUM.BIN TOBOUM.fd DECORS.DAT
