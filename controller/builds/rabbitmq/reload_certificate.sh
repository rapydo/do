#!/bin/bash
set -e

if [[ $(rabbitmq-diagnostics status) ]];
then
    rabbitmqctl eval 'ssl:clear_pem_cache().'

    echo "PEM Cached cleared"
else
    echo ""
    echo "RabbitMQ is not reachable (still starting?), can't clear the PEM cache"
fi

