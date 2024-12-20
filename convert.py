import requests
import discord
from discord.ext import commands
from pydub import AudioSegment
from faster_whisper import WhisperModel
import pandas as pd
from io import BytesIO
import subprocess
import os
import csv
import time
import shutil

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


# 初始化bot
intents = discord.Intents.default()                      # 啟用預設權限
intents.message_content = True                           # 讓bot可以讀訊息
bot = commands.Bot(command_prefix='[', intents=intents)  # 設置命令前綴

# 確認是否會遇到下載警告
def get_confirm_token(response:requests.Response): 
    # 從 Google Drive 回應有下載警告中提取確認 token          
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value

    return None

# 下載檔案
def save_response_content(response:requests.Response, destination):
    CHUNK_SIZE = 32768      # 區塊大小(單位為bytes)

    # 此處將大檔案分割成一堆小區塊進行下載
    with open(destination, "wb") as f:    
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)

# 利用爬蟲從 Google Drive 下載檔案
def download_file_from_google_drive(file_id, destination):
    session = requests.Session()
    URL = "https://docs.google.com/uc?export=download&confirm=1"      # Google drive 要求下載的連結

    response = session.get(URL, params={"id": file_id}, stream=True)  # 獲取回應
    token = get_confirm_token(response)                               # 檢查是否產生下載警告

    # 當跑出下載警告時傳入確認下載的token
    if token:
        params = {"id": file_id, "confirm": token}
        response = session.get(URL, params=params, stream=True)

    save_response_content(response, destination)  # 將回應內容(檔案)下載至電腦

# youtube影片網址下載為mp3
def download_audio_from_youtube(video_url):
    try:
        output_file_yt = "yt.mp3"

        # -x是只提取音訊，忽略影片部分 check=True表示如果yt-dlp命令失敗則會引發錯誤
        # 會將 YouTube 影片中的音訊提取並轉換為 MP3 格式 並儲存在指定的檔案名稱中     
        subprocess.run(['yt-dlp', '-x', '--audio-format', 'mp3', video_url, '-o', output_file_yt], check=True) 
        print(f"音訊檔案已下載為 {output_file_yt}")
        return output_file_yt
    
    except Exception as e:
        print(f"下載音訊檔案時發生錯誤: {e}")
        return None
    
# 將音訊連結（YouTube 或 Google Drive）轉換為 WAV 格式
def convert_audio_to_wav(audio_url):
    try:
        downloaded_file_yt = None          # 初始化 YouTube 下載的文件變數
        output_file = 'output/output.wav'  # 設定轉換後的音訊檔案儲存路徑

        # 如果是 YouTube 連結就下載音訊
        if "youtube.com" in audio_url or "youtu.be" in audio_url:
            downloaded_file_yt = download_audio_from_youtube(audio_url)

            # 如果下載成功就載入音訊
            if downloaded_file_yt:
                # 使用 pydub 將音訊轉換為 WAV 格式
                audio = AudioSegment.from_file(downloaded_file_yt)  # 讀取下載的音訊文件
                audio.export(output_file, format = "wav")           # 將音訊導出為 WAV 格式
                print(f"音訊成功轉換並儲存為 {output_file}")
        
        # 如果不是 YouTube 連結 就假設是 Google Drive 連結
        else:
            file_id = audio_url.split('/')[-2]      # 從 URL 中提取 Google Drive 文件的 ID
            session = requests.Session()
            URL = "https://docs.google.com/uc?export=download&confirm=1" #Google drive 要求下載的連結
            
            # 發送請求以獲取音訊文件
            r = session.get(URL, params={"id": file_id}, stream=True)
            token = get_confirm_token(r)   # 獲得 token

            if token:
                # 如果 token 存在 更新請求參數以包括確認 token
                params = {"id": file_id, "confirm": token}
                r = session.get(URL, params=params, stream=True)

            # 使用 save_response_content 函式將下載的音訊內容儲存為 WAV 格式
            save_response_content(r, output_file)
            print(f"音訊成功轉換並儲存為 {output_file}")

        # 清理下載的音訊檔案
        if downloaded_file_yt and os.path.exists(downloaded_file_yt):
            os.remove(downloaded_file_yt)

        return output_file  

    except Exception as e:
        print(f"轉檔時發生錯誤:{e}")
        return None

def transcribe(audio, lang, mod):
    if not os.path.exists(audio):
        raise Exception(f"音訊檔案 {audio} 不存在或無法讀取")
    print(f"轉錄中...({audio})") 
    model = WhisperModel(mod)
    segments, info = model.transcribe(audio, language=lang, vad_filter=False, vad_parameters=dict(min_silence_duration_ms=100))  
    # 假設 info 是個物件，語言應該可以透過 .language 來獲取
    language = info.language
    
    print("轉錄語言:", language)
    segments = list(segments) # 將 segments 轉換為列表
    return language, segments


def formattedtime(seconds):
    #從檔案開始將每個間隔所表示時間寫成字串
    final_time = time.strftime("%H:%M:%S", time.gmtime(float(seconds))) 
    return f"{final_time},{seconds.split('.')[1]}"

def writetocsv(segments, output_csv_path):
    cols = ["start", "end", "text"]
    data = []
    for segment in segments:
        start = formattedtime(format(segment.start, ".3f"))
        end = formattedtime(format(segment.end, ".3f"))
        data.append([start, end, segment.text])

    df = pd.DataFrame(data, columns=cols)
    df.to_csv(output_csv_path, index=False, encoding='utf-8')
    return df  # 返回 DataFrame 而不是檔案路徑

def generatesrt(csv_file):
    rows = []
    count = 0
    try:
        with open(csv_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                count += 1
                txt = f"{count}\n{row['start']} --> {row['end']}\n{row['text'].strip()}\n\n"
                rows.append(txt)
    except Exception as e:
        print(f"SRT 檔案生成失敗: {e}")
    return rows
class Convert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description='將網址音訊轉換為文字稿')         # 定義一個 Discord 的斜線指令
    @discord.option('url', str, description='你想轉換成文字稿的網址')    # 增加一個參數 url 用於接受使用者輸入的音訊連結
    # 增加一個可選參數 language，用於指定語言（例如 "en"、"zh" 等）  
    @discord.option('language', str, description='你想轉換成的語言（請用小寫英文字母）', required=False, default=None) 
    # 增加一個可選參數 model 用於指定語音轉文字模型的大小 並限制選項範圍為 ['tiny', 'base', 'medium', 'large']  
    @discord.option('model', str, description='你想使用的轉錄模型', required=False, default='base', choices=['tiny', 'base', 'medium', 'large'])
    # 定義異步函式 接收三個參數：url（音訊連結）、language（語言）、model（模型）。 
    async def convert_to_txt(self, ctx: discord.ApplicationContext, url: str, language: str = None, model: str = 'model'):
            print("正在執行...")  
            await ctx.defer()  # 延長回應時間限制
            await ctx.followup.send("等億下會怎樣...")

            output_file = convert_audio_to_wav(url) 

            if output_file:
                try:
                    # 使用 faster-whisper 進行轉錄
                    lang, segments = transcribe(output_file, language, model)

                    # 寫入文字稿
                    with open('output.txt', 'w', encoding='utf8') as outputFile:
                        for segment in segments:
                            outputFile.write(segment.text + '\n')

                    await ctx.followup.send(content="以下為轉換的文字稿:", file=discord.File('output.txt'))
                    print("成功轉換成文字稿")

                    # 清理檔案
                    os.remove('output.txt')
                    os.remove(output_file)

                except Exception as e:
                    print(f"產生文字稿時發生錯誤: {e}")
                    await ctx.followup.send(f"產生文字稿時發生錯誤: {e}")
            else:
                await ctx.followup.send("轉檔失敗，請檢查輸入的連結")
                    
    @discord.slash_command(description='將網址音訊轉為Wav檔')         # 定義一個 Discord 的斜線指令
    @discord.option('url', str, description='你想轉換成Wav檔的網址')  # 增加一個參數 url 用於接受使用者輸入的音訊連結
    async def convert_to_wav(self, ctx: discord.ApplicationContext, url: str):
        print("正在執行...")  
        await ctx.send("等億下會怎樣...")

        output_file = convert_audio_to_wav(url)
        
        file_size = os.path.getsize(output_file)                # 偵測檔案大小
        file_size_MB = round(file_size / (1024 * 1024), 1)      # 轉為MB

        try:
            if output_file:

                await ctx.send(file=discord.File(output_file))
                await ctx.send("好了啦")
                print("完成執行")

                os.remove(output_file)  # 轉檔後刪除 WAV 檔案  
            else:
                await ctx.send("轉檔失敗 請檢查輸入的連結")
                
        except Exception as e:
            await ctx.send("檔案太大 目前太窮沒辦法升級discord 所以沒辦法回傳")
            await ctx.send(f"此檔案大小為{file_size_MB}MB 根據測試應該小於25MB才能回傳")
            print(f"此檔案大小為{file_size_MB}MB")
            print(f"發生錯誤:{e}")

            os.remove(output_file)  # 轉檔後刪除 WAV 檔案

    @discord.slash_command(description='將網址音訊轉換為srt檔')
    @discord.option('url', str, description='你想轉換成srt檔的網址')
    @discord.option('language', str, description='你想轉換成的語言（請用小寫英文字母）', required=False, default=None)
    @discord.option('model', str, description='你想使用的轉錄模型', required=False, default='base', choices=['tiny', 'base', 'medium', 'large'])
    async def convert_to_srt(self, ctx: discord.ApplicationContext, url, language, model):
        print("正在執行...")
        if not os.path.exists("output"):
            os.makedirs("output")  
        await ctx.defer()  # 延長回應時間限制
        await ctx.followup.send("等億下會怎樣...")

        output_file = convert_audio_to_wav(url) 

        if output_file:
            try:
                # 使用 faster-whisper 進行轉錄
                lang, segments = transcribe(output_file, language, model)
                
                # 寫入csv文字稿
                output_csv_path = os.path.join("output", "output.csv")
                writetocsv(segments, output_csv_path)

                # 產生SRT檔
                srt_data = generatesrt(output_csv_path)
                output_srt_path = os.path.join("output", "output.srt")
                with open(output_srt_path, "w") as srt_file:
                    for row in srt_data:
                        srt_file.write(row)

                await ctx.followup.send(content=f"這是您的 srt 檔案的語言 {lang}!", file=discord.File(output_srt_path))
                print("成功轉換成srt檔")

                # 清理檔案
                if os.path.exists(output_srt_path):
                    os.remove(output_srt_path)
                if os.path.exists(output_csv_path):
                    os.remove(output_csv_path)
                if os.path.exists(output_file):
                    os.remove(output_file)

            except Exception as e:
                print(f"產生文字稿時發生錯誤: {e}")
                await ctx.followup.send(f"產生文字稿時發生錯誤: {e}")
        else:
            await ctx.followup.send("轉檔失敗，請檢查輸入的連結")

def setup(bot):
    bot.add_cog(Convert(bot))