#!/usr/bin/env bash
# Build the self-contained bundle. MUST run inside packaging/Dockerfile.build.
set -euo pipefail

SRC="${SRC:-/src}"
BUILD="${SRC}/build"
APPDIR="${BUILD}/AppDir"
DIST="${SRC}/dist"

# --- refuse to build against the host's glibc (research D-02) -----------------
# A bundle built on a newer host dies at launch on older targets with a linker error, before
# any of GPUM's own error reporting can run. Failing loudly here is far better than shipping
# something that only works on the maintainer's machine.
if [ ! -f /etc/gpum-build-container ] && [ "${GPUM_ALLOW_HOST_BUILD:-0}" != "1" ]; then
  cat >&2 <<'MSG'
ERROR: this script must run inside the build container.

    docker build -f packaging/Dockerfile.build -t gpum-build .
    docker run --rm -v "$PWD:/src" gpum-build /src/packaging/build-appimage.sh

The container pins Ubuntu 22.04 (glibc 2.35). Building on a newer host produces a bundle that
fails to start on every older distribution — see docs/building.md.
MSG
  exit 2
fi

echo "==> cleaning"
rm -rf "$BUILD" "$DIST"
mkdir -p "$BUILD" "$DIST"

echo "==> installing gpum and build tooling"
PY=python3.11
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet "${SRC}[nvidia]" pyinstaller

VERSION="$(cd /tmp && "$PY" -c 'from importlib.metadata import version; print(version("gpum"))')"
echo "==> building gpum ${VERSION}"

"$PY" -m PyInstaller \
    --noconfirm --clean \
    --distpath "${BUILD}/pyinstaller" \
    --workpath "${BUILD}/work" \
    "${SRC}/packaging/gpum.spec"

echo "==> assembling AppDir"
mkdir -p "${APPDIR}/usr/bin" "${APPDIR}/usr/share/icons/hicolor/scalable/apps"
cp -r "${BUILD}/pyinstaller/gpum/." "${APPDIR}/usr/bin/"
cp "${SRC}/packaging/AppRun" "${APPDIR}/AppRun"
chmod +x "${APPDIR}/AppRun"
cp "${SRC}/packaging/gpum.desktop" "${APPDIR}/gpum.desktop"
cp "${SRC}/src/gpum/resources/gpum.svg" "${APPDIR}/gpum.svg"
cp "${SRC}/src/gpum/resources/gpum.svg" \
   "${APPDIR}/usr/share/icons/hicolor/scalable/apps/gpum.svg"

echo "==> verifying AppDir (build-blocking)"
"${SRC}/packaging/verify-appdir.sh" "$APPDIR"

echo "==> sealing AppImage"
OUT="${DIST}/GPUM-${VERSION}-x86_64.AppImage"
ARCH=x86_64 appimagetool "$APPDIR" "$OUT"
chmod +x "$OUT"

# The user-facing size budget applies here, to what someone actually downloads (research S-04).
SIZE_BUDGET_MB=120
actual_mb=$(du -m "$OUT" | cut -f1)
# Docker runs as root, so everything written to the mounted source tree lands root-owned and
# the user who invoked the build cannot even chmod their own artifact. Hand ownership back.
if [ -n "${HOST_UID:-}" ] && [ -n "${HOST_GID:-}" ]; then
  chown -R "${HOST_UID}:${HOST_GID}" "$DIST" "$BUILD" 2>/dev/null || true
else
  # Fall back to whoever owns the mounted tree.
  OWNER="$(stat -c '%u:%g' "$SRC" 2>/dev/null || true)"
  [ -n "$OWNER" ] && chown -R "$OWNER" "$DIST" "$BUILD" 2>/dev/null || true
fi

echo
echo "built: ${OUT}"
echo "size:  ${actual_mb} MB (budget ${SIZE_BUDGET_MB} MB)"
if [ "$actual_mb" -gt "$SIZE_BUDGET_MB" ]; then
  echo "ERROR: bundle exceeds the download budget; revisit the exclusion list in gpum.spec" >&2
  exit 1
fi
