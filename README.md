scoretracker
============

###Installation
* Install the latest Raspian image

```
sudo apt-get update && sudo apt-get upgrade
sudo apt-get install git sox espeak libasound2-dev libsox-fmt-mp3 python-dev
# PIP
wget https://bootstrap.pypa.io/get-pip.py
sudo python get-pip.py --no-setuptools --no-wheel
```

Install the following packages:
* [Kivy 1.9.0](http://kivy.org/docs/installation/installation-rpi.html)
* [libnfc 1.7.1](http://nfc-tools.org/index.php?title=Libnfc#Debian_.2F_Ubuntu)
* [zeromq 4.1.3](http://zeromq.org/intro:get-the-software)
* [PIP](https://pip.pypa.io/en/latest/installing.html)

PIP packages:
* cython
* requests (2.7.0)
* enum34
* [pyzmq](http://zeromq.org/bindings:python) (14.7.0)
* pyalsaaudio (0.8.2)

* Clone this repository into your Raspberry's home directory:
```
git clone https://github.com/shinoceros/scoretracker
```
