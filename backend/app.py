from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, as_completed
import yt_dlp
import os
import zipfile
import shutil
import uuid
from datetime import datetime, timedelta
import logging
from functools import partial
import time
import threading

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_WORKERS = 4
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
TEMP_FOLDER = os.path.join(BASE_DIR, "temp")
MAX_RETRIES = 3
CLEANUP_INTERVAL = 900  # 15 minutes
MAX_FILE_AGE = 3600    # 1 hour

# Create necessary folders
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

class DownloadManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self.active_downloads = {}
        self.lock = threading.Lock()
        
    def get_download_options(self, format_type):
        """Get download options based on format type."""
        if format_type == 'mp3':
            return {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        else:  # mp4
            return {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoRemuxer',
                    'preferedformat': 'mp4',
                }],
            }

    def download_file(self, link, format_type, output_path):
        """Download a single file with retry mechanism."""
        for attempt in range(MAX_RETRIES):
            try:
                ydl_opts = {
                    **self.get_download_options(format_type),
                    'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link, download=True)
                    filename = ydl.prepare_filename(info)
                    
                    # Get the actual file path after conversion
                    actual_ext = 'mp3' if format_type == 'mp3' else 'mp4'
                    actual_filename = os.path.splitext(filename)[0] + '.' + actual_ext
                    
                    # Verify file exists
                    if os.path.exists(actual_filename):
                        return actual_filename
                    else:
                        # Search for the file in the output directory
                        for file in os.listdir(output_path):
                            if file.startswith(os.path.splitext(os.path.basename(filename))[0]):
                                return os.path.join(output_path, file)
                    
            except Exception as e:
                logger.error(f"Download attempt {attempt + 1} failed for {link}: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None

    def create_zip(self, files, zip_path):
        """Create a ZIP file from the downloaded files."""
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    if os.path.exists(file):
                        zipf.write(file, os.path.basename(file))
            return True
        except Exception as e:
            logger.error(f"Error creating zip file: {str(e)}")
            return False

    def cleanup_old_files(self):
        """Clean up files older than MAX_FILE_AGE."""
        current_time = datetime.now()
        for folder in [DOWNLOAD_FOLDER, TEMP_FOLDER]:
            if os.path.exists(folder):
                for root, _, files in os.walk(folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                            if current_time - file_time > timedelta(seconds=MAX_FILE_AGE):
                                os.remove(file_path)
                                logger.info(f"Cleaned up old file: {file_path}")
                        except Exception as e:
                            logger.error(f"Error cleaning up {file_path}: {str(e)}")

download_manager = DownloadManager()

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.json
        links = data.get('links', [])
        format_type = data.get('format', 'mp3').lower()
        
        if not links:
            return jsonify({'error': 'No links provided'}), 400

        # Create unique download directory for this request
        session_id = str(uuid.uuid4())
        temp_path = os.path.join(TEMP_FOLDER, session_id)
        os.makedirs(temp_path, exist_ok=True)

        # Download files concurrently
        download_func = partial(download_manager.download_file, format_type=format_type, output_path=temp_path)
        futures = [download_manager.executor.submit(download_func, link) for link in links if link.strip()]

        # Collect results
        downloaded_files = []
        for future in as_completed(futures):
            try:
                filename = future.result()
                if filename:
                    downloaded_files.append(filename)
            except Exception as e:
                logger.error(f"Error downloading: {str(e)}")

        if not downloaded_files:
            shutil.rmtree(temp_path, ignore_errors=True)
            return jsonify({'error': 'No files were downloaded successfully'}), 400

        # Create ZIP file
        zip_filename = os.path.join(DOWNLOAD_FOLDER, f"{session_id}.zip")
        if not download_manager.create_zip(downloaded_files, zip_filename):
            shutil.rmtree(temp_path, ignore_errors=True)
            return jsonify({'error': 'Failed to create zip file'}), 500

        # Clean up individual files
        shutil.rmtree(temp_path, ignore_errors=True)

        # Send file and schedule cleanup
        try:
            return send_file(
                zip_filename,
                as_attachment=True,
                download_name=f"youtube_downloads_{format_type}.zip"
            )
        finally:
            def delayed_cleanup():
                time.sleep(5)  # Wait for file to be sent
                try:
                    if os.path.exists(zip_filename):
                        os.remove(zip_filename)
                        logger.info(f"Cleaned up zip file: {zip_filename}")
                except Exception as e:
                    logger.error(f"Error cleaning up zip file: {str(e)}")

            threading.Thread(target=delayed_cleanup).start()

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'downloads_folder': os.path.exists(DOWNLOAD_FOLDER),
        'temp_folder': os.path.exists(TEMP_FOLDER)
    })

def periodic_cleanup():
    """Periodic cleanup of old files."""
    while True:
        time.sleep(CLEANUP_INTERVAL)
        download_manager.cleanup_old_files()

if __name__ == "__main__":
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    
    # Run the Flask app
    app.run(port=5000, threaded=True)