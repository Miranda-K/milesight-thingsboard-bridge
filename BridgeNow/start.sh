#!/bin/bash
echo "Setting up ThingsBoard for the first time..."
docker compose --profile install run --rm thingsboard-installer

echo "Starting the full stack..."
docker compose up -d
