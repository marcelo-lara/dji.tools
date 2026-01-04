# DJI Drone files tool

## Mount drone DCIM folder

## Copy to server storage
mkdir -p /srv/storage/raw_footage
rm -rf /srv/storage/raw_footage/*
cp -r -p /mnt/usb/DCIM/DJI_001/* /srv/storage/raw_footage

# install mp4Merge
wget https://github.com/gyroflow/mp4-merge/releases/download/v1.0.0/mp4-merge-linux-x64
chmod +x mp4-merge-linux-x64
mv mp4-merge-linux-x64 ./mp4-merge

# install Gyroflow
sudo apt install libva2 libvdpau1 libasound2t64 libxkbcommon0 libpulse0 libc++-dev libvulkan1
wget https://github.com/gyroflow/gyroflow/releases/download/v1.6.3/Gyroflow-linux64.tar.gz
tar -xf Gyroflow-linux64.tar.gz -C /usr/bin/Gyroflow
