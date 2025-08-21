#!/bin/bash

while true; do
    # Delete contents inside uploads directory but not the directory itself
    rm  /home/ubuntu/secure-upload-main/uploads/*png
    rm  /home/ubuntu/secure-upload-main/uploads/*jpeg
    rm  /home/ubuntu/secure-upload-main/uploads/*jpg

    # Sleep for 2 hours (7200 seconds)
    sleep 7200
done
