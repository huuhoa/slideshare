# Copyright (C) 2015 NGUYEN Huu Hoa <huuhoa at gmail.com>
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

from __future__ import with_statement

import os
import urlparse
from lxml import html
import requests
import string
from datetime import datetime

default_dpi = 96.0

def _datetime_to_pdfdate(dt):
    return dt.strftime("%Y%m%d%H%M%SZ")


def _parse(cont, indent=1):
    if type(cont) is dict:
        return b"<<\n" + b"\n".join(
            [4 * indent * b" " + k + b" " + _parse(v, indent + 1)
             for k, v in sorted(cont.items())]) + b"\n" + 4 * (indent - 1) * b" " + b">>"
    elif type(cont) is int:
        return str(cont).encode()
    elif type(cont) is float:
        return ("%0.4f" % cont).encode()
    elif isinstance(cont, PDFObject):
        return ("%d 0 R" % cont.identifier).encode()
    elif type(cont) is str or type(cont) is bytes:
        if type(cont) is str and type(cont) is not bytes:
            raise Exception("parse must be passed a bytes object in py3")
        return cont
    elif type(cont) is list:
        return b"[ " + b" ".join([_parse(c, indent) for c in cont]) + b" ]"
    else:
        raise Exception("cannot handle type %s" % type(cont))


class PDFObject(object):
    def __init__(self, content, stream=None):
        self.content = content
        self.stream = stream
        self.identifier = None

    def tostring(self):
        if self.stream:
            return (
                ("%d 0 obj " % self.identifier).encode() +
                _parse(self.content) +
                b"\nstream\n" + self.stream + b"\nendstream\nendobj\n")
        else:
            return ("%d 0 obj " % self.identifier).encode() + _parse(self.content) + b" endobj\n"


class PDFDocument(object):
    def __init__(self, version=3, title=None, author=None, creator=None,
                 producer=None, creationdate=None, moddate=None, subject=None,
                 keywords=None, nodate=False):
        self.version = version  # default pdf version 1.3
        now = datetime.now()
        self.objects = []

        info = {}
        if title:
            info[b"/Title"] = b"(" + title + b")"
        if author:
            info[b"/Author"] = b"(" + author + b")"
        if creator:
            info[b"/Creator"] = b"(" + creator + b")"
        if producer:
            info[b"/Producer"] = b"(" + producer + b")"
        if creationdate:
            info[b"/CreationDate"] = b"(D:" + _datetime_to_pdfdate(creationdate).encode() + b")"
        elif not nodate:
            info[b"/CreationDate"] = b"(D:" + _datetime_to_pdfdate(now).encode() + b")"
        if moddate:
            info[b"/ModDate"] = b"(D:" + _datetime_to_pdfdate(moddate).encode() + b")"
        elif not nodate:
            info[b"/ModDate"] = b"(D:" + _datetime_to_pdfdate(now).encode() + b")"
        if subject:
            info[b"/Subject"] = b"(" + subject + b")"
        if keywords:
            info[b"/Keywords"] = b"(" + b",".join(keywords) + b")"

        self.info = PDFObject(info)

        # create an incomplete pages object so that a /Parent entry can be
        # added to each page
        self.pages = PDFObject({
            b"/Type": b"/Pages",
            b"/Kids": [],
            b"/Count": 0
        })

        self.catalog = PDFObject({
            b"/Pages": self.pages,
            b"/Type": b"/Catalog"
        })
        self.add_object(self.catalog)
        self.add_object(self.pages)

    def add_object(self, obj):
        obj.identifier = len(self.objects) + 1
        self.objects.append(obj)

    def add_image(self, color, width, height, image_format, image_data, pdf_x, pdf_y):
        if color == 'L':
            colorspace = b"/DeviceGray"
        elif color == 'RGB':
            colorspace = b"/DeviceRGB"
        elif color == 'CMYK' or color == 'CMYK;I':
            colorspace = b"/DeviceCMYK"
        else:
            print("unsupported color space: %s" % color)
            return

        if pdf_x < 3.00 or pdf_y < 3.00:
            print("pdf width or height is below 3.00 - decrease the dpi")

        # either embed the whole jpeg or deflate the bitmap representation
        if image_format is "JPEG":
            ofilter = [b"/DCTDecode"]
        elif image_format is "JPEG2000":
            ofilter = [b"/JPXDecode"]
            self.version = 5  # jpeg2000 needs pdf 1.5
        else:
            ofilter = [b"/FlateDecode"]
        image = PDFObject({
            b"/Type": b"/XObject",
            b"/Subtype": b"/Image",
            b"/Filter": ofilter,
            b"/Width": width,
            b"/Height": height,
            b"/ColorSpace": colorspace,
            # hardcoded as PIL doesn't provide bits for non-jpeg formats
            b"/BitsPerComponent": 8,
            b"/Length": len(image_data)
        }, image_data)

        if color == 'CMYK;I':
            # Inverts all four channels
            image.content[b'/Decode'] = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0]

        text = ("q\n%0.4f 0 0 %0.4f 0 0 cm\n/Im0 Do\nQ" % (pdf_x, pdf_y)).encode()

        content = PDFObject({
            b"/Length": len(text)
        }, text)

        page = PDFObject({
            b"/Type": b"/Page",
            b"/Parent": self.pages,
            b"/Resources": {
                b"/XObject": {
                    b"/Im0": image
                }
            },
            b"/MediaBox": [0, 0, pdf_x, pdf_y],
            b"/Contents": content
        })
        self.pages.content[b"/Kids"].append(page)
        self.pages.content[b"/Count"] += 1
        self.add_object(page)
        self.add_object(content)
        self.add_object(image)

    def tostring(self):
        # add info as last object
        self.add_object(self.info)

        xreftable = list()

        result = ("%%PDF-1.%d\n" % self.version).encode()

        xreftable.append(b"0000000000 65535 f \n")
        for o in self.objects:
            xreftable.append(("%010d 00000 n \n" % len(result)).encode())
            result += o.tostring()

        xrefoffset = len(result)
        result += b"xref\n"
        result += ("0 %d\n" % len(xreftable)).encode()
        for x in xreftable:
            result += x
        result += b"trailer\n"
        result += _parse({b"/Size": len(xreftable), b"/Info": self.info, b"/Root": self.catalog}) + b"\n"
        result += b"startxref\n"
        result += ("%d\n" % xrefoffset).encode()
        result += b"%%EOF\n"
        return result


class ConvertPDF(object):
    def __init__(self, dpi=None, title=None,
                 author=None, creator=None, producer=None, creationdate=None,
                 moddate=None, subject=None, keywords=None, colorspace="RGB",
                 nodate=False, verbose=False):
        self.pdf = PDFDocument(3, title, author, creator, producer, creationdate,
                               moddate, subject, keywords, nodate)
        self.colorspace = colorspace
        self.dpi = dpi

    def _get_image_size(self, file_name):
        import struct
        import imghdr

        '''Determine the image type of fhandle and return its size.
        from draco'''
        with open(file_name, 'rb') as file_handle:
            head = file_handle.read(24)
            if len(head) != 24:
                return
            if imghdr.what(file_name) == 'png':
                check = struct.unpack('>i', head[4:8])[0]
                if check != 0x0d0a1a0a:
                    return
                width, height = struct.unpack('>ii', head[16:24])
            elif imghdr.what(file_name) == 'gif':
                width, height = struct.unpack('<HH', head[6:10])
            elif imghdr.what(file_name) == 'jpeg':
                try:
                    file_handle.seek(0)  # Read 0xff next
                    size = 2
                    ftype = 0
                    while not 0xc0 <= ftype <= 0xcf:
                        file_handle.seek(size, 1)
                        byte = file_handle.read(1)
                        while ord(byte) == 0xff:
                            byte = file_handle.read(1)
                        ftype = ord(byte)
                        size = struct.unpack('>H', file_handle.read(2))[0] - 2
                    # We are at a SOFn block
                    file_handle.seek(1, 1)  # Skip `precision' byte.
                    height, width = struct.unpack('>HH', file_handle.read(4))
                except Exception:  # IGNORE:W0703
                    return
            else:
                return
            return width, height

    def add_image(self, image_file):
        try:
            rawdata = image_file.read()
        except AttributeError:
            with open(image_file, "rb") as im:
                rawdata = im.read()
        imgdata = rawdata
        width, height = self._get_image_size(image_file)
        ndpi = self.dpi, self.dpi
        # output size based on dpi; point = 1/72 inch
        pdf_x, pdf_y = 72.0 * width / float(ndpi[0]), 72.0 * height / float(ndpi[1])

        self.pdf.add_image(self.colorspace, width, height, "JPEG", imgdata, pdf_x, pdf_y)

    def write(self, output_file):
        with open(output_file, "w") as file_output:
            file_output.write(self.pdf.tostring())


def _download_image(image_url):
    from tempfile import NamedTemporaryFile

    temp_file = NamedTemporaryFile(delete=False)
    r = requests.get(image_url, stream=True)
    for chunk in r.iter_content(4096):
        temp_file.write(chunk)
    return temp_file.name


def download(request_url):
    print("Downloading HTML content ...")
    page = requests.get(request_url)
    tree = html.fromstring(page.text)
    counter = 1
    output_pdf = None

    all_images = tree.xpath('//img[@class="slide_image"]')
    image_files = []
    convert_pdf = ConvertPDF(dpi=72)
    for img in all_images:
        file_url = img.get("data-full")
        if output_pdf is None:
            filename, ext = os.path.splitext(os.path.basename(urlparse.urlsplit(file_url).path))
            output_pdf = filename.replace("-1-1024", "") + ".pdf"
            print("output file: %s" % output_pdf)

        print("Downloading page %d" % counter)

        input_page = _download_image(file_url)

        convert_pdf.add_image(input_page)
        os.unlink(input_page)

        counter += 1

    convert_pdf.write(output_pdf)

    print("Done!")

