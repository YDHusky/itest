#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频处理模块
"""

import json
import os
import shutil
import time
from pathlib import Path

# 设置 Vosk 模型路径（必须在导入 speech_recognition 之前）
MODEL_PATH = Path(__file__).parent.parent / "model"
if MODEL_PATH.exists():
    os.environ["VOSK_MODEL_PATH"] = str(MODEL_PATH)

try:
    import speech_recognition as sr
    from pydub import AudioSegment
    try:
        from vosk import Model, KaldiRecognizer
        import wave
        HAS_VOSK = True
    except ImportError:
        HAS_VOSK = False
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    HAS_VOSK = False
    sr = None
    AudioSegment = None
    Model = None
    KaldiRecognizer = None

from loguru import logger

# Vosk 模型路径 - 使用相对路径便于打包
VOSK_MODEL_PATH = Path("./model")


# 默认临时目录
HEAR_TEMP_DIR = Path("./hear_temp")
WAV_TEMP_DIR = Path("./wav_temp")
LIB_PATH = Path("./lib")

# 缓存目录
CACHE_DIR = Path("./cache/audio")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def setup_lib_path():
    """设置库路径"""
    if LIB_PATH.exists():
        os.environ["PATH"] += os.pathsep + str(LIB_PATH.absolute())


def _get_file_hash(file_path: Path) -> str:
    """计算文件哈希值作为缓存键"""
    import hashlib
    
    if not file_path.exists():
        return ""
    
    # 使用文件名 + 修改时间 + 大小作为哈希输入
    stat = file_path.stat()
    hash_input = f"{file_path.name}_{stat.st_mtime}_{stat.st_size}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:16]


def _get_cache_path(cache_key: str) -> Path:
    """获取缓存文件路径"""
    return CACHE_DIR / f"{cache_key}.json"


def _load_from_cache(cache_key: str) -> str:
    """从缓存加载文本"""
    cache_path = _get_cache_path(cache_key)
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                text = data.get('text', '')
                logger.info(f"✓ 从缓存加载音频文本: {cache_key[:8]}...")
                return text
        except Exception as e:
            logger.debug(f"缓存读取失败: {e}")
    return ""


def _save_to_cache(cache_key: str, text: str):
    """保存文本到缓存"""
    try:
        cache_path = _get_cache_path(cache_key)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({'text': text, 'cached_at': time.time()}, f, ensure_ascii=False)
        logger.info(f"✓ 音频文本已缓存: {cache_key[:8]}...")
    except Exception as e:
        logger.debug(f"缓存保存失败: {e}")


def mp3_to_wav(input_dir: Path = None, output_dir: Path = None) -> bool:
    """
    将MP3文件转换为WAV格式
    
    Args:
        input_dir: MP3文件目录，默认 hear_temp
        output_dir: WAV输出目录，默认 wav_temp
    
    Returns:
        是否成功
    """
    if not HAS_DEPS:
        logger.error("缺少依赖，请安装: pip install pydub speechrecognition")
        return False
    
    setup_lib_path()
    
    input_dir = input_dir or HEAR_TEMP_DIR
    output_dir = output_dir or WAV_TEMP_DIR
    
    # 清理并创建输出目录
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_dir.exists():
        logger.warning(f"输入目录不存在: {input_dir}")
        return False
    
    mp3_files = list(input_dir.glob("*.mp3"))
    if not mp3_files:
        logger.warning(f"未找到MP3文件: {input_dir}")
        return False
    
    for mp3_file in mp3_files:
        try:
            audio = AudioSegment.from_mp3(mp3_file)
            wav_path = output_dir / f"{mp3_file.stem}.wav"
            audio.export(wav_path, format="wav")
            logger.debug(f"转换完成: {mp3_file.name} -> {wav_path.name}")
        except Exception as e:
            logger.error(f"转换失败 {mp3_file}: {e}")
    
    logger.info(f"MP3转WAV完成，共转换 {len(mp3_files)} 个文件")
    return True


def _wav_to_str_vosk(wav_file: Path) -> str:
    """使用 Vosk 直接识别单个 WAV 文件"""
    if not HAS_VOSK or not VOSK_MODEL_PATH.exists():
        return ""
    
    try:
        model = Model(str(VOSK_MODEL_PATH))
        
        with wave.open(str(wav_file), "rb") as wf:
            recognizer = KaldiRecognizer(model, wf.getframerate())
            
            text_parts = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text_parts.append(result.get('text', ''))
            
            # 获取最终结果
            final_result = json.loads(recognizer.FinalResult())
            text_parts.append(final_result.get('text', ''))
            
            return ' '.join(filter(None, text_parts))
    except Exception as e:
        logger.error(f"Vosk 识别失败 {wav_file}: {e}")
        return ""


def wav_to_str(input_dir: Path = None, language: str = 'en', cache_key: str = None) -> str:
    """
    将WAV文件转换为文字
    
    Args:
        input_dir: WAV文件目录，默认 wav_temp
        language: 识别语言，默认英文
        cache_key: 缓存键，如果提供且缓存存在则直接返回缓存结果
    
    Returns:
        识别出的文字
    """
    if not HAS_DEPS:
        logger.error("缺少依赖，请安装: pip install pydub speechrecognition")
        return ""
    
    # 检查缓存
    if cache_key:
        cached_text = _load_from_cache(cache_key)
        if cached_text:
            return cached_text
    
    input_dir = input_dir or WAV_TEMP_DIR
    
    if not input_dir.exists():
        logger.warning(f"输入目录不存在: {input_dir}")
        return ""
    
    wav_files = sorted(input_dir.glob("*.wav"))
    result_text = ""
    
    # 优先使用 Vosk 直接识别
    if HAS_VOSK and VOSK_MODEL_PATH.exists():
        logger.info(f"使用 Vosk 模型: {VOSK_MODEL_PATH}")
        for wav_file in wav_files:
            text = _wav_to_str_vosk(wav_file)
            result_text += text + " "
            logger.debug(f"识别完成: {wav_file.name}")
    else:
        # 降级使用 speech_recognition
        logger.warning("Vosk 模型未找到，尝试使用 speech_recognition")
        r = sr.Recognizer()
        
        for wav_file in wav_files:
            try:
                with sr.AudioFile(str(wav_file)) as source:
                    audio = r.record(source)
                
                try:
                    text = r.recognize_sphinx(audio, language=language)
                    result_text += text + " "
                    logger.debug(f"识别完成: {wav_file.name}")
                except sr.UnknownValueError:
                    logger.warning(f"无法识别音频内容: {wav_file.name}")
                except sr.RequestError as e:
                    logger.error(f"请求错误: {e}")
                    
            except Exception as e:
                logger.error(f"处理失败 {wav_file}: {e}")
    
    result_text = result_text.strip()
    
    # 保存到缓存
    if cache_key and result_text:
        _save_to_cache(cache_key, result_text)
    
    logger.info(f"语音识别完成，共识别 {len(wav_files)} 个文件")
    return result_text


class AudioProcessor:
    """音频处理器类"""
    
    def __init__(self, hear_dir: Path = None, wav_dir: Path = None):
        self.hear_dir = hear_dir or HEAR_TEMP_DIR
        self.wav_dir = wav_dir or WAV_TEMP_DIR
        self._current_cache_key: str = None
    
    def mp3_to_wav(self) -> bool:
        """将MP3转换为WAV（使用实例目录）"""
        return mp3_to_wav(self.hear_dir, self.wav_dir)
    
    def wav_to_str(self, cache_key: str = None) -> str:
        """将WAV转换为文字（使用实例目录）"""
        return wav_to_str(self.wav_dir, cache_key=cache_key)
    
    def process(self, mp3_files: list = None, audio_type: str = None, audio_id: str = None) -> str:
        """
        处理音频文件：转换MP3到WAV并识别文字
        
        Args:
            mp3_files: MP3文件路径列表，为None则处理hear_dir中的所有文件
            audio_type: 音频类型（如 'exam', 'mock', 'train'）
            audio_id: 音频ID（如考试ID）
        
        Returns:
            识别出的文字
        """
        # 生成缓存键
        cache_key = None
        if audio_type and audio_id and mp3_files:
            # 基于类型、ID和文件内容生成缓存键
            import hashlib
            hash_input = f"{audio_type}_{audio_id}"
            for mp3_path in sorted(mp3_files):
                file_hash = _get_file_hash(Path(mp3_path))
                hash_input += f"_{file_hash}"
            cache_key = hashlib.md5(hash_input.encode()).hexdigest()[:16]
            self._current_cache_key = cache_key
        
        # 检查缓存
        if cache_key:
            cached_text = _load_from_cache(cache_key)
            if cached_text:
                return cached_text
        
        if mp3_files:
            # 清理并重建hear_dir
            if self.hear_dir.exists():
                shutil.rmtree(self.hear_dir)
            self.hear_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制MP3文件
            for i, mp3_path in enumerate(mp3_files):
                dest = self.hear_dir / f"hear{i}.mp3"
                shutil.copy(mp3_path, dest)
        
        # 转换并识别
        if self.mp3_to_wav():
            result = self.wav_to_str(cache_key=cache_key)
            return result
        return ""
    
    def cleanup(self):
        """清理临时文件"""
        for dir_path in [self.hear_dir, self.wav_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                logger.debug(f"清理目录: {dir_path}")
    
    @staticmethod
    def clear_cache():
        """清除所有音频缓存"""
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            logger.info("音频缓存已清除")
    
    @staticmethod
    def get_cache_info() -> dict:
        """获取缓存信息"""
        if not CACHE_DIR.exists():
            return {'count': 0, 'size': 0}
        
        cache_files = list(CACHE_DIR.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'count': len(cache_files),
            'size': total_size / 1024  # KB
        }
