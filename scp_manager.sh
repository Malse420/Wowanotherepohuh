#!/bin/bash

# Configuration file path
CONFIG_FILE="$HOME/.scp_servers"
GCP_CACHE="$HOME/.gcp_instances"

# Color Codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check command availability
function check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}Error: $1 is not installed.${NC}" >&2
        exit 1
    fi
}

# Ensure required commands are available
check_command "scp"
check_command "gcloud"

# Function to display the main menu
function main_menu() {
    while true; do
        echo -e "\n${BLUE}SCP Management Tool${NC}"
        echo -e "${YELLOW}1. List Servers${NC}"
        echo -e "${YELLOW}2. Add Server${NC}"
        echo -e "${YELLOW}3. Remove Server${NC}"
        echo -e "${YELLOW}4. Push File${NC}"
        echo -e "${YELLOW}5. Pull File${NC}"
        echo -e "${YELLOW}6. List GCP Instances${NC}"
        echo -e "${YELLOW}7. Exit${NC}"
        read -p "Choose an option: " choice
        case $choice in
            1) list_servers ;;
            2) add_server ;;
            3) remove_server ;;
            4) push_file ;;
            5) pull_file ;;
            6) list_gcp_instances ;;
            7) echo -e "${GREEN}Exiting...${NC}"; exit 0 ;;
            *) echo -e "${RED}Invalid option. Please try again.${NC}" ;;
        esac
    done
}

# Function to list servers
function list_servers() {
    if [ -f "$CONFIG_FILE" ]; then
        echo -e "${GREEN}Configured Servers:${NC}"
        cat "$CONFIG_FILE"
    else
        echo -e "${RED}No servers configured.${NC}"
    fi
}

# Function to add a server
function add_server() {
    read -p "Enter server address: " address
    read -p "Enter SSH identity file path: " identity
    while [ ! -f "$identity" ]; do
        echo -e "${RED}Invalid SSH identity file path. Please try again.${NC}"
        read -p "Enter SSH identity file path: " identity
    done
    read -p "Enter port (default 22): " port
    port=${port:-22}
    echo "$address,$identity,$port" >> "$CONFIG_FILE"
    echo -e "${GREEN}Server added.${NC}"
}

# Function to remove a server
function remove_server() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}No servers configured.${NC}"
        return
    fi

    read -p "Enter server address to remove: " address
    if grep -q "^$address," "$CONFIG_FILE"; then
        read -p "Are you sure you want to remove the server $address? (y/n): " confirm
        if [[ "$confirm" == "y" ]]; then
            sed -i "/^$address,/d" "$CONFIG_FILE"
            echo -e "${GREEN}Server removed.${NC}"
        else
            echo -e "${YELLOW}Operation cancelled.${NC}"
        fi
    else
        echo -e "${RED}Server not found.${NC}"
    fi
}

# Function to push a file to a server
function push_file() {
    select_server
    read -p "Enter source file path: " src_path
    while [ ! -f "$src_path" ]; do
        echo -e "${RED}Source file does not exist. Please try again.${NC}"
        read -p "Enter source file path: " src_path
    done
    read -p "Enter destination path on server: " dest_path
    scp -i "$identity" -P "$port" "$src_path" "$address":"$dest_path"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}File successfully pushed to $address.${NC}"
    else
        echo -e "${RED}Failed to push file to $address.${NC}"
    fi
}

# Function to pull a file from a server
function pull_file() {
    select_server
    read -p "Enter source file path on server: " src_path
    read -p "Enter destination path on local machine: " dest_path
    scp -i "$identity" -P "$port" "$address":"$src_path" "$dest_path"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}File successfully pulled from $address.${NC}"
    else
        echo -e "${RED}Failed to pull file from $address.${NC}"
    fi
}

# Function to select a server from the list
function select_server() {
    if [ -f "$CONFIG_FILE" ]; then
        echo -e "${BLUE}Select a server:${NC}"
        select server in $(awk -F, '{print $1}' "$CONFIG_FILE"); do
            if [ -n "$server" ]; then
                local IFS=, # Set the Internal Field Separator
                read -r address identity port <<< $(grep "^$server," "$CONFIG_FILE")
                export address identity port
                break
            else
                echo -e "${RED}Invalid selection. Please try again.${NC}"
            fi
        done
    else
        echo -e "${RED}No servers configured.${NC}"
        exit 1
    fi
}

# Function to add GCP instances to the server list
function add_gcp_instances() {
    while IFS=' ' read -r name ip; do
        if [[ -n "$ip" ]]; then
            echo "$ip,${HOME}/.ssh/google_compute_engine,22" >> "$CONFIG_FILE"
        fi
    done < "$GCP_CACHE"
    echo -e "${GREEN}GCP instances added to server list.${NC}"
}

# Function to list GCP instances
function list_gcp_instances() {
    echo -e "${BLUE}Fetching GCP instances...${NC}"
    if gcloud compute instances list --format="value(name,EXTERNAL_IP)" > "$GCP_CACHE"; then
        cat "$GCP_CACHE"
        add_gcp_instances
    else
        echo -e "${RED}Failed to fetch GCP instances.${NC}"
    fi
}

# Catch interruptions gracefully
trap 'echo -e "${RED}\nScript interrupted. Exiting...${NC}"; exit 1;' SIGINT

# Main script execution
main_menu
