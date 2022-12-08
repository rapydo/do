#!/bin/bash
set -e

echo "Converting TS Interfaces to JSON Schemas..."

grep -v 'from "@app/types"' /app/app/rapydo/app/types.ts > /tmp/types.ts
grep -v 'from "@rapydo/types"' /app/app/custom/app/types.ts >> /tmp/types.ts

ts-json-schema-generator -f /app/tsconfig.app.json -p /tmp/types.ts -o /app/app/types.json

node /rapydo/compile_validation_schemas.js

echo "Conversion completed"
