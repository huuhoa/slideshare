# slideshare
Download slideshare slides as images and combine them to make final pdf

# Prerequisites
* aria2c: for downloading images from web
* convert: from ImageMagick for converting image to pdf

The following python modules are required to install first
* lxml
* requests


# Install
Clone GIT repository to local drive and execute setup.py

``` bash
$ git clone https://github.com/huuhoa/slideshare.git
$ cd slideshare
$ python setup.py install


# Usage
Append slideshare urls to runner.py to array all_urls, then from command line call 

``` bash
$ python runner.py
```

Or from command line

``` bash
$ python
> import slideshare
> slideshare.download("url-to-slide")

```
