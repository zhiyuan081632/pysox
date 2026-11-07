#！Python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 13:30:33 2020

@author: zhihui.yzh
"""
import os
from pickle import FALSE, TRUE
import string
import sys
import getopt
from os import path
from typing import List
import wave
import struct
import numpy as np
import argparse
from datetime import datetime
from pydub import AudioSegment
import multiprocessing
import signal
import linecache
import re
import _thread
from pathlib import Path
import chardet
import subprocess
import csv
from collections import defaultdict
from scipy.io import wavfile


file_count=0

def get_filenames(in_path) -> List[str]:
    filenames = []
    try:
        assert in_path and os.path.exists(in_path), f'in_path must exist. in_path: {in_path}'
    except AssertionError as e:
        print(e)
        return []

    if os.path.isdir(in_path):
        # directory
        abs_dirpath = os.path.abspath(in_path)
        for root, dirs, files in os.walk(abs_dirpath):
            for file in files:
                # if "_16k" in root:
                filenames.append(os.path.join(root, file))
    elif os.path.isfile(in_path):
        # file
        filenames.append(os.path.abspath(in_path))
    else:
        print(f'in_path is neither a directory nor a file: {in_path}')
        return []

    return filenames

# 列出所有文件，并统计文件数目
def list_files(in_path):
    print('List all files')
    filenames = get_filenames(in_path)  # 获取文件名列表和文件数目
    for in_file in filenames:
        print(in_file)
    print(f'\nTotal number of files: {len(filenames)}')


# 将*.pcm文件转换为*.wav文件         
def pcm_convert_wav(in_path, out_path, ch=1, rate=16000, width=2):
    filenames = get_filenames(in_path)
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.pcm', '.raw', '.wav']:
            print('\nin:\t', in_file)  
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.wav'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)
            
            with open(in_file, 'rb') as raw_file:
                pcmdata = raw_file.read()
                with pywave.open(out_file_path, 'wb') as wav_file:
                    wav_file.setparams((ch, width, rate, 0, 'NONE', 'NONE'))
                    wav_file.writeframes(pcmdata)

    
# 将*.wav文件转换为*.pcm文件 
def wav_convert_pcm(in_path, out_path):
    print('Convert wav format to pcm')
    filenames = get_filenames(in_path)
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file)   
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.pcm'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)
            
            wav_in = AudioSegment.from_wav(in_file)
            wav_in.export(out_file_path, format='raw')


def wav_convert_pcm2(in_path, out_path, skip_bytes=44):
    """
    将 WAV 文件转换为 PCM 文件，跳过指定字节数的头部（默认44字节）。
    
    Args:
        in_path (str): 输入 WAV 文件路径或目录。
        out_path (str): 输出 PCM 文件路径或目录。
        skip_bytes (int): 跳过的字节数，默认44字节。
    """
    print('Convert wav format to pcm (skipping specified header bytes)')
    filenames = get_filenames(in_path)
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file)   
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.pcm'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)
            
            with open(in_file, 'rb') as wav_file:
                # 跳过指定字节数的头部
                wav_file.seek(skip_bytes)
                pcm_data = wav_file.read()
                
            with open(out_file_path, 'wb') as pcm_file:
                pcm_file.write(pcm_data)

def other2wav(in_file):
# for in_file in filenames:
    _, in_type = os.path.splitext(in_file)
    if in_type.lower() in ['.mp3', '.aac', '.m4a', '.amr', '.mp4', '.wav', '.mkv', '.ogg', '.flac']:      
        print('\nin:\t', in_file) 
        in_name = os.path.basename(in_file)       
        out_file_name = os.path.splitext(in_name)[0] + '.wav'
        relative_path = os.path.dirname(os.path.relpath(in_file, in_path))
        if not os.path.exists(os.path.join(out_path, relative_path)):
            try:
                os.makedirs(os.path.join(out_path, relative_path))
            except FileExistsError:
                pass
        out_file_path = os.path.join(out_path, relative_path, out_file_name)
        
        print('out:\t', out_file_path)
        # ffmpeg command
        # ffmpeg -i input.wav -ac 1 -ar 16000 -y output.wav
        cmd_str = [
            'ffmpeg',
            '-i', in_file,
            '-ac', "1",
            '-ar', "16000",
            '-y', 
            out_file_path
        ]

        print("cmd:\t", ' '.join(cmd_str))
        subprocess.run(cmd_str, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  
            
# 将其他格式音频转换为*.wav文件
def other_convert_wav(in_path, out_path, ch=1, rate=16000, width=2):
    print('Convert other format to wav')
    filenames = get_filenames(in_path)

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        pool.map(other2wav, filenames)
    
# 读取wav文件的格式信息和音频数据，手动解析RIFF块，
# 兼容PCM(0x0001)、IEEE float(0x0003)及WAVE_FORMAT_EXTENSIBLE(0xFFFE)格式
# （Python内置wave模块和pywave仅支持PCM，遇到0xFFFE会报 unknown format: 65534）
def wav_read_fmt_data(in_file):
    WAVE_FORMAT_PCM = 0x0001
    WAVE_FORMAT_IEEE_FLOAT = 0x0003
    WAVE_FORMAT_EXTENSIBLE = 0xFFFE

    fmt_chunk = None
    audio_data = None
    with open(in_file, 'rb') as f:
        riff_header = f.read(12)
        if len(riff_header) < 12 or riff_header[0:4] != b'RIFF' or riff_header[8:12] != b'WAVE':
            raise wave.Error('not a RIFF/WAVE file: %s' % in_file)
        while fmt_chunk is None or audio_data is None:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                break
            chunk_id = chunk_header[0:4]
            chunk_size = struct.unpack('<I', chunk_header[4:8])[0]
            if chunk_id == b'fmt ':
                fmt_chunk = f.read(chunk_size)
            elif chunk_id == b'data':
                audio_data = f.read(chunk_size)
            else:
                f.seek(chunk_size, 1)  # 跳过其他块（LIST/fact等）
            if chunk_size & 1:
                f.seek(1, 1)  # 块大小按2字节对齐，跳过填充字节

    if fmt_chunk is None or audio_data is None:
        raise wave.Error('fmt chunk and/or data chunk missing: %s' % in_file)

    format_tag, nchannels, framerate = struct.unpack_from('<HHI', fmt_chunk, 0)
    block_align = struct.unpack_from('<H', fmt_chunk, 12)[0]
    if format_tag == WAVE_FORMAT_EXTENSIBLE:
        # 真实格式存放在SubFormat GUID的前2字节
        format_tag = struct.unpack_from('<H', fmt_chunk, 24)[0]
    if format_tag not in (WAVE_FORMAT_PCM, WAVE_FORMAT_IEEE_FLOAT):
        raise wave.Error('unsupported format tag: %r' % (format_tag,))
    if nchannels == 0 or block_align % nchannels:
        raise wave.Error('bad fmt chunk: %s' % in_file)

    sampwidth = block_align // nchannels  # 每个采样点字节数
    return format_tag, nchannels, framerate, sampwidth, audio_data


# 写入44字节标准头的wav文件
def write_wav44(out_file, format_tag, nchannels, framerate, sampwidth, audio_data):
    data_size = len(audio_data)
    byte_rate = framerate * nchannels * sampwidth
    block_align = nchannels * sampwidth
    with open(out_file, 'wb') as f:
        f.write(struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF', data_size + 36,
            b'WAVE',
            b'fmt ', 16,
            format_tag, nchannels, framerate,
            byte_rate, block_align, sampwidth * 8,
            b'data', data_size
        ))
        f.write(audio_data)


# 将*.wav文件转换为44字节头的*.wav文件
def wav_convert_wav44(in_path, out_path):
    print('Convert wav format to wav with 44 Bytes header')
    filenames = get_filenames(in_path)
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.wav'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)

            # 手动解析RIFF块，兼容WAVE_FORMAT_EXTENSIBLE(0xFFFE)格式
            format_tag, nchannels, framerate, sampwidth, audio_data = wav_read_fmt_data(in_file)

            # 写入44字节标准头的wav文件
            write_wav44(out_file_path, format_tag, nchannels, framerate, sampwidth, audio_data)



def wav_convert_wav44_2(in_path, out_path):
    import pywave
    print('Convert wav format to wav with 44 Bytes header')
    filenames = get_filenames(in_path)
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.wav'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)

            # in_wave = pywave.open(in_file, 'rb')
            # params = in_wave.getparams()
            # nchannels, sampwidth, framerate, nframes = params[:4]
            # str_data = in_wave.readframes(nframes) #read data
            # with pywave.open(out_file_path, 'wb') as out_wav:
            #     out_wav.setparams((nchannels, sampwidth, framerate, 0, 'NONE', 'NONE'))
            #     out_wav.writeframes(str_data)
            # in_wave.close()
            with wave.open(in_file, 'rb') as wav_file:
                # 读取原始参数
                params = wav_file.getparams()
                n_channels, sampwidth, framerate, n_frames = params[:4]
                
                # 计算关键值
                byte_rate = framerate * n_channels * sampwidth
                block_align = n_channels * sampwidth
                
                # 计算数据大小（总帧数×每帧字节数）
                data_size = n_frames * sampwidth
                # 计算文件大小（数据大小+36字节头）
                file_size = data_size + 36
                
                # 读取原始音频数据
                wav_file.setpos(0)  # 确保从文件开头读取
                audio_data = wav_file.readframes(n_frames)
            
             # 写入新文件
        with wave.open(out_file_path, 'wb') as new_wav:
            # 设置参数（不包含n_frames）
            new_wav.setnchannels(n_channels)
            new_wav.setsampwidth(sampwidth)
            new_wav.setframerate(framerate)
            
            # 写入44字节标准头
            new_wav.writeframesraw(struct.pack(
                '<4sI4s4sI4sIHHIIHH4sI',
                b'RIFF', file_size,
                b'WAVE',
                b'fmt ', 16,
                1, n_channels, framerate,
                byte_rate, block_align, sampwidth * 8,
                b'data', data_size
            ))
            
            # 写入音频数据
            new_wav.writeframesraw(audio_data)
    

# 将*.wav文件转换为*.ogg文件
def wav_convert_ogg(in_path, out_path):
    print('Convert wav format to ogg')
    filenames = get_filenames(in_path)
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.ogg'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)
            # ffmpeg command
            # ffmpeg -i input.wav -acodec libvorbis -b:a 34k output.ogg
            cmd_str = [
                'ffmpeg',
                '-i', in_file,
                '-acodec', 'libvorbis',
                '-b:a', '34k',
                out_file_path
            ]

            print("cmd:\t", ' '.join(cmd_str))
            subprocess.run(cmd_str, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  
        else:
            print("Unsupported file type!") 

# wav文件重采样：采样率和采样位变换
def wav_resample(in_path, out_path, rate=16000, width=2):
    print('Resample wav format')
    filenames = get_filenames(in_path)
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.wav'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)
            
            wav_in = AudioSegment.from_wav(in_file)
            wav_out = wav_in.set_frame_rate(rate)
            wav_out = wav_out.set_sample_width(width)
            wav_out.export(out_file_path, format='wav')


# 在wav文件前插入静音xx ms
def wav_insert_silence(in_path, out_path, silence_ms=1000):
    print('Insert silence')
    filenames = get_filenames(in_path)
    
    silence_file_name = 'silence.wav'
    # if not os.path.exists(silence_file_name):
    #     wav_silence = AudioSegment.silent(duration=int(silence_ms), frame_rate=16000) 
    #     wav_silence.export('sil.wav', format='wav')
    #     silence_mono = wav_silence.set_channels(1)
    # else:
    silence_mono = AudioSegment.from_wav(silence_file_name)
    silence_mono.export(silence_file_name, format="wav")
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.wav'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)
            
            wav_in = AudioSegment.from_wav(in_file)
            wav_out = silence_mono + wav_in
            wav_out.export(out_file_path, format='wav')

    os.remove(silence_file_name)

# wav文件内容复制n次
def wav_repeat(in_path, rep_num=1):
    print('Reapeat wav file')
    print('rep_num: ', rep_num)
    filenames = get_filenames(in_path)
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.wav'
            out_file_path = os.path.join(out_path, out_file_name)
            
            wav_in = AudioSegment.from_wav(in_file)
            wav_in = wav_in * rep_num
            wav_in.export(out_file_path, format='wav')
            print('out:\t', out_file_path)


# 截取前/后xx ms音频
def wav_extract(in_path, out_path, ext_ms=1000):
    print('Extract wav file')
    print('ext_ms: ', ext_ms)
    filenames = get_filenames(in_path)

    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.wav'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)
            
            wav_in = AudioSegment.from_wav(in_file)
            
            # 正数为前xx ms，负数为后xx ms
            if ext_ms >= 0:
                wav_ext = wav_in[:ext_ms]
            else:
                wav_ext = wav_in[ext_ms:]
            wav_ext.export(out_file_path, format='wav')


# wav文件音频倍速
def wav_speed(in_path, out_path, speed=1.0):
    from audiostretchy.stretch import stretch_audio
    
    print('Speed wav file')
    print('speed: ', speed)
    filenames = get_filenames(in_path)

    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.wav'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)
            
            ## spawn方法： 变语速，也变音高
            # wav_in = AudioSegment.from_wav(in_file)
            # wav_out = wav_in._spawn(wav_in.raw_data, overrides={"frame_rate": int(wav_in.frame_rate * speed)}).set_frame_rate(wav_in.frame_rate)
            # wav_out.export(out_file_path, format='wav')
            
            # stretchy方法：变语速，不变音高
            try:
                ratio = 1 / speed
                print(f"Ratio: {ratio:.2f}")
                stretch_audio(in_file, out_file_path, ratio=ratio)
            except Exception as e:
                print(f"Error processing {in_file}: {e}")


# wav文件音频增益    
def wav_gain(in_path, out_path, gain_db=1.0):
    print('Speed wav file')
    print('gain_db: ', gain_db)
    filenames = get_filenames(in_path)

    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.wav'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)
            
            wav_in = AudioSegment.from_wav(in_file)
            wav_out = wav_in + gain_db
            wav_out.export(out_file_path, format='wav')


# wav文件拆分成n个单通道wav文件 
def wav_split_mono(in_path, out_path):
    print('Split wav to mono format')
    filenames = get_filenames(in_path)
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.mp3', '.aac', '.m4a', '.amr', '.mp4', '.wav', '.mkv', '.ogg']:   
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)    
            wav_in = AudioSegment.from_wav(in_file)
            mono_data = wav_in.split_to_mono()
            for ch in range(wav_in.channels):
                wav_file_name = in_name.replace(in_type, f'_ch{ch}.wav')
                out_file_path = os.path.join(out_path, wav_file_name)
                print('out:\t', out_file_path)
                mono_data[ch].export(out_file_path, format='wav')

# # 将n个单通道wav文件合并成一个多通道wav文件 
# def wav_merge_mono(in_path, out_path):
#     print('Merge mono file to multi file')
#     filenames = get_filenames(in_path)
    
#     wav_in = [AudioSegment.empty()]*len(filenames)
#     for ch in range(len(filenames)):
#         wav_in[ch] = AudioSegment.from_wav(filenames[ch])
#     out_file_name = os.path.join(out_path, "merged_nono.wav")
#     wav_out = AudioSegment.from_mono_audiosegments(*wav_in)
#     wav_out.export(out_file_name, format='wav')
#     print('out:\t', out_file_name)
#     return out_file_name

def wav_merge_multi(in_path, out_path):
    """
    将多个wav文件合并成一个多声道文件。

    Args:
        in_path (str): 输入文件路径，包含多个文件的文件夹路径。
        out_path (str): 输出文件路径，合并后的多声道文件将保存于此路径。

    """
    print('Merge multi wav file to one multi channel file')
    filenames = get_filenames(in_path)
    
    mono_segments = []
    for filename in filenames:
        wav = AudioSegment.from_wav(filename)
        print('sample rate:\t', wav[0].frame_rate)
        print('sample bit:\t', wav[0].sample_width*8)
        mono_segments.extend(wav.split_to_mono())
    
    out_file_name = os.path.join(out_path, "merged.wav")
    wav_out = AudioSegment.from_mono_audiosegments(*mono_segments)
    wav_out.export(out_file_name, format='wav')
    print('out:\t', out_file_name)
    return out_file_name


# 批量拼接wav列表，并有静音xx ms
def wav_cat_silence2(wav_list, silence_ms=1000):
    print('Wav cat wavlist')
    
    if silence_ms is None:
        silence_ms = 1000
        
    concatenated_audio = AudioSegment.empty()
    for wav_path in wav_list:
        if wav_path.endswith('.wav'): 
            print("wav file: ", wav_path)
            audio = AudioSegment.from_wav(wav_path)
            concatenated_audio += audio
            
            # 添加静音
            silence = AudioSegment.silent(duration=float(silence_ms)) 
            concatenated_audio += silence
    first_file_path = wav_list[0] 
    out_file_dir = os.path.abspath(os.path.join(os.path.dirname(first_file_path), os.pardir))
    out_file_name = os.path.join(out_file_dir, 'concatenated_audio.wav')
    print(out_file_name)
    concatenated_audio.export(out_file_name, format="wav")
    return out_file_name

def wav_cat_silence(in_path, out_path, silence_ms=1000):
    print('Split wav to mono format')
    print('silence_ms: ', silence_ms)
    filenames = get_filenames(in_path)
    
    silence = AudioSegment.silent(duration=float(silence_ms)) 
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:   
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)    
            out_file_name = os.path.join(out_path, in_name)
            print('out:\t', out_file_name)
            
            wav_in = AudioSegment.from_wav(in_file)
            wav_out = silence + wav_in
            wav_out.export(out_file_name, format='wav')

        
# 将n个单通道wav文件合并成一个多通道wav文件 
def wav_split_mux(in_path, out_path, mux_ch):
    print('Mux wav file')
    print('mux ch: ', mux_ch)
    filenames = get_filenames(in_path)

    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.wav']:
            print('\nin:\t', in_file) 
            in_name = os.path.basename(in_file)       
            out_file_name = os.path.splitext(in_name)[0] + '.wav'
            out_file_path = os.path.join(out_path, out_file_name)
            print('out:\t', out_file_path)
            
            wav_in = AudioSegment.from_wav(in_file)
            wav_tmp = [AudioSegment.empty()]*len(mux_ch)
            if(wav_in.channels < len(mux_ch)):
                print('wav channel less than mux_ch')
                return
            for ch in range(len(mux_ch)):
                wav_tmp[ch] = wav_in.split_to_mono()[int(mux_ch[ch])]
            wav_out = AudioSegment.from_mono_audiosegments(*wav_tmp)
            wav_out.export(out_file_name, format='wav')


# 将多通道wav文件混音成一个单通道wav文件
def wav_mix_to_mono(in_path: str, out_path: str, method: str = 'average') -> None:
    filenames = get_filenames(in_path)

    for in_file in filenames:
        sample_rate, audio_data = wavfile.read(in_file)
        
        if audio_data.ndim == 1:
            mono_audio = audio_data
        else:
            if method == 'average':
                mono_audio = np.mean(audio_data, axis=1)
            elif method == 'sum':
                mono_audio = np.sum(audio_data, axis=1)
            elif method == 'left':
                mono_audio = audio_data[:, 0]
            elif method == 'right':
                mono_audio = audio_data[:, -1]
            else:
                raise ValueError("不支持的混音方法")
            
        mono_audio = mono_audio.astype(audio_data.dtype)
        in_name = os.path.basename(in_file)    
        out_file_path = os.path.join(out_path, in_name)
        wavfile.write(out_file_path, sample_rate, mono_audio)
        print(f'out:\t', out_file_path)


def parse_offset_time_to_seconds(offset_time_str):
    """将时:分:秒[.毫秒]格式的字符串转换为秒（浮点数）
    
    支持 'HH:MM:SS.mmm'、'HH:MM:SS'、'MM:SS'、'SS' 等写法，毫秒部分可省略
    """
    parts = offset_time_str.split(':')
    if len(parts) == 3:
        hours, minutes, rest = parts
    elif len(parts) == 2:
        hours, minutes, rest = '0', parts[0], parts[1]
    else:
        hours, minutes, rest = '0', '0', parts[0]
    if '.' in rest:
        seconds_s, frac = rest.split('.')
        seconds = float(seconds_s)
        milliseconds = float('0.' + frac)  # 小数部分按十进制秒处理，'.5' 与 '.500' 均为半秒
    else:
        seconds = float(rest)
        milliseconds = 0.0
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + seconds + milliseconds
    return total_seconds

def format_seconds_to_hms(seconds):
    """将秒（浮点数）转换为时:分:秒.毫秒格式的字符串"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = seconds % 60
    milliseconds = int((seconds_part - int(seconds_part)) * 1000)  # 提取毫秒部分
    return f"{hours:02}:{minutes:02}:{int(seconds_part):02}.{milliseconds:03}"

import soundfile as sf


# 将原始音频根据标注文件.textgrid进行切分    
def wav_textgrid_cut(in_path, out_path, textgrid_file, offset_time='00:00:00.000'):
    print('TextGrid cut wav file')
    filenames = get_filenames(in_path)
    
    offset_seconds = parse_offset_time_to_seconds(offset_time)
    
    name_counts = defaultdict(int)
    
    for wav_file in filenames:
        # 使用 soundfile 读取音频数据
        data, samplerate = sf.read(wav_file)
        print(f"Sample rate: {samplerate}")
        print(f"Channels: {data.shape[1] if data.ndim > 1 else 1}")
        
        time_start = 0
        time_end = 0
        wav_id = 0
        item_dir = ''
        intervals = ''
        in_dir_name, in_file_name = os.path.split(wav_file)
        with open(textgrid_file, 'rb') as f:
            result = chardet.detect(f.read())
            encoding = result['encoding']
        fp_textgrid = open(textgrid_file, "r", encoding=encoding)
        fp_textgrid.readline()

        annot_file = os.path.join(out_path, "annot.txt")
        fp_annote = open(annot_file, "a", encoding='utf-8')
        
        current_tier_name = None
        
        for line in fp_textgrid:
            line = line.strip()
            
            if (re.search(r'name = "(.+?)"', line) != None):
                current_tier_name_0bj = re.search(r'name = "(.+?)"', line)
                current_tier_name = current_tier_name_0bj.group(1)
                print(current_tier_name)
            
            if(re.match("xmin = (.*)", line) != None):
                start0bj = re.match("xmin = (.*)", line)
                time_start_seconds = round(float(start0bj.group(1)), 3)
            if(re.match("xmax = (.*)", line) != None):
                end0bj = re.match("xmax = (.*)", line)
                time_end_seconds = round(float(end0bj.group(1)), 3)
            if(re.match("text = (.*)", line) != None):
                text0bj = re.match("text = (.*)", line)
                text = eval(text0bj.group(1))
                clean_text = text.replace('\t', '').replace('\n', '').replace('\\', '').replace('/', '').replace(' ', '')
                if(len(clean_text)):
                    wav_id = wav_id + 1
                    split_wav_name = f"{wav_id}_{current_tier_name}_{clean_text}_{time_start_seconds}-{time_end_seconds}.wav"
                    split_wav_file = os.path.join(out_path, split_wav_name)
                    time_start_hms = format_seconds_to_hms(time_start_seconds + offset_seconds)
                    time_end_hms = format_seconds_to_hms(time_end_seconds + offset_seconds)
                    print(f'{wav_id}, {time_start_hms}~{time_end_hms}\t{split_wav_file}')
                    
                    # 计算切分起始和结束的样本点
                    start_sample = int((time_start_seconds + offset_seconds) * samplerate)
                    end_sample = int((time_end_seconds + offset_seconds) * samplerate)
                    
                    # 切分音频数据
                    split_data = data[start_sample:end_sample, :] if data.ndim > 1 else data[start_sample:end_sample]
                    
                    # 保存切分后的音频
                    sf.write(split_wav_file, split_data, samplerate)
                    
                    fp_annote.write(split_wav_name + '\t' + text + '\n')
                    
                    # 统计每个音区的唤醒词数量
                    if clean_text == '嗨领克':
                        name_counts[current_tier_name] += 1

        fp_textgrid.close()
        fp_annote.close()
    
    print("\nValid label per name:")
    for name, count in name_counts.items():
        print(f"{name}: {count}")


def video_textgrid_cut(in_path, out_path, textgrid_file, offset_time='00:00:00.000'):
    """
    根据 TextGrid 标注文件，对 MP4 视频进行切分，并确保输出音频为单通道、16kHz。
    
    Args:
        in_path (str): 输入视频文件或目录路径（支持 .mp4, .mkv 等 ffmpeg 支持的格式）
        out_path (str): 输出目录
        textgrid_file (str): TextGrid 标注文件路径
        offset_time (str): 时间偏移，格式 'HH:MM:SS.mmm'
    """
    print('TextGrid cut video file (audio to mono 16kHz)')
    filenames = get_filenames(in_path)
    
    offset_seconds = parse_offset_time_to_seconds(offset_time)
    name_counts = defaultdict(int)

    # 读取 TextGrid 文件编码
    with open(textgrid_file, 'rb') as f:
        encoding = chardet.detect(f.read())['encoding']
    
    for video_file in filenames:
        _, ext = os.path.splitext(video_file)
        if ext.lower() not in ['.mp4', '.mkv', '.avi', '.mov']:  # 可按需扩展
            continue
        
        print(f'\nProcessing video: {video_file}')
        current_tier_name = None
        intervals = []

        with open(textgrid_file, "r", encoding=encoding) as fp_textgrid:
            lines = fp_textgrid.readlines()

        # 解析 TextGrid 内容（简化版，假设 tier 结构清晰）
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if re.search(r'name = "(.+?)"', line):
                current_tier_name_obj = re.search(r'name = "(.+?)"', line)
                current_tier_name = current_tier_name_obj.group(1)
            elif re.match(r"xmin = (.*)", line):
                start_sec = float(re.match(r"xmin = (.*)", line).group(1))
                i += 1
                end_sec = float(re.match(r"xmax = (.*)", lines[i].strip()).group(1))
                i += 1
                text_line = lines[i].strip()
                text_obj = re.match(r"text = (.*)", text_line)
                if text_obj:
                    try:
                        text = eval(text_obj.group(1))
                    except:
                        text = ""
                    clean_text = text.replace('\t', '').replace('\n', '').replace('\\', '').replace('/', '').replace(' ', '')
                    if clean_text:
                        intervals.append({
                            'tier': current_tier_name,
                            'start': start_sec,
                            'end': end_sec,
                            'text': clean_text
                        })
            i += 1

        # 执行视频切分
        annot_file = os.path.join(out_path, "video_annot.txt")
        for idx, seg in enumerate(intervals, 1):
            start_s = seg['start'] + offset_seconds
            end_s = seg['end'] + offset_seconds
            duration_s = end_s - start_s
            clean_text = seg['text']
            tier = seg['tier']

            # 构造安全的文件名（避免非法字符）
            safe_text = "".join(c for c in clean_text if c.isalnum() or c in ('_', '-'))
            if not safe_text:
                safe_text = "segment"

            start_round = round(seg['start'], 3)
            end_round = round(seg['end'], 3)
            out_name = f"{idx}_{tier}_{safe_text}_{start_round}-{end_round}.mp4"
            out_path_full = os.path.join(out_path, out_name)

            # ffmpeg 命令：-ss 放在 -i 前实现快速定位，-t 指定时长，
            # 视频重编码以保证精确到帧的切分（copy 模式只能在关键帧切分）
            cmd = [
                'ffmpeg',
                '-y',
                '-ss', str(start_s),
                '-i', video_file,
                '-t', str(duration_s),
                '-map', '0:v',          # 保留视频流
                '-map', '0:a',          # 保留音频流
                '-c:v', 'libx264',      # 视频重编码（精确切分）
                '-preset', 'fast',      # 编码速度
                '-c:a', 'aac',          # 音频重编码为 AAC（兼容 MP4）
                '-ac', '1',             # 单通道 (mono)
                '-ar', '16000',         # 16kHz 采样率
                '-b:a', '64k',          # 音频码率
                out_path_full
            ]

            print(f"Cutting: {start_s:.3f}s ~ {end_s:.3f}s -> {out_name}")
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                print(f"FFmpeg error on segment {idx}: {e}")
                continue

            # 记录标注（与 wav_textgrid_cut 一致）
            with open(annot_file, 'a', encoding='utf-8') as af:
                af.write(out_name + '\t' + seg['text'] + '\n')

            if clean_text == '嗨领克':
                name_counts[tier] += 1

    print("\nValid label per name:")
    for name, count in name_counts.items():
        print(f"{name}: {count}")
        
       
def video_time_cut(in_path, out_path, start_time='00:00:00.000', end_time=None):
    """
    按指定时间段切分 MP4 视频文件。
    
    Args:
        in_path (str): 输入视频文件或目录路径
        out_path (str): 输出目录
        start_time (str): 起始时间，格式 'HH:MM:SS.mmm'，默认 00:00:00.000
        end_time (str): 结束时间，格式 'HH:MM:SS.mmm'，默认到文件末尾
    """
    print('Video time cut')
    filenames = get_filenames(in_path)
    start_s = parse_offset_time_to_seconds(start_time)
    end_s = parse_offset_time_to_seconds(end_time) if end_time else None

    for video_file in filenames:
        _, ext = os.path.splitext(video_file)
        if ext.lower() not in ['.mp4', '.mkv', '.avi', '.mov']:
            continue
        
        print(f'\nProcessing: {video_file}')
        in_name = os.path.basename(video_file)
        name_no_ext = os.path.splitext(in_name)[0]

        # 构造输出文件名
        start_tag = start_time.replace(':', '').replace('.', '')
        if end_s is not None:
            end_tag = end_time.replace(':', '').replace('.', '')
            out_name = f"{name_no_ext}_{start_tag}-{end_tag}{ext}"
        else:
            out_name = f"{name_no_ext}_{start_tag}-end{ext}"
        out_file = os.path.join(out_path, out_name)

        # 构造 ffmpeg 命令
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_s),
            '-i', video_file,
        ]
        if end_s is not None:
            duration_s = end_s - start_s
            if duration_s <= 0:
                print(f'  Skip: end_time ({end_time}) <= start_time ({start_time})')
                continue
            cmd += ['-t', str(duration_s)]

        cmd += [
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-c:a', 'aac',
            '-b:a', '128k',
            out_file
        ]

        start_hms = format_seconds_to_hms(start_s)
        end_hms = format_seconds_to_hms(end_s) if end_s else 'end'
        print(f'  {start_hms} ~ {end_hms} -> {out_name}')
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f'  out: {out_file}')
        except subprocess.CalledProcessError as e:
            print(f'  FFmpeg error: {e}')


# 将视频文件按时间间隔进行切分，时长单位为秒
def video_interval_cut(in_path, out_path, interv_seconds=60):
    print('Video interval cut')
    filenames = get_filenames(in_path)
    interv_seconds = float(interv_seconds)

    for video_file in filenames:
        _, ext = os.path.splitext(video_file)
        if ext.lower() not in ['.mp4', '.mkv', '.avi', '.mov']:
            continue

        print(f'\nProcessing: {video_file}')

        # 用 ffprobe 获取视频总时长
        try:
            duration_s = float(subprocess.check_output([
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_file
            ]).decode('utf-8').strip())
        except subprocess.CalledProcessError as e:
            print(f'  ffprobe error: {e}')
            continue
        print(f'duration: {duration_s:.2f}s')
        print(f'interv seconds: {interv_seconds:.0f}s')

        # 计算切分段数
        total_segments = int(duration_s // interv_seconds) + (1 if duration_s % interv_seconds > 0 else 0)
        print(f'total segments: {total_segments}')

        in_name = os.path.basename(video_file)
        name_no_ext = os.path.splitext(in_name)[0]

        for cnt in range(total_segments):
            start_s = cnt * interv_seconds
            end_s = min(start_s + interv_seconds, duration_s)
            out_file_name = f'{name_no_ext}_{interv_seconds:.0f}s_{cnt}{ext}'
            out_file = os.path.join(out_path, out_file_name)

            # -ss 放在 -i 前实现快速定位，视频重编码保证精确切分
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_s),
                '-i', video_file,
                '-t', str(end_s - start_s),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-c:a', 'aac',
                '-b:a', '128k',
                out_file
            ]

            print(f'out: {cnt+1}/{total_segments}:\t{out_file}')
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                print(f'  FFmpeg error: {e}')


# 将原始音频根据时长进行切分，时长单位为秒
def wav_cut(in_file, interv_seconds=60):
    _, in_type = os.path.splitext(in_file)
    if in_type.lower() in ['.wav']:
        print('\nin:\t', in_file) 
        in_name = os.path.basename(in_file)       
        
        time_start = 0
        time_end = 0
        wav_id = 0
        item_dir = ''
        intervals = ''

        wav_in = AudioSegment.from_wav(in_file)
        frame_count = wav_in.frame_count()
        frame_rate = wav_in.frame_rate
        duration_ms = len(wav_in)  # 音频总时长（毫秒）
        duration_seconds = duration_ms / 1000.0  # 音频总时长（秒）
        print(f"duration: {duration_seconds:.2f}s ({duration_ms}ms)")
        print(f"interv seconds: {interv_seconds}s")
        
        # 计算切分段数
        total_segments = int(duration_seconds // interv_seconds) + (1 if duration_seconds % interv_seconds > 0 else 0)
        print(f"total segments: {total_segments}")

        cnt = 0 
        time_start_ms = 0
        
        while(time_start_ms < duration_ms):
            time_end_ms = min(time_start_ms + interv_seconds * 1000, duration_ms)
            out_file_name = in_name.replace(in_type, ('_' + str(int(interv_seconds)) + 's' + '_' + str(cnt) + '.wav'))
            # wav_out_name = os.path.join(out_path, out_file_name)
            
            relative_path = os.path.dirname(os.path.relpath(in_file, in_path))
            if not os.path.exists(os.path.join(out_path, relative_path)):
                try:
                    os.makedirs(os.path.join(out_path, relative_path))
                except FileExistsError:
                    pass
            out_file_path = os.path.join(out_path, relative_path, out_file_name)
            
            print(f'out: {cnt+1}/{total_segments}:\t{out_file_path}')
            segment = wav_in[time_start_ms:time_end_ms]
            segment.export(out_file_path, format="wav")
            
            time_start_ms = time_end_ms  # 推进切分起点，否则死循环重复切第 0 段
            cnt += 1

def wav_interval_cut(in_path, out_path, interv_seconds=60.0):
    print('Audio interval cut')
    filenames = get_filenames(in_path)
    interv_seconds = float(interv_seconds)

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        # 必须把 interv_seconds 传给 wav_cut，否则永远按默认 60s 切分
        pool.starmap(wav_cut, [(f, interv_seconds) for f in filenames])


# 计算音频时长，并写入到文件中 
def compute_wav_duration(in_path, out_path):
    print('Compute the duration of all files')
    filenames = get_filenames(in_path)
    total_dur_seconds = 0.0
    duration_info = []
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.mp3', '.aac', '.m4a', '.amr', '.mp4', '.wav', '.mkv', '.ogg']:   
            print('\nin:\t', in_file) 
        try:
            audio = AudioSegment.from_file(in_file, format=in_type.lower())
            duration = len(audio) / 1000 # ms to s
            total_dur_seconds += duration
            print(f"{in_file}\t{duration} seconds")
            duration_info.append(f"{in_file}\t{duration}")  # 收集时长信息
        except Exception as e:
            print(f"Error reading {in_file}: {e}")
            
    # 创建输出文件的路径
    # out_file = os.path.join(out_path, 'duration.txt')
    out_file = 'duration.txt'
    if os.path.exists(out_file):
        os.remove(out_file)

    # 统一写入文件
    with open(out_file, 'w', newline='') as f:
        for info in duration_info:
            f.write(info + '\n')
        total_dur_seconds = round(total_dur_seconds, 3)
        total_dur_hours = total_dur_seconds / 3600
        f.write(f"\nTotal duration: {total_dur_seconds} seconds, {round(total_dur_hours, 2)} hours")
    print('\nWrite duration to:\t', out_file)
    print(f"Total duration: {total_dur_seconds} seconds, {round(total_dur_hours, 2)} hours")

# 解析音频文件，包括通道、采样率，采样位、时长等信息
def get_audio_infor(in_file):
    command = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-show_entries', 'stream=codec_name,sample_rate,channels,bit_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        in_file
    ]

    try:
        output = subprocess.check_output(command).decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        print("Error running ffprobe:", e)
        exit(1)

    lines = output.split('\n')
    audio_info = {
        'filename': in_file,
        'sample_rate': None,
        'channels': None,
        'sample_bit': None,
        'bit_rate': None,
        'duration': None
    }

    if lines:
        format = lines[0]
        if 'pcm_s16le' in format:
            audio_info['sample_bit'] = 16
        elif 'pcm_float' in format:
            audio_info['sample_bit'] = 32
        else:
            audio_info['sample_bit'] = 'unknown'
        audio_info['sample_rate'] = int(lines[1])  
        audio_info['channels'] = int(lines[2])  
        audio_info['bit_rate'] = float(lines[3])
        audio_info['duration'] = float(lines[4])
        
    missing_keys = [key for key, value in audio_info.items() if value is None]
    if missing_keys:
        raise ValueError(f"Missing audio information: {', '.join(missing_keys)}")

    return audio_info
    

def profile_audio(in_path, out_path):   
    print('Profile audio files')
    filenames = get_filenames(in_path)
    
    for in_file in filenames:
        _, in_type = os.path.splitext(in_file)
        if in_type.lower() in ['.mp3', '.aac', '.m4a', '.amr', '.mp4', '.wav', '.mkv', '.ogg']:    
            try:
                profile = get_audio_infor(in_file)
                for key, value in profile.items():
                    print(f"{key}: {value}")
                    
                 # set out file path  
                out_file = os.path.join(out_path, "profile.csv")
                print('out file: ', out_file)

                with open(out_file, 'a', newline='', encoding='gbk') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=profile.keys())
                    if os.path.getsize(out_file) == 0: 
                        writer.writeheader()
                    writer.writerow(profile)

            except Exception as e:
                print(f"Error profiling {in_path}: {e}")


# 首先将某文件或某目录下的非wav格式文件转换成wav格式文件
# 然后对wav文件进行操作：拼接、截取、倍速等
if __name__ == '__main__':

    func_des='''
        \n==================================pysox==================================
        建议先转换成成wav文件再进行其他处理
        支持以下操作：
        list        ----    列出文件
        pcm2wav     ----    pcm转换为wav
        wav2pcm     ----    wav转换为pcm
        oth2wav     ----    其他格式转换为wav
        wav2wav44   ----    wav转换为44字节头WAV
        wav2ogg     ----    wav转换为ogg
        repeat      ----    语音复制拷贝
        extract      ----   截取语音片段
        speed       ----    倍速
        gain        ----    放大dB
        mux         ----    提取某些通道
        mix         ----    将多通道音频混音成单通道音频
        mono        ----    拆分成单通道文件
        cat         ----    拼接成长音频, 默认静音间隔为1秒 
        resample    ----    转换采样率
        textgridcut ----    按标注文件TextGrid切分音频
        videotextgridcut ---- 按TextGrid切分MP4视频
        videocut    ----    按时间间隔切分MP4视频
        videotimecut ----   按时间段(start_time~end_time)切分MP4视频
        textcut     ----    按标注文件Text切分音频
        intervcut   ----    按时间间隔切分音频
        merge       ----    多个单通道文件合并成多通道
        insertsil   ----    文件头插入静音
        duration    ----    计算音频文件时长
        profile     ----    解析音频文件头信息
        '''
    # print(func_des)

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--in_path', required=True, help='输入目录或文件')
    parser.add_argument('-o', '--out_path', help='输出目录或文件')
    parser.add_argument('-a', '--act_func', required=True, help="可执行操作")
    parser.add_argument('--in_ch', type=int, default=1, help="输入文件通道数，默认值：3")
    parser.add_argument('--in_rate', type=int, default=16000, help="输入文件采样率，默认值：16000")
    parser.add_argument('--in_width', type=int, default=2, help="输入文件采样宽度，默认值：2")
    parser.add_argument('--out_ch', type=int, default=3, help="输出文件通道数，默认值：3")
    parser.add_argument('--out_rate', type=int, default=16000, help="输出文件采样率，默认值：16000")
    parser.add_argument('--out_width', type=int, default=2, help="输出文件采样宽度，默认值：2")
    parser.add_argument('--rep_num', type=int, default=10, help="复制次数，默认值：10")
    parser.add_argument('--ext_ms', type=int, default=10, help="截取语音前段时长（秒），默认值：10000")
    parser.add_argument('--spd_val', type=float, default=1, help="倍速，默认值：1")
    parser.add_argument('--gain_db', type=float, default=0, help="放大dB，默认值：0")
    parser.add_argument('--mux_ch', type=str, default="0,1,2", help="通道提取，默认值：012")
    parser.add_argument('--mix_method', type=str, default="average", help="多通道混音，支持：average, sum, left, right, 默认值：average")
    parser.add_argument('--textgrid_file', type=str, help="TextGrid格式标注文件")
    parser.add_argument('--textgrid_start', type=str, default="00:00:00.000", help="TextGrid格式标注文件起始时间")
    parser.add_argument('--text_file', type=str, help="Text格式标注文件")
    parser.add_argument('--interv_s', type=str, default=60, help="切分语音时间间隔（秒），默认值：60")
    parser.add_argument('--silence_ms', type=str, help="插入静音时长(ms)，默认值：0")
    parser.add_argument('--start_time', type=str, default='00:00:00.000', help="起始时间 HH:MM:SS.mmm，默认值：00:00:00.000")
    parser.add_argument('--end_time', type=str, default=None, help="结束时间 HH:MM:SS.mmm，默认到文件末尾")

    args = parser.parse_args()

    in_path = args.in_path
    func = args.act_func
    out_path = args.out_path
    input_file_list = []
    
    if not out_path:
        if os.path.isdir(in_path):
            out_path = in_path.rstrip(os.sep) + '_out'
        elif os.path.isfile(in_path):
            out_path = os.path.dirname(in_path).rstrip(os.sep) + '_out'

    if not os.path.exists(out_path):
        os.mkdir(out_path)
    print('input  path:\t' + in_path)
    print('output path:\t' + out_path)
    
    # multi processing
    try:
        num_processes = multiprocessing.cpu_count()
        print("Number of available CPU cores: ", num_processes)
    except (NotImplementedError, OSError):
        num_processes = 4
        print("Warning: Unable to determine the number of CPUs, defaulting to 4 processes.")
    pool = multiprocessing.Pool(processes=num_processes) 

    # function
    if (func == 'help'):
        print(func_des)
    elif(func == 'list'):
        list_files(in_path)
    elif(func == 'pcm2wav'):
        pcm_convert_wav(in_path, out_path, args.in_ch, args.in_rate, args.in_width) 
    elif(func == 'wav2pcm'):
        wav_convert_pcm(in_path, out_path)     
    elif(func == 'wav2pcm2'):
        wav_convert_pcm2(in_path, out_path)    
    elif (func == 'oth2wav'):
        other_convert_wav(in_path, out_path, args.in_ch, args.in_rate, args.in_width) 
    elif (func == 'wav2wav44'):
        wav_convert_wav44(in_path, out_path)
    elif (func == 'wav2ogg'):
        wav_convert_ogg(in_path, out_path)
    elif(func == 'repeat'):
        wav_repeat(in_path, out_path, args.rep_num)
    elif(func == 'extract'):
        wav_extract(in_path, out_path, args.ext_ms)
    elif(func == 'speed'):
        wav_speed(in_path, out_path, args.spd_val)
    elif(func == 'gain'):
        wav_gain(in_path, out_path, args.gain_db)
    elif(func == 'mux'):
        wav_split_mux(in_path, out_path, args.mux_ch)
    elif(func == 'mix'):
        wav_mix_to_mono(in_path, out_path, args.mix_method)
    elif (func == 'resample'):
        wav_resample(in_path, out_path, args.out_rate, args.out_width)
    elif (func == 'mono'):
        wav_split_mono(in_path, out_path)
    elif (func == 'merge'):
        wav_merge_multi(in_path, out_path)
    elif (func == 'textgridcut'):
        wav_textgrid_cut(in_path, out_path, args.textgrid_file, args.textgrid_start)
    elif (func == 'videotextgridcut'):
        video_textgrid_cut(in_path, out_path, args.textgrid_file, args.textgrid_start)
    elif (func == 'videocut'):
        video_interval_cut(in_path, out_path, args.interv_s)
    elif (func == 'videotimecut'):
        video_time_cut(in_path, out_path, args.start_time, args.end_time)
    elif (func == 'intervcut'):
        wav_interval_cut(in_path, out_path, args.interv_s)
    elif (func == 'insertsil'):
        wav_insert_silence(in_path, out_path, args.silence_ms)   
    elif (func == 'cat'):
        wav_cat_silence(in_path, args.silence_ms)
    elif (func == 'duration'):
        compute_wav_duration(in_path, out_path)
    elif (func == 'profile'):
        profile_audio(in_path, out_path)
    else:
        print('not supported function')
        print(func_des)
        
    pool.close()
    pool.join()
    print('\r\nDone.')
    