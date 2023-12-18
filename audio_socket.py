from pydub import AudioSegment
from pydub.utils import make_chunks
from flask import Blueprint
from datetime import datetime

import os
import json
import base64
import subprocess

from urllib import request as downloader
from pathlib import Path

audio_socket = Blueprint('audio_socket', __name__)
duration = 20 # no of milliseconds of each base64 string from audio file
audio_types = ["story", "rhyme", "riddle"]

AUDIO_CACHE = {}

def get_audio(input_selector):

    if input_selector > 2:
        return None

    urlData = "https://sunbirddevbbpublic.blob.core.windows.net/jars/ivrs/ivrs_config.json?st=2023-12-18T06%3A03%3A54Z&se=2023-12-19T06%3A03%3A54Z&sp=rl&sv=2018-03-28&sr=b&sig=PBpT54uK5Voc5Fb3HLsRO3%2F7%2BSBpHZFC7Y2unDqSFPY%3D"
    webURL = downloader.urlopen(urlData)
    data = webURL.read()
    encoding = webURL.info().get_content_charset('utf-8')
    config = json.loads(data.decode(encoding))

    audio_type = audio_types[input_selector]
    no_of_audios = len(config[audio_type])

    day_of_year = datetime.today().timetuple().tm_yday
    mod_day_no = int(day_of_year % no_of_audios)

    audio_index = no_of_audios if mod_day_no == 0 else mod_day_no

    return config[audio_type][audio_index - 1]

def get_chunks(input_selector, file_path):
    audio_type = audio_types[input_selector]

    day_of_year = datetime.today().timetuple().tm_yday
    path = Path(file_path)
    filename = path.stem + path.suffix.split("?")[0]

    cache_key = audio_type+":"+filename

    if cache_key in AUDIO_CACHE:
        chunk_detail = AUDIO_CACHE[cache_key]

        if chunk_detail['cached_on'] == day_of_year:
            return chunk_detail['chunks']

    path = Path(file_path)
    filename = path.stem + path.suffix.split("?")[0]
    local_file_path = "temp_audio_files/" + filename
    local_converted_file_path = "temp_converted_files/" + path.stem + ".wav"

    downloader.urlretrieve(file_path, local_file_path)

    subprocess.call(['ffmpeg', '-i', local_file_path, '-ar', '8000', '-ab', '128', '-ac', '1', '-y', local_converted_file_path])

    audio = AudioSegment.from_file(local_converted_file_path)

    # Define the number of parts you want to split the audio into
    raw_chunks = make_chunks(audio, duration)
    chunks_array = []
    for i, chunk in enumerate(raw_chunks):
        start_time = i * duration

        chunks_array.append({
            "event": "media",
            "sequence_number": str(i + 1),
            "media": {
                "chunk": str(i + 1),
                "timestamp": str(int(start_time)),
                "payload": base64.b64encode(chunk.raw_data).decode("utf-8")
            }
        })

    AUDIO_CACHE[cache_key] = {'cached_on': day_of_year, 'chunks': chunks_array}

    return chunks_array

def remove_temp_file(file_path):
    os.remove(file_path)

@audio_socket.route('/media')
def echo(ws):
    while not ws.closed:
        message = ws.receive()
        # print(message)
        if message is None:
            continue
        request_payload = json.loads(message)
        event = request_payload['event']

        if event == "media":
            # chunk = get_payload(request)
            pass
        elif event == 'dtmf':
            session_id = request_payload['stream_sid']
            print("inside dtmf")
            # clear the existing auio events if it's playing already
            mark_event = {"event":"clear","stream_sid":session_id}
            ws.send(json.dumps(mark_event))

            input_selector = int(request_payload["dtmf"]["digit"]) - 1

            audio_url = get_audio(input_selector)
            if audio_url:
                chunks = get_chunks(input_selector, audio_url)
                for chunk in chunks:
                    chunk["stream_sid"] = session_id
                    ws.send(json.dumps(chunk))
            else:
                pass

            # mark_event = {"event":"mark","sequence_number": int(request_payload['sequence_number']) + 1,"stream_sid":request_payload['stream_sid'],"mark":{"name":"reply complete"}}
            # ws.send(json.dumps(mark_event))
        elif event == "stop":
            print("inside stop")
