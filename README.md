# slideshare
Download slideshare slides as images and combine them to make final pdf

# Prerequisites
* aria2c: for downloading images from web
* convert: from ImageMagick for converting image to pdf

The following python modules are required to install first
* lxml
* requests

# Limitation
Current version only runs on MacOSX because it need pdf joiner which is distributed with MacOSX

# Usage
Append slideshare urls to runner.py to array all_urls, then from command line call 

``` bash
$ python runner.py
```

