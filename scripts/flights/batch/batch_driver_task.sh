#!/bin/bash
# Scheduled-task wrapper: capture the driver's stdout/stderr (decision 77 debugging aid).
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
[ -e /home/chao/batch-done ] && mv /home/chao/batch-done /home/chao/batch-done.$(date -u +%Y%m%dT%H%M%SZ).bak
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> /home/chao/batch-driver.out
