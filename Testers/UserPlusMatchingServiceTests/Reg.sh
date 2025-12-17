#!/usr/bin/env bash

GATEWAY_URL="http://127.0.0.1:5000"

echo "=== Registering drivers via /user/register ==="

curl -s -X POST "${GATEWAY_URL}/user/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Driver One",
    "phone": "9000000001",
    "role": "driver",
    "password": "pass1"
  }'
echo

curl -s -X POST "${GATEWAY_URL}/user/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Driver Two",
    "phone": "9000000002",
    "role": "driver",
    "password": "pass2"
  }'
echo

echo "=== Registering users (non-driver users) via /user/register ==="

curl -s -X POST "${GATEWAY_URL}/user/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer One",
    "phone": "8000000001",
    "role": "rider",
    "password": "cust1"
  }'
echo

curl -s -X POST "${GATEWAY_URL}/user/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Two",
    "phone": "8000000002",
    "role": "rider",
    "password": "cust2"
  }'
echo

curl -s -X POST "${GATEWAY_URL}/user/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Three",
    "phone": "8000000003",
    "role": "rider",
    "password": "cust3"
  }'
echo

echo "=== Done ==="
