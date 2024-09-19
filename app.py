from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import paramiko
import os
import json
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from paramiko import Transport, SFTPClient
import logging
import asyncio
import aiofiles
import zipfile

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# SSH and SCP setup
def create_ssh_client(server, port, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

def create_ssh_client_with_key(server, port, user, key_path):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, key_filename=key_path)
    return client

# Simple connection pool
connection_pool = {}

def get_ssh_client(server, port, user, password):
    key = f'{server}:{port}:{user}'
    if key not in connection_pool:
        connection_pool[key] = create_ssh_client(server, port, user, password)
    return connection_pool[key]

def close_ssh_client(server, port, user):
    key = f'{server}:{port}:{user}'
    if key in connection_pool:
        connection_pool[key].close()
        del connection_pool[key]

# Function to download a file from the remote server
async def download_file(server, port, user, password, remote_path, local_path):
    transport = Transport((server, port))
    transport.connect(username=user, password=password)
    sftp = SFTPClient.from_transport(transport)
    async with aiofiles.open(local_path, 'wb') as file:
        await file.write(sftp.get(remote_path))
    sftp.close()
    transport.close()
    logging.info(f'File downloaded from {remote_path} to {local_path}')

# Function to upload a file to the remote server
async def upload_file(server, port, user, password, local_path, remote_path):
    transport = Transport((server, port))
    transport.connect(username=user, password=password)
    sftp = SFTPClient.from_transport(transport)
    async with aiofiles.open(local_path, 'rb') as file:
        await sftp.put(file.read(), remote_path)
    sftp.close()
    transport.close()
    logging.info(f'File uploaded from {local_path} to {remote_path}')

# Function to compress files before transfer
def compress_file(file_path):
    zip_path = f'{file_path}.zip'
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(file_path, os.path.basename(file_path))
    logging.info(f'File {file_path} compressed to {zip_path}')
    return zip_path

# Function to load servers from a JSON file
def load_servers():
    with open('servers.json', 'r') as file:
        return json.load(file)

# Function to save servers to a JSON file
def save_servers(servers):
    with open('servers.json', 'w') as file:
        json.dump(servers, file, indent=4)

# Function to list local files with lazy loading
def list_local_files(directory, offset=0, limit=10):
    files = os.listdir(directory)
    return files[offset:offset + limit]

# Function to list remote files with lazy loading
def list_remote_files(ssh_client, remote_path, offset=0, limit=10):
    stdin, stdout, stderr = ssh_client.exec_command(f'ls {remote_path}')
    files = stdout.read().decode().split('\n')
    return files[offset:offset + limit]

@app.route('/')
@login_required
def index():
    local_files = list_local_files('.')
    return render_template('index.html', local_files=local_files)

@app.route('/connect', methods=['POST'])
@login_required
def connect():
    server = request.form['server']
    port = int(request.form['port'])
    user = request.form['user']
    password = request.form['password']
    remote_path = request.form['remote_path']

    try:
        ssh_client = get_ssh_client(server, port, user, password)
        remote_files = list_remote_files(ssh_client, remote_path)
        local_files = list_local_files('.')
        return render_template('index.html', local_files=local_files, remote_files=remote_files)
    except Exception as error:
        flash(str(error))
        return redirect(url_for('index'))

@app.route('/load_more_files', methods=['GET'])
@login_required
def load_more_files():
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 10))
    local_files = list_local_files('.', offset, limit)
    return jsonify(local_files=local_files)

@app.route('/download', methods=['POST'])
@login_required
def download():
    server = request.form['server']
    port = int(request.form['port'])
    user = request.form['user']
    password = request.form['password']
    remote_file = request.form['remote_file']
    local_file = request.form['local_file']

    try:
        asyncio.run(download_file(server, port, user, password, remote_file, local_file))
        flash('File downloaded successfully.')
    except Exception as error:
        flash(str(error))
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    server = request.form['server']
    port = int(request.form['port'])
    user = request.form['user']
    password = request.form['password']
    local_file = request.form['local_file']
    remote_file = request.form['remote_file']

    try:
        # Compress the file before upload
        compressed_file = compress_file(local_file)
        asyncio.run(upload_file(server, port, user, password, compressed_file, remote_file))
        flash('File uploaded successfully.')
    except Exception as error:
        flash(str(error))
    return redirect(url_for('index'))

@app.route('/servers')
@login_required
def servers():
    servers = load_servers()
    return render_template('servers.html', servers=servers)

@app.route('/add_server', methods=['POST'])
@login_required
def add_server():
    new_server = {
        "name": request.form['name'],
        "address": request.form['address'],
        "port": int(request.form['port']),
        "username": request.form['username']
    }
    servers = load_servers()
    servers.append(new_server)
    save_servers(servers)
    flash('Server added successfully.')
    return redirect(url_for('servers'))

@app.route('/remove_server', methods=['POST'])
@login_required
def remove_server():
    server_name = request.form['name']
    servers = load_servers()
    servers = [s for s in servers if s['name'] != server_name]
    save_servers(servers)
    flash('Server removed successfully.')
    return redirect(url_for('servers'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Replace with actual authentication logic
        if username == 'admin' and password == 'password':
            user = User(id=1)
            login_user(user)
            return redirect(url_for('servers'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/preview_file', methods=['GET'])
@login_required
def preview_file():
    file_path = request.args.get('file_path')
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return jsonify({'content': content})
    except Exception as error:
        return jsonify({'error': str(error)})

if __name__ == '__main__':
    app.run(debug=True)
