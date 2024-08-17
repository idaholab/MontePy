import xml.etree.ElementTree as ET
import urllib.request

NS = {"a": "http://www.sitemaps.org/schemas/sitemap/0.9"}
TOLERANCE = 0.8


def discover_urls():
    tree = ET.parse("doc/build/html/sitemap.xml")
    root = tree.getroot()
    return [node.find("a:loc", NS).text for node in root.findall("a:url", NS)]


def test_urls(urls):
    passed = 0
    for url in urls:
        code = urllib.request.urlopen(url).getcode()
        if code == 200:
            passed += 1
        else:
            print(url, code)
    if passed / len(urls) < TOLERANCE:
        raise ValueError(f"Too many URLs failed")


if __name__ == "__main__":
    test_urls(discover_urls())
