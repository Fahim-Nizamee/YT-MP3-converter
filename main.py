from flask import Flask, render_template, request, send_file
import os
import urllib.parse
import subprocess
import secrets
import shutil

app = Flask(__name__)

def update_youtube_dl():
    pass

def download_video(video_url, download_directory):
    subprocess.run(['youtube-dl', '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', '--extract-audio', '--audio-format', 'mp3', '-o', f'{download_directory}/%(title)s.%(ext)s', video_url])

def convert_to_mp3(mp4_path, mp3_path):
    subprocess.run(['ffmpeg', '-i', mp4_path, '-vn', '-acodec', 'libmp3lame', '-b:a', '320k', mp3_path])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    video_url = request.form['video_url']
    delete_folders_with_finished_txt()

    try:
        download_token = secrets.token_urlsafe(16)
        download_directory = f'{app.root_path}/static/downloads/{download_token}'
        os.makedirs(download_directory)
        with open(f'{download_directory}/finished.txt', 'w'):
            pass

        # Update youtube-dl
        update_youtube_dl()

        # Download the video
        download_video(video_url, download_directory)

        # Convert the video to MP3
        video_title = os.listdir(download_directory)[0]  # Assumes only one video is downloaded
        mp4_path = f'{download_directory}/{video_title}'
        mp3_path = f'{download_directory}/{video_title.replace(".mp4", ".mp3")}'
        convert_to_mp3(mp4_path, mp3_path)

        return render_template('success.html', download_link=f'/download/{download_token}/{video_title}')

    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/download/<token>/<filename>')
def download(token, filename):
    decoded_filename = urllib.parse.unquote(filename)
    download_path = f'{app.root_path}/static/downloads/{token}/{decoded_filename}.mp3'
    return send_file(download_path, as_attachment=True)

def delete_folders_with_finished_txt():
    base_directory = f'{app.root_path}/static/downloads/'
    if os.path.exists(base_directory):
        for folder_name in os.listdir(base_directory):
            folder_path = os.path.join(base_directory, folder_name)
            finished_txt_path = os.path.join(folder_path, 'finished.txt')

            if os.path.exists(finished_txt_path):
                shutil.rmtree(folder_path)

if __name__ == '__main__':
    app.run(debug=False)
