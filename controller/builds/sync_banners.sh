#!/bin/bash

for folder in $(ls); do
    if [[ -d ${folder} ]]; then
        if [[ -f ${folder}/print_versions.sh ]]; then
            echo "Copying banner in ${folder}"
	        cp banner.sh $folder/;
        fi
    fi
done
# cp banner.sh rabbitmq/banner.sh
