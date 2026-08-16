#!/usr/bin/env bash
# Assertions V-01..V-06 from contracts/distribution-contract.md.
#
# V-01 and V-02 are build-BLOCKING, not advisory: both failures are invisible on the build
# machine and only appear on a user's, where they produce either a cryptic launch crash or
# silently wrong numbers.
set -uo pipefail

APPDIR="${1:?usage: verify-appdir.sh <AppDir>}"
FAILURES=0
GLIBC_FLOOR_MINOR=35
# The user-facing budget (research S-04) applies to the *compressed* AppImage, which the build
# script checks after sealing. The AppDir is uncompressed, so it gets a looser ceiling here
# whose job is only to catch a gross regression — e.g. QtWebEngine creeping back in.
APPDIR_CEILING_MB=200

fail() { echo "  FAIL: $*"; FAILURES=$((FAILURES + 1)); }
pass() { echo "  ok:   $*"; }

echo "Verifying ${APPDIR}"

# --- V-01: no NVIDIA driver library may be bundled (BLOCKING) ------------------
echo "V-01 driver libraries"
found_driver=$(find "$APPDIR" -type f \( \
      -name 'libnvidia-*' -o -name 'libcuda*' -o -name 'libGLX_nvidia*' \
   -o -name 'libnvcuvid*' -o -name 'libnvoptix*' \) 2>/dev/null)
if [ -n "$found_driver" ]; then
  fail "driver libraries bundled — these are version-locked to the host driver and would"
  echo "        misreport on any machine with a different one:"
  echo "$found_driver" | sed 's/^/          /'
else
  pass "no NVIDIA driver libraries bundled"
fi

# --- V-02: nothing may require a glibc newer than the floor (BLOCKING) ---------
echo "V-02 glibc floor (2.${GLIBC_FLOOR_MINOR})"
too_new=""
while IFS= read -r obj; do
  syms=$(objdump -T "$obj" 2>/dev/null | grep -oE 'GLIBC_2\.[0-9]+' | sort -u || true)
  for sym in $syms; do
    minor="${sym#GLIBC_2.}"
    if [ "$minor" -gt "$GLIBC_FLOOR_MINOR" ] 2>/dev/null; then
      too_new="${too_new}\n  $(basename "$obj") needs ${sym}"
    fi
  done
done < <(find "$APPDIR" -type f \( -name '*.so*' -o -perm -u+x \) 2>/dev/null | head -400)
if [ -n "$too_new" ]; then
  fail "objects require a newer glibc than the oldest supported target:"
  echo -e "$too_new" | sed 's/^/        /'
  echo "        This bundle was almost certainly built outside the container."
else
  pass "no object requires glibc newer than 2.${GLIBC_FLOOR_MINOR}"
fi

# --- V-03: required Qt modules present, excluded ones absent ------------------
echo "V-03 Qt module set"
for required in libQt6Core libQt6Gui libQt6Widgets; do
  if find "$APPDIR" -name "${required}*" -print -quit | grep -q .; then
    pass "$required present"
  else
    fail "$required missing"
  fi
done
for banned in libQt6WebEngineCore libQt6Quick libQt63DCore libQt6Multimedia libQt6Charts; do
  if find "$APPDIR" -name "${banned}*" -print -quit | grep -q .; then
    fail "$banned bundled despite being excluded (size budget)"
  fi
done

# --- V-04: both display session types must work -------------------------------
echo "V-04 platform plugins"
if find "$APPDIR" -name "libqxcb.so" -print -quit | grep -q .; then
  pass "X11 platform plugin present"
else
  fail "libqxcb.so missing — FR-018 requires X11 sessions to work"
fi
# PySide6 names this libqwayland.so; older/other builds use libqwayland-generic.so.
if find "$APPDIR" \( -name "libqwayland.so" -o -name "libqwayland-*.so" \) -print -quit | grep -q .; then
  pass "Wayland platform plugin present"
else
  fail "no Wayland platform plugin — FR-018 requires Wayland sessions to work"
fi

# --- V-05: uncompressed size sanity ------------------------------------------
echo "V-05 uncompressed size"
size_mb=$(du -sm "$APPDIR" | cut -f1)
if [ "$size_mb" -gt "$APPDIR_CEILING_MB" ]; then
  fail "AppDir is ${size_mb} MB, over the ${APPDIR_CEILING_MB} MB ceiling — an excluded Qt"
  echo "        module has probably crept back in"
else
  pass "AppDir is ${size_mb} MB (compressed budget checked after sealing)"
fi

# --- V-06: launchable ---------------------------------------------------------
echo "V-06 launchability"
[ -x "$APPDIR/AppRun" ] && pass "AppRun is executable" || fail "AppRun missing or not executable"

# Qt's xcb plugin dlopens this by name; if it is bundled but not on AppRun's library path the
# application aborts on a real display while passing every headless test.
if find "$APPDIR" -name 'libxcb-cursor.so*' -print -quit | grep -q .; then
  if grep -q '_internal' "$APPDIR/AppRun"; then
    pass "libxcb-cursor bundled and on AppRun's library path"
  else
    fail "libxcb-cursor is bundled but AppRun's LD_LIBRARY_PATH does not cover _internal;"
    echo "        the xcb plugin will fail to load on a real display"
  fi
else
  fail "libxcb-cursor.so.0 missing — Qt 6.5+ needs it for the xcb platform plugin"
fi
if [ -f "$APPDIR/gpum.desktop" ]; then
  if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$APPDIR/gpum.desktop" && pass "desktop entry validates" \
      || fail "desktop entry does not validate"
  else
    pass "desktop entry present (validator unavailable)"
  fi
else
  fail "gpum.desktop missing"
fi

echo
if [ "$FAILURES" -gt 0 ]; then
  echo "VERIFY: FAILED (${FAILURES} check(s))"
  exit 1
fi
echo "VERIFY: PASSED"
