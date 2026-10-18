#!/bin/bash
# P3.2 (owner ruling 333 B): the Thinking speech packets of the carriers, A2T -> E21 -> E22, one SERVING-SWAP WINDOW per carrier (scripts/flights/carriers/carrier_think_packets_gpu.sh).
# Each window stops the resident session, encodes on the GPU (A2T: smoke stage, rate gate, full stage + promotion; Earnings: four-window smoke pass, then -- only if it passed --
# the full pass; encode under a root lease, audit, provenance, formal packets), stops the encoder normally and starts the Thinking session again. A failure inside a window restores the
# Thinking geometry and stops the chain (the first non-zero exit); later carriers wait for the coordinator.
#
#   bash scripts/flights/carriers/batch_chain_carrier_packets.sh [all|a2t|e21|e22]
#
# After a clean exit the P3.3 package is derived with `carrier_think_derive_cells.py --require-receipts` (the queue hook queue_carriers_after.sh does it), which pins the packet
# artifacts into the nine carrier baselines. The exposure rows of the packets are closed with chain_lib.sh close_rows_after_seal (a failure is logged, not fatal: a window pass
# seals no run manifest, so the coordinator may close the rows by hand with ledger_mark_consumed.py --apply).
# Preconditions (the coordinator's): the DRAFT rows countersigned and committed (package_launch ... --until commit), no flight / lease / driver alive, the master tree clean.
SEG=${1:-all}
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
SP=$MAIN/scripts/flights/batch
CP=$MAIN/scripts/flights/carriers
. "$MAIN/scripts/lib/data_root.sh" && saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
LOG=/home/chao/batch-chain-carrierpackets.out
PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
. "$SP/chain_lib.sh"
case "$SEG" in all) CARRIERS="a2t e21 e22" ;; a2t|e21|e22) CARRIERS=$SEG ;; *) echo "usage: batch_chain_carrier_packets.sh [all|a2t|e21|e22]"; exit 64 ;; esac
echo "chain start $(date -u +%FT%TZ) segment $SEG HEAD $(git -C "$MAIN" rev-parse --short HEAD)" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh|lease_cli' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
[ -e "$DATA/locks/flight.lock" ] && { echo "flight.lock present; abort" >> $LOG; exit 7; }
ids_of() {  # the packets run ids of one carrier, from the registration writer's own table
  $PY -B -c "import sys; sys.path.insert(0, '$CP'); import carrier_think_packets_write_registration as w; print(' '.join(s['run'] for s in w.pass_specs() if s['carrier'] == '$1'))"
}
for C in $CARRIERS; do
  chain_log "carrier $C packets window begins"
  bash "$CP/carrier_think_packets_gpu.sh" --run "$C" >> $LOG 2>&1; RC=$?
  chain_log "carrier $C packets window ended rc=$RC"
  [ $RC -eq 0 ] || exit $RC
  CLOSE_ROWS_REPO=$MAIN CLOSE_ROWS_PY=$PY close_rows_after_seal $(ids_of "$C") || chain_log "close_rows_after_seal failed (rc=$?); close the rows by hand: ledger_mark_consumed.py --apply"
done
exit 0
