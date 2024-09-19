# SCP Management Tool

This tool provides an interactive menu-driven interface to manage SCP operations between your local machine and remote servers or GCP instances.

## Features
- List, add, and remove servers
- Perform SCP push and pull operations
- Integrate with GCP to manage instances
- Store server details in a configuration file

## Usage
Run the script using:
```bash
bash scp_manager.sh
```

Follow the menu prompts to perform operations.

## Configuration
Server details are stored in `~/.scp_servers`. You can manually edit this file if needed.

## Requirements
- Bash
- gcloud CLI (for GCP integration)

## Future Enhancements
- Implement SCP push and pull operations
- Add GCP instance management
- Improve error handling and validation