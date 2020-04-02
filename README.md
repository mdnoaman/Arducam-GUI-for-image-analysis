# Arducam-GUI-for-image-analysis
This project aims at utilizing budget cameras from Arducam to use for experiments such as capturing fluorescence images from atoms.
The script is based on the examples given on this page https://github.com/ArduCAM/ArduCAM_USB_Camera_Shield

The camera model AR0135 is used for this project which is a monochrome 12 bit sensor.
The start.py imports the cam_vid.py class which has all the streaming methods for continuously capturing images. Multiprocessing is used to obtain a realtime operation without affecting different routines.

The "GUI" is built with opencv which not only displays the images but also draws a bounding box with a configurable size. It also plots a real time measured avarage signal captures in the region of interest (ROI) with time. There is another functionality of displaying a zoomed in image window for the ROI to visually ananlyze the image portion of interest. All these funtions are operated by keyboard inputs while keeping the main image window active. The details are written in the start.py code. By press 's' button a raw file can be saved for further analysis. There are two files which can be used to adjust the settings of the camera such as exposure, gain, mode etc. One general setting file, which is provided by the https://github.com/ArduCAM/ArduCAM_USB_Camera_Shield has a large number of setting options. However for the ease of use, I have added another file which can be updated to quickly change few settings. In this case, I am changing the exposure time. By pressing 'r' button the updated file will be read by the program to adapt the new exposure value. This happens while the camera is still running. The program actually pauses for a very short time while it updates the new setting. This feature can be pretty useful when taking several images with hand written documenation.

The SDK file can be obtained, again from here https://github.com/ArduCAM/ArduCAM_USB_Camera_Shield
