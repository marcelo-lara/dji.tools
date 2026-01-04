# DJI Drone files tool

## Mount drone DCIM folder

## Copy to server storage
mkdir -p /srv/storage/raw_footage
rm -rf /srv/storage/raw_footage/*
cp -r -p /mnt/usb/DCIM/DJI_001/* /srv/storage/raw_footage
