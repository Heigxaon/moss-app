# main.py
import threading
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.settings import SettingsWithTabbedPanel
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.lang import Builder

from core import AIChat, config, save_config, load_config, messages

# 加载 kv 文件
Builder.load_file('moss.kv')

class MossScreen(Screen):
    chat_data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ai = None
        self.current_bubble = None  # 当前正在流式更新的气泡索引
        self.reasoning_text = ""

    def on_enter(self):
        # 恢复历史对话到界面
        self.chat_data.clear()
        for msg in messages[1:]:  # 跳过 system
            if msg['role'] == 'user':
                self.add_bubble(msg['content'], side='right')
            elif msg['role'] == 'assistant':
                self.add_bubble(msg['content'], side='left')
        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.1)

    def add_bubble(self, text, side='left'):
        """添加一条完整气泡"""
        self.chat_data.append({'side': side, 'text': text})
        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.1)

    def update_bubble(self, index, new_text):
        """更新已有气泡内容（用于流式）"""
        if 0 <= index < len(self.chat_data):
            self.chat_data[index]['text'] = new_text
            self.chat_data = self.chat_data  # 触发刷新
            Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.05)

    def scroll_to_bottom(self):
        scroll = self.ids.chat_scroll
        scroll.scroll_y = 0

    def send_message(self):
        text = self.ids.input_msg.text.strip()
        if not text:
            return
        self.ids.input_msg.text = ""
        self.add_bubble(text, side='right')

        # 停止之前的请求
        if self.ai:
            self.ai.stop()
        self.ai = AIChat(callback=self.on_chunk)
        self.ai.chat(text)

    @mainthread
    def on_chunk(self, chunk_type, content):
        if chunk_type == 'reasoning':
            # 可选：显示思考过程（灰色斜体）
            self.reasoning_text += content
            # 这里可以单独处理
        elif chunk_type == 'content':
            if self.reasoning_text:
                # 首次收到正文时，将思考内容作为单独气泡插入（可选）
                self.reasoning_text = ""
            # 检查是否需要新建气泡
            if self.current_bubble is None:
                self.add_bubble(content, side='left')
                self.current_bubble = len(self.chat_data) - 1
            else:
                # 追加到当前气泡
                bubble = self.chat_data[self.current_bubble]
                bubble['text'] += content
                self.update_bubble(self.current_bubble, bubble['text'])
        elif chunk_type == 'done':
            self.current_bubble = None
            # 显示余额（可选）
            balance = AIChat.get_balance()
            if balance is not None:
                self.add_bubble(f"[i]余额: {balance:.4f}[/i]", side='left')
        elif chunk_type == 'error':
            self.add_bubble(f"[color=ff0000]错误: {content}[/color]", side='left')
            self.current_bubble = None

class MossApp(App):
    use_kivy_settings = False

    def build(self):
        self.title = "MOSS AI"
        Window.bind(on_keyboard=self.on_key)
        return MossScreen()

    def on_key(self, window, key, *args):
        # 按返回键退出设置界面
        if key == 27:  # ESC / Back
            if self.root_window.children[0].__class__.__name__ == 'Settings':
                self.close_settings()
                return True
        return False

    def build_config(self, config):
        config.setdefaults('AI', {
            'model': 'deepseek-ai/DeepSeek-V3',
            'temperature': 1.0,
            'max_tokens': 2048,
            'max_memory': 5,
            'siliconflow_key': '',
            'deepseek_key': ''
        })

    def build_settings(self, settings):
        settings.add_json_panel('AI 设置', self.config, data='''
        [
            {"type": "title", "title": "模型配置"},
            {"type": "options", "title": "模型", "desc": "选择使用的模型", "section": "AI", "key": "model",
             "options": ["deepseek-ai/DeepSeek-V3", "deepseek-chat", "deepseek-reasoner", "Qwen/Qwen2.5-7B-Instruct"]},
            {"type": "numeric", "title": "Temperature", "desc": "创意温度 (0-2)", "section": "AI", "key": "temperature", "min": 0, "max": 2},
            {"type": "numeric", "title": "最大 Token", "section": "AI", "key": "max_tokens", "min": 1, "max": 8192},
            {"type": "numeric", "title": "记忆轮数", "section": "AI", "key": "max_memory", "min": 0, "max": 20},
            {"type": "string", "title": "SiliconFlow API Key", "section": "AI", "key": "siliconflow_key"},
            {"type": "string", "title": "DeepSeek API Key", "section": "AI", "key": "deepseek_key"}
        ]
        ''')

    def on_config_change(self, config, section, key, value):
        # 同步到 core.config
        if section == 'AI':
            if key == 'model':
                core_config['模型'] = value
            elif key == 'temperature':
                core_config['创意温度(temperature)'] = float(value)
            elif key == 'max_tokens':
                core_config['生成上限(max_tokens)'] = int(value)
            elif key == 'max_memory':
                core_config['最大记忆'] = int(value)
            elif key == 'siliconflow_key':
                core_config['SiliconFlow']['APIkey'] = value
            elif key == 'deepseek_key':
                core_config['DeepSeek']['APIkey'] = value
            save_config()

    def close_settings(self, *args):
        super().close_settings()
        # 刷新主界面模型显示
        screen = self.root
        if hasattr(screen, 'ids'):
            pass

if __name__ == '__main__':
    # 初始化 core.config 从文件加载
    from core import config as core_config
    MossApp().run()