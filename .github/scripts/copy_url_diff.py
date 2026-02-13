import collections as co
import glob
import os
import re
import shutil
import sys

URL_FINDER = re.compile(r'("(https://.+?)\\"|\((https://.+?)\))')
REMOVE_FINDER = re.compile(r"^-")
ADD_FINDER = re.compile(r"^\+")


def map_urls(patch_file):
    urls = {}
    queue = co.deque()
    with open(patch_file, "r") as fh:
        for line in fh:
            # removed line
            if REMOVE_FINDER.match(line):
                for match in URL_FINDER.finditer(line):
                    groups = [g for g in match.groups() if g is not None]
                    queue.append(groups[-1])  # get url
            # add line that will be replacements
            elif ADD_FINDER.match(line):
                for match in URL_FINDER.finditer(line):
                    groups = [g for g in match.groups() if g is not None]
                    urls[queue.popleft()] = groups[-1]
    return urls


def replace_urls(urls, path):
    shutil.copy(path, f"{path}.bak")
    with open(f"{path}.bak", "r") as in_fh, open(path, "w") as out_fh:
        for line in in_fh:
            old_line = line
            for old_url, new_url in urls.items():
                line = line.replace(old_url, new_url)
            out_fh.write(line)
    os.remove(f"{path}.bak")


def main():
    urls = map_urls(sys.argv[1])
    for path in glob.glob("demo/answers/*.ipynb"):
        print(path)
        replace_urls(urls, path)


if __name__ == "__main__":
    main()
