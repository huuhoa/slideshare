__author__ = 'huuhoa'

import slideshare

if __name__ == "__main__":
    all_urls = [
        #"http://www.slideshare.net/amraldo/introduction-to-stm32part1",
        #"http://www.slideshare.net/amraldo/introduction-to-stm32part2",
        ]
    for x in all_urls:
        slideshare.download_slideshare(x)
