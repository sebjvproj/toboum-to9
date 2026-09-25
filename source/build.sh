#!/bin/sh
# Construit TOTO.BIN et la disquette TOTO.fd
# Il faut python3 + Pillow et lwasm (lwtools). Décor au choix : sh build.sh rome
set -e
cd "$(dirname "$0")"
python3 donnees.py ${1:-egypte}
lwasm --6809 --decb -o TOTO.BIN --list=toto.lst --symbols toto.asm
python3 make_fd.py TOTO.BIN TOTO.fd
