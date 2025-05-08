import json
import os.path
import shutil

import speech_recognition as sr
from pydub import AudioSegment


def mp3_to_wav():
    lib_path = "./lib"
    os.environ["PATH"] += os.pathsep + os.path.abspath(lib_path)
    in_path = "hear_temp"
    save_path = "wav_temp"
    if os.path.exists(save_path):
        shutil.rmtree(save_path)
    os.mkdir(save_path)
    if os.path.exists(in_path):
        hear_mp3_list = os.listdir(in_path)
        for hear in hear_mp3_list:
            audio = AudioSegment.from_mp3(os.path.join(in_path, hear))
            basename = hear.split(".")[0]
            audio.export(os.path.join(save_path, basename + '.wav'), format="wav")




def wav_to_str():
    in_path = "wav_temp"
    r = sr.Recognizer()
    mp3_str = ""
    for wav in os.listdir(in_path):
        with sr.AudioFile(os.path.join(in_path, wav)) as source:
            audio = r.record(source)
        try:
            text = r.recognize_vosk(audio, language='en')
            mp3_str += json.loads(text)['text']
        except sr.UnknownValueError:
            print("无法识别音频内容")
        except sr.RequestError as e:
            print(f"请求错误; {e}")
    return mp3_str


