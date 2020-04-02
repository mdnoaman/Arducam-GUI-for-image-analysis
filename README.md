# Arducam-GUI-for-image-analysis
This project aims at utilizing budget cameras from Arducam to use for experiments such as capturing fluorescence images from atoms.
The script is based on the examples given on this page https://github.com/ArduCAM/ArduCAM_USB_Camera_Shield

the camera model AR0135 is used for this project which is a monochrome 12 bit sensor.
The start.py imports the cam_vid.py class which has all the streaming methods for continuously capturing images. Multiprocessing is used to obtain a realtime operation without affecting different routines.
