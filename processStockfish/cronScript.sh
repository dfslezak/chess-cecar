#!/bin/bash

export PATH=$PATH:/home/dfslezak/local/bin/
kill `ps ex | grep runStockfish | awk {'print $1;'}`
cd /home/dfslezak/repos/neurociencia/ajedrez/codigo/processStockfish
sleep 2
nohup /usr/bin/python -u runStockfishAnalysis.py -d 12 -m 6 -n 100 &
