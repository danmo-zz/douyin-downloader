#!/usr/bin/env python3
"""
抖音无水印下载器 - Android App GUI 版本
功能：输入抖音分享链接，下载无水印视频
"""

import os
import re
import requests
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

# 请求头，模拟移动端访问
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/121.0.2277.107 Version/17.0 Mobile/15E148 Safari/604.1'
}


class DouyinDownloader(BoxLayout):
    def __init__(self, **kwargs):
        super(DouyinDownloader, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [20, 20, 20, 20]
        self.spacing = 15

        # 标题
        title = Label(
            text='抖音无水印下载器',
            font_size='24sp',
            size_hint=(1, 0.1),
            color=get_color_from_hex('#2196F3')
        )
        self.add_widget(title)

        # 输入框提示
        input_label = Label(
            text='粘贴抖音分享链接:',
            font_size='16sp',
            size_hint=(1, 0.05),
            halign='left',
            color=get_color_from_hex('#333333')
        )
        input_label.text_size = self.width, None
        self.add_widget(input_label)

        # 输入框
        self.link_input = TextInput(
            hint_text='https://v.douyin.com/...',
            size_hint=(1, 0.1),
            font_size='14sp'
        )
        self.add_widget(self.link_input)

        # 下载按钮
        self.download_btn = Button(
            text='开始下载',
            size_hint=(1, 0.1),
            background_color=get_color_from_hex('#2196F3'),
            font_size='18sp'
        )
        self.download_btn.bind(on_press=self.start_download)
        self.add_widget(self.download_btn)

        # 日志提示
        log_label = Label(
            text='日志输出:',
            font_size='16sp',
            size_hint=(1, 0.05),
            halign='left',
            color=get_color_from_hex('#333333')
        )
        log_label.text_size = self.width, None
        self.add_widget(log_label)

        # 日志输出区域
        self.log_scroll = ScrollView(size_hint=(1, 0.55))
        self.log_text = TextInput(
            text='准备就绪，请输入抖音分享链接...\n',
            readonly=True,
            size_hint=(1, None),
            height=400,
            font_size='12sp',
            background_color=get_color_from_hex('#f5f5f5')
        )
        self.log_scroll.add_widget(self.log_text)
        self.add_widget(self.log_scroll)

    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.text += f'[{timestamp}] {message}\n'

    def parse_share_url(self, share_text):
        """从分享文本中提取视频信息"""
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', share_text)
        if not urls:
            raise ValueError("未找到有效的分享链接")

        share_url = urls[0]
        share_response = requests.get(share_url, headers=HEADERS)
        video_id = share_response.url.split("?")[0].strip("/").split("/")[-1]
        share_url = f'https://www.iesdouyin.com/share/video/{video_id}'

        response = requests.get(share_url, headers=HEADERS)
        response.raise_for_status()

        pattern = re.compile(
            pattern=r"window\._ROUTER_DATA\s*=\s*(.*?)</script>",
            flags=re.DOTALL,
        )
        find_res = pattern.search(response.text)

        if not find_res or not find_res.group(1):
            raise ValueError("解析视频信息失败")

        import json
        json_data = json.loads(find_res.group(1).strip())
        VIDEO_ID_PAGE_KEY = "video_(id)/page"
        NOTE_ID_PAGE_KEY = "note_(id)/page"

        if VIDEO_ID_PAGE_KEY in json_data["loaderData"]:
            original_video_info = json_data["loaderData"][VIDEO_ID_PAGE_KEY]["videoInfoRes"]
        elif NOTE_ID_PAGE_KEY in json_data["loaderData"]:
            original_video_info = json_data["loaderData"][NOTE_ID_PAGE_KEY]["videoInfoRes"]
        else:
            raise Exception("无法解析视频信息")

        data = original_video_info["item_list"][0]
        video_url = data["video"]["play_addr"]["url_list"][0].replace("playwm", "play")
        desc = data.get("desc", "").strip() or f"douyin_{video_id}"
        desc = re.sub(r'[\\/:*?"<>|]', '_', desc)

        return {
            "url": video_url,
            "title": desc,
            "video_id": video_id
        }

    def download_video(self, video_info, output_dir='/sdcard/Download'):
        """下载视频到本地"""
        import os
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"douyin_{video_info['video_id']}.mp4"
        filepath = output_path / filename

        self.log(f"正在下载: {video_info['title']}")
        response = requests.get(video_info['url'], headers=HEADERS, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

        self.log(f"下载完成: {filepath}")
        return str(filepath)

    def start_download(self, instance):
        """开始下载按钮点击事件"""
        link_text = self.link_input.text.strip()
        if not link_text:
            self.log("错误: 请输入分享链接")
            return

        try:
            self.download_btn.disabled = True
            self.download_btn.text = "下载中..."

            self.log(f"正在解析链接: {link_text[:50]}...")
            video_info = self.parse_share_url(link_text)
            self.log(f"视频标题: {video_info['title']}")

            output_path = self.download_video(video_info)

            self.log(f"✅ 成功保存到: {output_path}")
            self.log("可以在系统下载文件夹中找到视频\n")

            self.download_btn.disabled = False
            self.download_btn.text = "开始下载"

        except Exception as e:
            self.log(f"❌ 错误: {str(e)}")
            self.download_btn.disabled = False
            self.download_btn.text = "开始下载"


class DouyinDownloaderApp(App):
    def build(self):
        self.title = '抖音无水印下载器'
        return DouyinDownloader()

    def get_application_config(self):
        return super().get_application_config()


if __name__ == '__main__':
    DouyinDownloaderApp().run()
