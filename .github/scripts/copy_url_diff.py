import glob
import os
import re
import shutil

OLD_FINDER = re.compile(r'-\s+"\s+\\"(.+?)\\"')
NEW_FINDER = re.compile(r'\+\s+"\s+\\"(.+?)\\"')


def map_urls(patch_file):
    urls = {}
    with open(patch_file, "r") as fh:
        for line in fh:
            if match := OLD_FINDER.match(line):
                old_url = match.group(1)
                line = next(fh)
                new_url = NEW_FINDER.match(line).group(1)
                urls[old_url] = new_url
    return urls


def replace_urls(urls, path):
    shutil.copy(path, f"{path}.bak")
    with open(f"{path}.bak", "r") as in_fh, open(path, "w") as out_fh:
        for line in in_fh:
            for old_url, new_url in urls.items():
                line = line.replace(old_url, new_url)
            out_fh.write(line)
    os.remove(f"{path}.bak")


def main():
    urls = map_urls("links.patch")
    for path in glob.glob("demo/answers/*.ipynb"):
        print(path)
        replace_urls(urls, path)


if __name__ == "__main__":
    main()
