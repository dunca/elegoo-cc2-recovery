#!/usr/bin/env bash
# Build the CC2 recovery U-Boot (runs from RAM via FEL; never written to the eMMC).
#
# Upstream U-Boot v2026.01 + OpenCentauri's Centauri Carbon 2 board files and patches,
# configured to: ignore the stock env on the eMMC (so its console stays on),
# boot straight into `ums 0 mmc 1`, and (with --ext4-write) allow ext4write.
#
# Requirements (macOS/Homebrew shown; Linux equivalents work):
#   brew install dtc swig make u-boot-tools arm-none-eabi-gcc openssl@3 gh
#   gh auth login            # only used to fetch OpenCentauri's files
#
# Usage: ./build-recovery-uboot.sh [--ext4-write] [WORKDIR]
# Output: WORKDIR/build/spl/sunxi-spl.bin and WORKDIR/build/u-boot.bin
set -euo pipefail

EXT4=0
if [[ "${1:-}" == "--ext4-write" ]]; then EXT4=1; shift; fi
W="${1:-$PWD/cc2-uboot}"
UBOOT_TAG=v2026.01
OC_PATH=meta-opencentauri/recipes-bsp/u-boot/files

mkdir -p "$W" && cd "$W"
[[ -d u-boot ]] || git clone --depth 1 --branch "$UBOOT_TAG" https://source.denx.de/u-boot/u-boot.git u-boot

mkdir -p files
for f in $(gh api "repos/OpenCentauri/cosmos/contents/$OC_PATH" --jq '.[] | select(.type=="file") | .name'); do
  gh api "repos/OpenCentauri/cosmos/contents/$OC_PATH/$f" --jq .content | base64 -d > "files/$f"
done

cd u-boot
git checkout -- . && git clean -fdq
for p in ../files/0001-*.patch ../files/0002-*.patch; do git apply --whitespace=nowarn "$p"; done
cp ../files/elegoo-centauri-carbon*.dts dts/upstream/src/arm/
cp ../files/*_defconfig ../files/*.config configs/
cp ../files/*.env board/sunxi/

# One combined defconfig: CC2 board + USB-mass-storage recovery fragment + no env from eMMC.
# (`make defconfig fragment.config` did not merge the fragment, so concatenate instead.)
cat configs/elegoo_centauri_carbon2_defconfig configs/usb-msd-cc2.config > configs/cc2_recovery_defconfig
printf 'CONFIG_ENV_SOURCE_FILE=""\nCONFIG_BOOTDELAY=0\n' >> configs/cc2_recovery_defconfig
if (( EXT4 )); then printf 'CONFIG_CMD_EXT4_WRITE=y\nCONFIG_EXT4_WRITE=y\n' >> configs/cc2_recovery_defconfig; fi

# The in-tree pylibfdt does not build with SWIG 4 + Python 3.14; use the PyPI wheel instead.
python3 -m venv ../venv
../venv/bin/pip -q install setuptools pyelftools pylibfdt
export PATH="$PWD/../venv/bin:$(brew --prefix make 2>/dev/null)/libexec/gnubin:$PATH"
export CROSS_COMPILE=arm-none-eabi-
SSL=$(brew --prefix openssl@3 2>/dev/null || echo /usr)

make O=../build cc2_recovery_defconfig
# The final binman packaging step fails on macOS; the two files we need are built before it.
make O=../build -j"$(getconf _NPROCESSORS_ONLN)" NO_PYTHON=1 \
  HOSTCFLAGS="-I$SSL/include" HOSTLDFLAGS="-L$SSL/lib" || true

ls -l ../build/spl/sunxi-spl.bin ../build/u-boot.bin
grep -E 'ENV_IS_NOWHERE|^CONFIG_BOOTCOMMAND|EXT4_WRITE' ../build/.config
if strings -n4 ../build/u-boot.bin | grep -q '^bootcmd=run '; then
  echo "WARNING: a board env bootcmd was compiled in; check CONFIG_ENV_SOURCE_FILE" >&2
fi
echo "OK. Load with: sunxi-fel spl build/spl/sunxi-spl.bin; sunxi-fel write 0x42e00000 build/u-boot.bin; sunxi-fel exe 0x42e00000"
