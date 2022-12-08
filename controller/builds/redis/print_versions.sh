#!/bin/bash
echo "Redis $(redis-server --version | awk '{ print $3}')"
