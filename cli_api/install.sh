#!/usr/bin/env bash

set -euo pipefail

if [ "$UID" -eq 0 ] ; then
    DEFAULT_INSTALL_DIR=/usr/local
else
    DEFAULT_INSTALL_DIR=$HOME/.local
fi

APP_FILES="gears.py
pylavor.py
razor_app.py
razor
uninstall.sh"

echo -n "Where should the application be installed? [$DEFAULT_INSTALL_DIR] "

read install_dir

if [ -z "$install_dir" ] ; then
    install_dir=$DEFAULT_INSTALL_DIR
fi
lib_dir=$install_dir/lib/razor_cli
bin_dir=$install_dir/bin

mkdir -p "$install_dir"
mkdir -p "$lib_dir"
mkdir -p "$bin_dir"

echo "Installing Unidecode library in Python"
pip install unidecode requests==2.31.0

echo "Creating an Uninstall file"
rm -f uninstall.sh
touch uninstall.sh

echo "rm -f $bin_dir/razor" >> uninstall.sh
echo "rm -R $lib_dir" >> uninstall.sh

echo "Copying app files"
for file in $APP_FILES ; do
    cp -a "$file" "$lib_dir"
done

echo "Creating entry in $bin_dir"

echo "cd $lib_dir" >> $lib_dir/razor
echo "python3 razor_app.py" >> $lib_dir/razor

rm -f $bin_dir/razor
ln -s $lib_dir/razor $bin_dir/razor

