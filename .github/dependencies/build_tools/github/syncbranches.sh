#!/bin/bash
git checkout -q actions-data-download
git pull --tags origin actions-data-download
git pull --tags origin main
git push origin actions-data-download:actions-data-download

git checkout -q gh-pages
git pull --tags origin gh-pages
git pull --tags origin main
git push origin gh-pages:gh-pages

git checkout -q main

git branch -d actions-data-download
git branch -d gh-pages
