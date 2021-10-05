#!/bin/bash

# Convert mpiGraph result into html

set -e

IFS=$'\n'
DIR="result-2020-09-08-19.04.45"

for i in `ls $DIR`
do
    if [[ "$i" == "readme.md" ]]
    then 
        continue
    fi
    cd "$DIR"
    python3 ../mpiGraph/html_generator.py -i $i -o tmp
    mv $i tmp/mpiGraph.out
    mv tmp $i
    cd ..
done