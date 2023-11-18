from flask import Flask, render_template, request, send_file, current_app
from flask_sqlalchemy import SQLAlchemy
from pytube import YouTube
from pydub import AudioSegment
from slugify import slugify
import os
import secrets
import urllib
from concurrent.futures import ThreadPoolExecutor
import requests
from io import BytesIO

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
executor = ThreadPoolExecutor()

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(16), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    video_data = db.Column(db.LargeBinary, nullable=True)
    music_data = db.Column(db.LargeBinary, nullable=True)
    finished = db.Column(db.Boolean, default=False)

def download_video(video_url, token):
    with app.app_context():
        yt = YouTube(video_url)
        video_title = slugify(yt.title)

        # Download video content into memory
        video_response = requests.get(yt.streams.filter(progressive=True, file_extension="mp4").order_by('resolution').desc().first().url)
        video_data = video_response.content

        # Download music content into memory
        audio = AudioSegment.from_file(BytesIO(video_data), format='mp4')
        mp3_data = BytesIO()
        audio.export(mp3_data, format='mp3', bitrate='320k')

        # Save both video and music data in the database
        file_record = File(token=token, title=video_title, video_data=video_data, music_data=mp3_data.getvalue(), finished=False)
        db.session.add(file_record)
        db.session.commit()

        return video_title


def mark_as_finished(token):
    with app.app_context():
        file_record = File.query.filter_by(token=token, finished=False).first()

        if file_record:
            file_record.finished = True
            db.session.commit()

from sqlalchemy import text

# ...

def delete_finished_data():
    with app.app_context():
        finished_records = File.query.filter_by(finished=True).all()

        if finished_records:
            for file_record in finished_records:
                db.session.delete(file_record)

            db.session.commit()

        # Perform a VACUUM to release unused space in the database file
        db.session.execute(text("VACUUM"))
        db.session.commit()

# def convert_to_mp3(video_data):
#     audio = AudioSegment.from_file(BytesIO(video_data), format='mp4')
#     mp3_data = BytesIO()
#     print(mp3_data, file=sys.stderr)

#     audio.export(mp3_data, format='mp3', bitrate='320k')
#     return mp3_data.getvalue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    video_url = request.form['video_url']
    try:
        download_token = secrets.token_urlsafe(16)

        future = executor.submit(download_video, video_url, download_token)
        video_title = future.result()

        delete_finished_data()
        mark_as_finished(download_token)

        return render_template('success.html', download_link=f'/download/{download_token}/{video_title}')

    except Exception as e:
        return render_template('error.html', error=str(e))


@app.route('/download/<token>/<filename>')
def download(token, filename):
    decoded_filename = urllib.parse.unquote(filename)
    file_record = File.query.filter_by(token=token, title=decoded_filename).first_or_404()
    
    
    data = file_record.music_data if file_record.music_data else file_record.video_data
    return send_file(BytesIO(data), as_attachment=True, download_name=f'{decoded_filename}.mp3')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
