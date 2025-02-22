from flask import Flask, request, send_file
from flask_cors import CORS
import yt_dlp
import os
import zipfile
import shutil
import random
import string
from threading import Timer

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create a 'download' folder if it doesn't exist
download_folder = "download"
os.makedirs(download_folder, exist_ok=True)

def generate_random_filename():
    """Generate a random filename for the ZIP file."""
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{random_string}.zip"

def delete_file_after_delay(file_path, delay=900):
    """Delete a file after a specified delay (in seconds)."""
    def delete_file():
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
    Timer(delay, delete_file).start()

def download_and_convert_to_mp3(link, output_folder):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info)
            print(f"Downloaded and converted {filename} to MP3 successfully.")
            return filename
    except Exception as e:
        print(f"Error downloading {link}: {e}")
        return None

def create_zip(output_folder, zip_filename):
    """Create a ZIP file from the contents of the output folder."""
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(output_folder):
            for file in files:
                zipf.write(os.path.join(root, file), file)
    print(f"Created ZIP file: {zip_filename}")

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    links = data.get('links')
    output_folder = "downloaded_files"
    os.makedirs(output_folder, exist_ok=True)

    downloaded_files = []
    for link in links:
        if link:
            file_path = download_and_convert_to_mp3(link, output_folder)
            if file_path:
                downloaded_files.append(file_path)

    # Generate a random filename for the ZIP file
    zip_filename = os.path.join(download_folder, generate_random_filename())
    create_zip(output_folder, zip_filename)

    # Clean up
    for file_path in downloaded_files:
        if os.path.exists(file_path):
            os.remove(file_path)
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)  # Remove the directory and its contents

    # Schedule the ZIP file for deletion after 15 minutes (900 seconds)
    delete_file_after_delay(zip_filename, delay=900)

    return send_file(zip_filename, as_attachment=True)

if __name__ == "__main__":
    app.run(port=5000)