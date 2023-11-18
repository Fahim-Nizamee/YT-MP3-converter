from flask import Flask, render_template, request, send_file,current_app
from pytube import YouTube
from pydub import AudioSegment
from slugify import slugify
import os
import urllib.parse
import subprocess
import secrets
import shutil
import urllib
from concurrent.futures import ThreadPoolExecutor
import time

app = Flask(__name__)
executor = ThreadPoolExecutor()

def download_video(video_url, download_directory):
    yt = YouTube(video_url)
    video = yt.streams.filter(progressive=True, file_extension="mp4").order_by('resolution').desc().first()
    video_title = slugify(yt.title)
    video.download(download_directory, filename=f'{video_title}.mp4')
    return video_title

def convert_to_mp3(mp4_path, mp3_path):
    audio = AudioSegment.from_file(mp4_path, format='mp4')
    audio.export(mp3_path, format='mp3', bitrate='320k')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    video_url = request.form['video_url']
    try:
        download_token = secrets.token_urlsafe(16)
        download_directory = f'{current_app.root_path}/static/downloads/{download_token}'
        os.makedirs(download_directory)
        with open(f'{download_directory}/finished.txt', 'w'):
            pass

        future = executor.submit(download_video, video_url, download_directory)
        video_title = future.result()

        mp4_path = f'{download_directory}/{video_title}.mp4'
        mp3_path = f'{download_directory}/{video_title}.mp3'
        executor.submit(convert_to_mp3, mp4_path, mp3_path)
        time.sleep(2)
        return render_template('success.html', download_link=f'/download/{download_token}/{video_title}')

    except Exception as e:
        return render_template('error.html', error=str(e))


@app.route('/download/<token>/<filename>')
def download(token, filename):
    decoded_filename = urllib.parse.unquote(filename)
    download_path = f'{current_app.root_path}/static/downloads/{token}/{slugify(decoded_filename)}.mp3'
    return send_file(download_path, as_attachment=True)
    

def delete_folders_with_finished_txt():
    base_directory = f'{current_app.root_path}/static/downloads/'
    if os.path.exists(base_directory):
        for folder_name in os.listdir(base_directory):
            folder_path = os.path.join(base_directory, folder_name)
            finished_txt_path = os.path.join(folder_path, 'finished.txt')

            if os.path.exists(finished_txt_path):
                shutil.rmtree(folder_path)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
