#!/bin/bash

new_ver=$1

echo "next version: $new_ver"

echo "Updating Changelog"

sed -i "s/#Next Version#/$new_ver/w changes" doc/source/changelog.rst
git add doc/source/changelog.rst

echo "Updating changelog to next version: " > commit_template

git commit -t commit_template

rm commit_template

echo "Tagging next release"

git tag "v$new_ver"
