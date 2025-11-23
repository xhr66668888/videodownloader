import yt_dlp
import os
import re
import glob
from moviepy.editor import VideoFileClip, AudioFileClip


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '', name)


def is_direct_download_platform(url):
    return 'douyin.com' in url or 'tiktok.com' in url


# === 核心逻辑：尝试下载 ===
def try_download(url, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_video(url):
    print(f"\n🚀 正在分析链接: {url}")

    video_title = "video_download"

    # 1. 获取标题
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'ignoreerrors': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                video_title = sanitize_filename(info.get('title', 'video'))
                print(f"📄 标题: {video_title}")
    except:
        print("⚠️ 标题获取失败，使用默认名")

    # --- 分支 A: 抖音/TikTok (直接下载) ---
    if is_direct_download_platform(url):
        output_file = f"{video_title}.mp4"
        print("💡 识别为抖音，直接下载...")
        try:
            try_download(url, {'format': 'best', 'outtmpl': output_file, 'ignoreerrors': True})
            print(f"✅ 完成: {output_file}")
        except Exception as e:
            print(f"❌ 抖音下载失败: {e}")
        return

    # --- 分支 B: B站/YouTube (尝试高清 -> 失败转标清) ---
    print("💡 识别为 YouTube/B站，启动智能下载模式...")

    output_file = f"{video_title}.webm"
    temp_v = "temp_video_raw"
    temp_a = "temp_audio_raw"

    # 清理旧文件
    for f in glob.glob(f"{temp_v}*") + glob.glob(f"{temp_a}*"):
        try:
            os.remove(f)
        except:
            pass

    # === 方案 1: 尝试下载高清 (音画分离) ===
    print("\n🎥 尝试方案 1: 下载最高画质 (WebM)...")
    try:
        # 下载画面
        ydl_opts_video = {
            'format': 'bestvideo',  # 只要最好的视频，不限格式
            'outtmpl': temp_v,
            'quiet': True,
            'no_warnings': True
        }
        try_download(url, ydl_opts_video)

        # 下载音频
        ydl_opts_audio = {
            'format': 'bestaudio',
            'outtmpl': temp_a,
            'quiet': True,
            'no_warnings': True
        }
        try_download(url, ydl_opts_audio)

        # 检查是否下载成功
        found_v = glob.glob(f"{temp_v}*")
        found_a = glob.glob(f"{temp_a}*")

        if found_v and found_a:
            print("🧩 正在合并音视频...")
            vc = VideoFileClip(found_v[0])
            ac = AudioFileClip(found_a[0])
            final = vc.set_audio(ac)
            final.write_videofile(output_file, codec='libvpx', audio_codec='libvorbis', verbose=False, logger=None)
            vc.close()
            ac.close()
            os.remove(found_v[0])
            os.remove(found_a[0])
            print(f"✅ 高清下载成功: {output_file}")
            return  # 成功就结束
        else:
            raise Exception("下载流不完整")

    except Exception as e:
        print(f"\n⚠️ 高清模式失败 ({e})，正在切换到兼容模式...")

    # === 方案 2: 保底模式 (直接下载 720p 单文件) ===
    # 如果上面失败了，会执行这里。不需要合并，通常不会报错。
    print("🎥 尝试方案 2: 下载标准画质 (兼容性最好)...")
    try:
        output_fallback = f"{video_title}_720p.mp4"
        fallback_opts = {
            'format': 'best',  # 只要这一行，别的都不要
            'outtmpl': output_fallback,
            'ignoreerrors': True
        }
        try_download(url, fallback_opts)
        print(f"✅ 标准画质下载成功: {output_fallback}")
    except Exception as e:
        print(f"❌ 所有方案都失败了: {e}")


if __name__ == "__main__":
    print("=== 智能下载器 (含自动保底机制) ===")
    while True:
        u = input("\n请输入链接 (q退出): ").strip()
        if u == 'q': break
        if u: download_video(u)