#!/usr/bin/env bash
nvidia-smi --query-gpu=clocks.sm,clocks.max.sm,temperature.gpu,power.draw,utilization.gpu,memory.used,pstate --format=csv,noheader
