# shellcheck shell=bash
# The ONE data-root authority for every live operations script (owner directive 2026-10-12, decision 274;
# design docs/superpowers/specs/2026-10-12-engineering-base-unification-design.md; manifest
# configs/base/engineering-base-v1.json). Source it; it defines variables and functions and never acts on its own.
#
# Cut-over (decision 284 step 2) is the ONE line below that assigns SAEA_DATA_ROOT_DEFAULT: change it from the E:
# original to the hot root (a literal: the locator and the Python helpers read the assignment textually), update
# roots.data_root.current in the manifest to match (the locator check
# compares the two) and ~/.bashrc's SPEECHRL_DATA_DIR. Nothing else changes.
#
#   saea_data_root_init     resolve SAEA_DATA_ROOT (explicit SAEA_DATA_ROOT > the default below), export it and
#                           SPEECHRL_DATA_DIR to the same value, refuse a split brain (the implicit default meeting an
#                           inherited SPEECHRL_DATA_DIR that names another root), then run saea_data_root_guard. Returns 1 (and one REFUSED line on
#                           stderr) on any refusal; callers do `saea_data_root_init || exit 70`.
#   saea_data_root_guard    refuse a data root that does not exist, or -- for every root other than the 9p E: original
#                           -- one that is not on a mounted ext4 filesystem (the hot root /home/chao/saea-data/speechrl-data
#                           sits inside the VHDX mount /mnt/saea-data-1 (fstab, LABEL=saea-data-1) behind the symlink
#                           /home/chao/saea-data, decision 296; after a reboot before the logon task SAEA-Mount-Data1
#                           attached the VHD the mount point is an empty root-fs directory and is refused)
#   saea_fs_type <path>     the filesystem type of the mount holding <path> (findmnt; falls back to stat -f)
#
# Environment overrides for tests: SAEA_DATA_ROOT (the root itself), SAEA_DATA_ROOT_FINDMNT (a findmnt stand-in).

SAEA_LEGACY_DATA_ROOT=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
SAEA_HOT_DATA_ROOT=/home/chao/saea-data/speechrl-data
SAEA_DATA_ROOT_DEFAULT=/home/chao/saea-data/speechrl-data

saea_fs_type() {
  local path=$1 fm=${SAEA_DATA_ROOT_FINDMNT:-findmnt} t
  t=$("$fm" -n -o FSTYPE -T "$path" 2>/dev/null | head -n 1)
  if [ -z "$t" ]; then
    case "$(stat -f -c %T "$path" 2>/dev/null)" in
      ext2/ext3) t=ext4 ;;
      v9fs) t=9p ;;
      '') t= ;;
      *) t=$(stat -f -c %T "$path" 2>/dev/null) ;;
    esac
  fi
  echo "$t"
}

saea_data_root_guard() {
  local root=${SAEA_DATA_ROOT:?saea_data_root_guard needs SAEA_DATA_ROOT} resolved t
  if [ ! -d "$root" ]; then
    echo "REFUSED (decision 284): data root $root does not exist or is not a directory (an unmounted hot root leaves /home/chao/saea-data dangling: run the SAEA-Mount-Data1 logon task, then retry)" >&2
    return 1
  fi
  resolved=$(readlink -f "$root")
  if [ "$resolved" = "$(readlink -f "$SAEA_LEGACY_DATA_ROOT" 2>/dev/null)" ] || [ "$root" = "$SAEA_LEGACY_DATA_ROOT" ]; then
    # Pre-cut-over: the E: original is 9p by construction; accepted until the default line changes.
    return 0
  fi
  t=$(saea_fs_type "$resolved")
  if [ "$t" != ext4 ]; then
    echo "REFUSED (decision 267/284): data root $root resolves to $resolved on filesystem '${t:-unknown}', not a mounted ext4; hot paths never run on 9p, drvfs or tmpfs" >&2
    return 1
  fi
  return 0
}

saea_data_root_init() {
  local root=${SAEA_DATA_ROOT:-$SAEA_DATA_ROOT_DEFAULT}
  # An explicit SAEA_DATA_ROOT is an operator choice and wins (it overwrites SPEECHRL_DATA_DIR); only the IMPLICIT
  # default meeting a different inherited SPEECHRL_DATA_DIR is refused, since that is the stale-profile split brain.
  if [ -z "${SAEA_DATA_ROOT:-}" ] && [ -n "${SPEECHRL_DATA_DIR:-}" ] && [ "${SPEECHRL_DATA_DIR%/}" != "${root%/}" ]; then
    echo "REFUSED (decision 274): the inherited SPEECHRL_DATA_DIR=$SPEECHRL_DATA_DIR differs from the data root $root; one flight writes one root (set SAEA_DATA_ROOT explicitly, or fix ~/.bashrc after the cut-over)" >&2
    return 1
  fi
  export SAEA_DATA_ROOT=${root%/}
  export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
  saea_data_root_guard
}
