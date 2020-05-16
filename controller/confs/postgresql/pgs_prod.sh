#!/bin/bash

###################
# Production configuration
base_conf='/var/lib/postgresql/data/postgresql.conf'
echo "" > $base_conf
echo "listen_addresses = '*'" >> $base_conf
echo "max_connections = 500" >> $base_conf
echo "shared_buffers = 1536MB" >> $base_conf
echo "maintenance_work_mem = 256MB" >> $base_conf
echo "dynamic_shared_memory_type = posix" >> $base_conf
echo "max_worker_processes = 10" >> $base_conf
echo "max_parallel_workers = 8" >> $base_conf
echo "log_timezone = 'UTC'" >> $base_conf
echo "datestyle = 'iso, mdy'" >> $base_conf
echo "timezone = 'UTC'" >> $base_conf
echo "lc_messages = 'en_US.utf8'" >> $base_conf
echo "lc_monetary = 'en_US.utf8'" >> $base_conf
echo "lc_numeric = 'en_US.utf8'" >> $base_conf
echo "lc_time = 'en_US.utf8'" >> $base_conf
echo "default_text_search_config = 'pg_catalog.english'" >> $base_conf

###################
echo "Production conf applied"
