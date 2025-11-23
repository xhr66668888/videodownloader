import yt_dlp
import os
import re
import glob
import time
from moviepy.editor import VideoFileClip, AudioFileClip


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '', name)


def is_direct_download_platform(url):
    return 'douyin.com' in url or 'tiktok.com' in url


# === 核心逻辑：尝试下载 ===
def try_download(url, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


# === 修改版：增加了返回值 (True成功 / False失败) ===
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

            # 验证文件是否真的存在
            if os.path.exists(output_file):
                print(f"✅ 完成: {output_file}")
                return True  # 成功
            else:
                print("❌ 下载看似完成但文件不存在")
                return False

        except Exception as e:
            print(f"❌ 抖音下载失败: {e}")
            return False  # 失败

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
            'format': 'bestvideo',
            'outtmpl': temp_v,
            'quiet': True, 'no_warnings': True
        }
        try_download(url, ydl_opts_video)

        # 下载音频
        ydl_opts_audio = {
            'format': 'bestaudio',
            'outtmpl': temp_a,
            'quiet': True, 'no_warnings': True
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
            return True  # 成功
        else:
            raise Exception("下载流不完整")

    except Exception as e:
        print(f"\n⚠️ 高清模式失败 ({e})，正在切换到兼容模式...")

    # === 方案 2: 保底模式 (直接下载 720p 单文件) ===
    print("🎥 尝试方案 2: 下载标准画质 (兼容性最好)...")
    try:
        output_fallback = f"{video_title}_720p.mp4"
        fallback_opts = {
            'format': 'best',
            'outtmpl': output_fallback,
            'ignoreerrors': True
        }
        try_download(url, fallback_opts)

        if os.path.exists(output_fallback):
            print(f"✅ 标准画质下载成功: {output_fallback}")
            return True  # 成功
        else:
            print("❌ 保底下载也失败了，文件未生成")
            return False

    except Exception as e:
        print(f"❌ 所有方案都失败了: {e}")
        return False  # 失败


# === 主程序逻辑 ===
if __name__ == "__main__":
    input_file = "links.txt"
    failed_log = "failed_log.txt"

    print("=== 批量视频下载器 ===")

    # 1. 检查 links.txt 是否存在
    if not os.path.exists(input_file):
        with open(input_file, "w", encoding="utf-8") as f:
            f.write("")  # 创建空文件
        print(f"⚠️ 未找到 {input_file}，已为你自动创建。")
        print(f"请将视频链接粘贴到 {input_file} 中，一行一个，然后重新运行程序。")
        exit()

    # 2. 读取链接
    with open(input_file, "r", encoding="utf-8") as f:
        # 读取非空行，并去除首尾空格
        urls = [line.strip() for line in f if line.strip()]

    total_count = len(urls)
    print(f"📂 从 {input_file} 读取到 {total_count} 个链接。")

    if total_count == 0:
        print("文件是空的，请先添加链接。")
        exit()

    failed_urls = []

    # 3. 开始循环下载
    for index, url in enumerate(urls):
        print(f"\n{'=' * 40}")
        print(f"处理进度: [{index + 1}/{total_count}]")
        print(f"{'=' * 40}")

        success = download_video(url)

        if not success:
            print(f"❌ 记录为失败: {url}")
            failed_urls.append(url)

        # 稍微暂停1秒，防止请求太快被封IP
        time.sleep(1)

    # 4. 输出失败报告
    print(f"\n\n{'=' * 40}")
    print("🎉 全部任务结束！")
    print(f"✅ 成功: {total_count - len(failed_urls)}")
    print(f"❌ 失败: {len(failed_urls)}")

    if failed_urls:
        with open(failed_log, "w", encoding="utf-8") as f:
            for u in failed_urls:
                f.write(u + "\n")
        print(f"⚠️ 失败的链接已保存到: {failed_log}")
        print("你可以检查该文件，稍后再次尝试下载。")
    else:
        print("💯 完美！没有失败的链接。")
