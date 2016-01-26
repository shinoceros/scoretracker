scoretracker
============

###Installation
* Install the latest Raspian image (Jessie Lite was used)

```
sudo apt-get update && sudo apt-get upgrade
sudo apt-get install git sox espeak libasound2-dev libsox-fmt-mp3 python-dev
# PIP
wget https://bootstrap.pypa.io/get-pip.py
sudo python get-pip.py --no-wheel
sudo pip install cython requests enum34 pyalsaaudio
```

Install the following packages:
* [Kivy 1.9.0](http://kivy.org/docs/installation/installation-rpi.html)
* [libnfc 1.7.1](http://nfc-tools.org/index.php?title=Libnfc#Debian_.2F_Ubuntu)
* [zeromq 4.1.3](http://zeromq.org/intro:get-the-software)
* [PIP](https://pip.pypa.io/en/latest/installing.html)

```
sudo pip install pyzmq

# Clone this repository into your Raspberry's home directory:
git clone https://github.com/shinoceros/scoretracker
```
