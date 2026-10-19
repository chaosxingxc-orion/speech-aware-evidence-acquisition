S=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/analysis/design338
export PYTHONDONTWRITEBYTECODE=1
export SPEECHRL_DATA_DIR=/home/chao/saea-data/speechrl-data
cd $S
/home/chao/.venvs/speechrl/bin/python -B $S/l338_bounds.py --out $S/l338-bounds.json > $S/run.log 2>&1; echo rc=$?
tail -5 $S/run.log
