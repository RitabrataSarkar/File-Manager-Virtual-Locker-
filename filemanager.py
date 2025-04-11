from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort, jsonify, send_file, make_response
import os
import time
from datetime import datetime
import json
import hashlib
import shutil
import re
import humanize

app = Flask(__name__)
app.secret_key = 'supersecretkey'

ROOT_FOLDER = 'uploads'
os.makedirs(ROOT_FOLDER, exist_ok=True)
USER_DB = 'users.json'

if not os.path.exists(USER_DB):
    with open(USER_DB, 'w') as f:
        json.dump({}, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    with open(USER_DB, 'r') as f:
        users = json.load(f)
    if username in users and users[username] == hash_password(password):
        user_folder = os.path.join(ROOT_FOLDER, username)
        os.makedirs(user_folder, exist_ok=True)
        return True
    return False

def signup(username, password):
    with open(USER_DB, 'r') as f:
        users = json.load(f)
    if username in users:
        return False
    users[username] = hash_password(password)
    with open(USER_DB, 'w') as f:
        json.dump(users, f)
    user_folder = os.path.join(ROOT_FOLDER, username)
    os.makedirs(user_folder, exist_ok=True)
    return True

def get_user_folder():
    if 'user' not in session:
        return None
    return os.path.join(ROOT_FOLDER, session['user'])

def list_folders(path):
    try:
        return sorted([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])
    except:
        return []

def list_files(path):
    try:
        return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    except:
        return []
    
def search_recursive(base_path, query):
    """ Recursively search for files and folders matching the query """
    matches = []
    for root, dirs, files in os.walk(base_path):
        for d in dirs:
            if query.lower() in d.lower():
                matches.append(os.path.join(root, d))
        for f in files:
            if query.lower() in f.lower():
                matches.append(os.path.join(root, f))
    return matches

def sanitize_folder_name(folder_name):
    return re.sub(r'[^a-zA-Z0-9_\-.]', '_', folder_name).strip('_')

def get_file_info(path):
    """Get detailed information about a file or folder with proper icons"""
    try:
        stat = os.stat(path)
        is_file = os.path.isfile(path)
        name = os.path.basename(path)
        
        # Default values
        file_type = "File"
        icon = "fa-file"  # Default file icon
        
        if not is_file:
            return {
                'name': name,
                'type': 'Folder',
                'size': '-',
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y %H:%M'),
                'path': path,
                'icon': 'fa-folder'  # Folder icon works fine
            }
        
        # Get file extension
        ext = os.path.splitext(name)[1].lower()
        
        # Map extensions to icons
        icon_map = {
            '.pdf': 'fa-file-pdf',
            '.jpg': 'fa-file-image',
            '.jpeg': 'fa-file-image',
            '.png': 'fa-file-image',
            '.gif': 'fa-file-image',
            '.zip': 'fa-file-zipper',
            '.rar': 'fa-file-zipper',
            '.7z': 'fa-file-zipper',
            '.doc': 'fa-file-word',
            '.docx': 'fa-file-word',
            '.xls': 'fa-file-excel',
            '.xlsx': 'fa-file-excel',
            '.ppt': 'fa-file-powerpoint',
            '.pptx': 'fa-file-powerpoint',
            '.txt': 'fa-file-lines',
            '.py': 'fa-file-code',
            '.js': 'fa-file-code',
            '.html': 'fa-file-code',
            '.css': 'fa-file-code',
        }
        
        # Set icon based on extension
        icon = icon_map.get(ext, 'fa-file')  # Default to fa-file if extension not found
        
        return {
            'name': name,
            'type': file_type,
            'size': humanize.naturalsize(stat.st_size),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y %H:%M'),
            'path': path,
            'icon': icon  # This will be the proper Font Awesome class
        }
        
    except Exception as e:
        return {
            'name': os.path.basename(path),
            'type': 'Unknown',
            'size': '-',
            'modified': '-',
            'path': path,
            'icon': 'fa-file'  # Fallback icon
        }
        
def get_file_details(path):
    """Get detailed information about a file or folder, including correct type and icon."""
    try:
        stat = os.stat(path)
        is_file = os.path.isfile(path)

        file_extension = os.path.splitext(path)[1].lower()
        file_type = "File"
        icon = "fas fa-file"  # Default icon with proper prefix

        # File Type Mapping
        file_types = {
            "image": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"],
            "document": [".pdf", ".doc", ".docx", ".txt", ".odt"],
            "spreadsheet": [".xls", ".xlsx", ".csv"],
            "presentation": [".ppt", ".pptx"],
            "archive": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "code": [".py", ".js", ".html", ".css", ".cpp", ".java", ".c", ".php", ".sh"],
            "executable": [".exe", ".msi", ".bat", ".app", ".out"],
        }

        icon_map = {
            "image": "fas fa-file-image",
            "document": "fas fa-file-pdf",
            "spreadsheet": "fas fa-file-excel",
            "presentation": "fas fa-file-powerpoint",
            "archive": "fas fa-file-archive",
            "code": "fas fa-file-code",
            "executable": "fas fa-file",
        }

        # Identify File Type and Icon
        for category, extensions in file_types.items():
            if file_extension in extensions:
                file_type = category.capitalize()
                icon = icon_map.get(category, "fas fa-file")
                break

        return {
            "name": os.path.basename(path),
            "type": file_type if is_file else "Folder",
            "size": humanize.naturalsize(stat.st_size) if is_file else "-",
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%b %d, %Y %I:%M %p'),
            "icon": icon if is_file else "fas fa-folder",  # Ensure proper prefix
            "path": path,
        }
    except Exception as e:
        return {"error": str(e)}



@app.route('/forgot_password/', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        
        if not username or not old_password or not new_password:
            flash('❌ All fields are required', 'error')
            return redirect(url_for('forgot_password'))
            
        with open(USER_DB, 'r') as f:
            users = json.load(f)
        if username not in users or users[username] != hash_password(old_password):
            flash('❌ Error: Incorrect username or password', 'error')
            return redirect(url_for('forgot_password'))
            
        users[username] = hash_password(new_password)
        with open(USER_DB, 'w') as f:
            json.dump(users, f)
            
        flash('✅ Password reset successful. Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_password.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' not in session:
        flash('❌ Please log in first', 'error')
        return redirect(url_for('login'))
    
    user_folder = get_user_folder()
    if not user_folder:
        flash('❌ User folder error', 'error')
        return redirect(url_for('login'))
    
    os.makedirs(user_folder, exist_ok=True)
    current_path = request.args.get('path', user_folder)
    
    # Security check
    normalized_user_folder = os.path.normpath(user_folder)
    normalized_current_path = os.path.normpath(current_path)
    
    if not normalized_current_path.startswith(normalized_user_folder):
        flash('❌ Access denied: Invalid path', 'error')
        return redirect(url_for('index', path=user_folder))
    
    # Check if path exists
    if not os.path.exists(current_path):
        flash('❌ Error: The requested path does not exist', 'error')
        return redirect(url_for('index', path=user_folder))
    
    # Calculate parent path properly
    parent_path = os.path.dirname(current_path)
    if parent_path == current_path or not parent_path.startswith(user_folder):
        parent_path = None

    try:
        folders = list_folders(current_path)
        files = list_files(current_path)
    except Exception as e:
        flash(f'❌ Error accessing directory: {str(e)}', 'error')
        return redirect(url_for('index', path=user_folder))
    
    if request.method == 'POST':
        if 'create_folder' in request.form:
            folder_name = sanitize_folder_name(request.form['folder_name'].strip())
            if not folder_name:
                flash('❌ Folder name cannot be empty', 'error')
            else:
                try:
                    os.makedirs(os.path.join(current_path, folder_name), exist_ok=True)
                    flash(f'✅ Folder "{folder_name}" created successfully', 'success')
                except Exception as e:
                    flash(f'❌ Error creating folder: {str(e)}', 'error')
                    
        elif 'upload_file' in request.files:
            file = request.files['upload_file']
            if file.filename:
                try:
                    file.save(os.path.join(current_path, file.filename))
                    flash(f'✅ File "{file.filename}" uploaded successfully', 'success')
                except Exception as e:
                    flash(f'❌ Error uploading file: {str(e)}', 'error')
        
        return redirect(url_for('index', path=current_path))
    
    breadcrumbs = []
    path_parts = current_path[len(user_folder):].split(os.sep)
    accumulated_path = user_folder
    breadcrumbs.append(('Home', accumulated_path))
    
    for part in path_parts:
        if part:
            accumulated_path = os.path.join(accumulated_path, part)
            breadcrumbs.append((part, accumulated_path))
    
    detailed_folders = []
    for folder in folders:
        path = os.path.join(current_path, folder)
        detailed_folders.append(get_file_info(path))
    
    detailed_files = []
    for file in files:
        path = os.path.join(current_path, file)
        detailed_files.append(get_file_info(path))
    
    return render_template(
        'index.html', 
        folders=detailed_folders,
        files=detailed_files,
        current_path=current_path,
        breadcrumbs=breadcrumbs,
        parent_path=parent_path,
        user_folder=user_folder
    )

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('❌ Both username and password are required', 'error')
            return redirect(url_for('login'))
            
        if authenticate(username, password):
            session['user'] = username
            flash(f'✅ Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
            
        flash('❌ Invalid username or password', 'error')
        
    return render_template('login.html')

@app.route('/signup/', methods=['GET', 'POST'])
def signup_route():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('❌ Both username and password are required', 'error')
            return redirect(url_for('signup_route'))
            
        if len(username) < 3:
            flash('❌ Username must be at least 3 characters', 'error')
            return redirect(url_for('signup_route'))
            
        if len(password) < 6:
            flash('❌ Password must be at least 6 characters', 'error')
            return redirect(url_for('signup_route'))
            
        if signup(username, password):
            flash('✅ Signup successful! Please login', 'success')
            return redirect(url_for('login'))
            
        flash('❌ Username already exists', 'error')
        
    return render_template('signup.html')

@app.route('/logout/')
def logout():
    if 'user' in session:
        flash(f'✅ You have been logged out, {session["user"]}', 'success')
        session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/download/<path:filename>/')
def download(filename):
    user_folder = get_user_folder()
    if not user_folder:
        flash('❌ Please log in first', 'error')
        return redirect(url_for('login'))
    
    # Security check
    if not filename.startswith(user_folder):
        flash('❌ Access denied: Invalid file path', 'error')
        return redirect(url_for('index'))
    
    # Check if file exists
    if not os.path.exists(filename):
        flash('❌ Error: The requested file does not exist', 'error')
        return redirect(url_for('index'))
    
    try:
        return send_from_directory(
            os.path.dirname(filename), 
            os.path.basename(filename), 
            as_attachment=True
        )
    except Exception as e:
        flash(f'❌ Error downloading file: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/delete/', methods=['POST'])
def delete_file():
    if 'user' not in session:
        flash('❌ Please log in first', 'error')
        return redirect(url_for('login'))
    
    file_path = request.form.get('file_path')
    user_folder = get_user_folder()
    
    if not file_path or not file_path.startswith(user_folder):
        flash('❌ Invalid file or permission denied', 'error')
        return redirect(url_for('index'))
    
    if not os.path.exists(file_path):
        flash('❌ Error: The file does not exist', 'error')
        return redirect(url_for('index'))
    
    try:
        os.remove(file_path)
        flash('✅ File deleted successfully', 'success')
    except Exception as e:
        flash(f'❌ Error deleting file: {str(e)}', 'error')
    
    return redirect(url_for('index', path=os.path.dirname(file_path)))

@app.route('/delete_folder/', methods=['POST'])
def delete_folder():
    if 'user' not in session:
        flash('❌ Please log in first', 'error')
        return redirect(url_for('login'))
    
    folder_path = request.form.get('folder_path')
    user_folder = get_user_folder()
    
    if not folder_path or not folder_path.startswith(user_folder):
        flash('❌ Invalid folder or permission denied', 'error')
        return redirect(url_for('index'))
    
    if not os.path.exists(folder_path):
        flash('❌ Error: The folder does not exist', 'error')
        return redirect(url_for('index'))
    
    try:
        shutil.rmtree(folder_path)
        flash('✅ Folder deleted successfully', 'success')
    except Exception as e:
        flash(f'❌ Error deleting folder: {str(e)}', 'error')
    
    return redirect(url_for('index', path=os.path.dirname(folder_path)))

@app.route('/search/')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    results = search_recursive(ROOT_FOLDER, query)
    return jsonify(results)

@app.route('/file_info')
def file_info():
    if 'user' not in session:
        return jsonify({})
    
    path = request.args.get('path', '')
    user_folder = get_user_folder()
    
    if not path.startswith(user_folder):
        return jsonify({})
    
    if not os.path.exists(path):
        return jsonify({})
    
    return jsonify(get_file_info(path))

@app.route('/create_file/', methods=['POST'])
def create_file():
    if 'user' not in session:
        flash('❌ Please log in first', 'error')
        return redirect(url_for('login'))

    file_name = request.form.get('file_name', '').strip()
    current_path = request.form.get('path', '').strip()

    if not file_name:
        flash('❌ File name cannot be empty', 'error')
        return redirect(url_for('index', path=current_path))

    user_folder = get_user_folder()
    if not current_path.startswith(user_folder):
        flash('❌ Invalid path or permission denied', 'error')
        return redirect(url_for('index', path=user_folder))

    file_path = os.path.join(current_path, file_name)

    if os.path.exists(file_path):
        flash('❌ A file with this name already exists', 'error')
    else:
        try:
            with open(file_path, 'w') as f:
                f.write('')  # Creates an empty file
            flash(f'✅ File "{file_name}" created successfully', 'success')
        except Exception as e:
            flash(f'❌ Error creating file: {str(e)}', 'error')

    return redirect(url_for('index', path=current_path))

@app.route('/edit_file')
def edit_file():
    if 'user' not in session:
        flash('❌ Please log in first', 'error')
        return redirect(url_for('login'))

    file_path = request.args.get('file_path', '').strip()
    user_folder = get_user_folder()

    # Security check - ensure the file is within the user's folder
    if not file_path.startswith(user_folder):
        flash('❌ Access denied', 'error')
        return redirect(url_for('index'))

    # Check if file exists
    if not os.path.exists(file_path):
        flash('❌ File not found', 'error')
        return redirect(url_for('index'))

    # Check if it's a text file by extension
    text_extensions = [
        '.txt', '.md', '.cfg', '.conf', '.ini', 
        '.log', '.json', '.xml', '.yaml', '.yml',
        '.py', '.js', '.html', '.css', '.php'
    ]
    
    if not any(file_path.lower().endswith(ext) for ext in text_extensions):
        flash('❌ Only text files can be edited', 'error')
        return redirect(url_for('index'))

    try:
        # Try UTF-8 first, fall back to latin-1 if needed
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
                
        return render_template('edit_file.html', 
                            file_path=file_path, 
                            content=content,
                            file_name=os.path.basename(file_path))
    except Exception as e:
        flash(f'❌ Error reading file: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/preview-image')
def preview_image():
    file_path = request.args.get('path')
    return send_file(file_path, mimetype='image/*')

@app.route('/serve-file/<path:filename>')
def serve_file(filename):
    """Serves a file for viewing or downloading."""
    try:
        return send_file(filename)
    except Exception as e:
        return str(e), 404


@app.route('/save_file/', methods=['POST'])
def save_file():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Please log in first'}), 403

    file_path = request.form.get('file_path', '').strip()
    user_folder = get_user_folder()

    if not file_path.startswith(user_folder):
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(request.form.get('content', ''))
        return jsonify({'success': True, 'message': 'File saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error saving file: {str(e)}'}), 500

@app.errorhandler(404)
def page_not_found(e):
    flash('❌ The page you requested was not found', 'error')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_server_error(e):
    flash('❌ An internal server error occurred', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)