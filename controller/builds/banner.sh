#!/bin/sh

print_line() {

    banner_width=81
    text_len=${#1}

    prefix_indent=$(( (banner_width - text_len) / 2 ))
    suffix_indent=$(( banner_width - text_len - prefix_indent ))

    prefix=''
    for _ in $(seq 1 $prefix_indent); do
        prefix="${prefix} "
    done

    suffix=''
    for _ in $(seq 1 $suffix_indent); do
        suffix="${suffix} "
    done
    
    echo "${prefix}${1}${suffix}"    
}


CWD="$( dirname "$0" )"
VERSIONS=$(/bin/sh ${CWD}/print_versions.sh 2>&1)
VERSIONS=$(print_line "${VERSIONS}")

printf "
 ╔═════════════════════════════════════════════════════════════════════════════════╗
 ║                                                                                 ║
 ║  ██████╗   █████╗  ██████╗  ██╗   ██╗ ██████╗   ██████╗      ██████╗       ██╗  ║
 ║  ██╔══██╗ ██╔══██╗ ██╔══██╗ ╚██╗ ██╔╝ ██╔══██╗ ██╔═══██╗     ╚════██╗     ███║  ║
 ║  ██████╔╝ ███████║ ██████╔╝  ╚████╔╝  ██║  ██║ ██║   ██║     █████╔╝      ╚██║  ║
 ║  ██╔══██╗ ██╔══██║ ██╔═══╝    ╚██╔╝   ██║  ██║ ██║   ██║      ╚═══██╗      ██║  ║
 ║  ██║  ██║ ██║  ██║ ██║         ██║    ██████╔╝ ╚██████╔╝     ██████╔╝ ██╗  ██║  ║
 ║  ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝         ╚═╝    ╚═════╝   ╚═════╝      ╚═════╝  ╚═╝  ╚═╝  ║
 ║${VERSIONS}║
 ╚═════════════════════════════════════════════════════════════════════════════════╝
"


















