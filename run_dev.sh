#!/bin/sh
docker run -it --rm -p 8000:8000 -v "$PWD":/app uvi
