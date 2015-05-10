import os
import urlparse
from lxml import html
import requests


def download_slideshare(request_url):
    print("Downloading HTML content ...")
    page = requests.get(request_url)
    tree = html.fromstring(page.text)
    output_pdf_temp = "temp.pdf"
    joiner = "'/System/Library/Automator/Combine PDF Pages.action/Contents/Resources/join.py'"
    counter = 1
    output_pdf = None

    all_images = tree.xpath('//img[@class="slide_image"]')
    for img in all_images:
        file_url = img.get("data-full")
        if output_pdf is None:

            filename, ext = os.path.splitext(os.path.basename(urlparse.urlsplit(file_url).path))
            output_pdf = filename.replace("-1-1024", "") + ".pdf"
            print("output file: %s" % output_pdf)

        print("Downloading page %d" % counter)

        input_page = "page_%d.jpg" % counter
        os.system('aria2c -q "%s" -o %s' % (file_url, input_page))
        output_page = "page_%d.pdf" % counter
        os.system('convert %s %s' % (input_page, output_page))
        os.system("python %s -o %s %s %s"
                  % (joiner, output_pdf_temp, output_pdf, output_page))
        os.system("mv %s %s" % (output_pdf_temp, output_pdf))
        os.system("rm -rf %s %s" % (input_page, output_page))

        counter += 1

    print("Done!")

