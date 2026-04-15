# core.py
import json
import threading
import requests
import time
from collections import defaultdict

# ---------- 配置管理 ----------
CONFIG_FILE = "moss_config.json"
DEFAULT_CONFIG = {
    "虚拟名": "User",
    "模型": "deepseek-ai/DeepSeek-V3",
    "角色": "",
    "系统提示词": "",
    "风格": "",
    "最大记忆": 5,
    "生成上限(max_tokens)": None,
    "创意温度(temperature)": 1.0,
    "核心词集(top_p)": 1.0,
    "候选项数(top_k)": None,
    "重复惩罚(frequency_penalty)": None,
    "推理模式(enable_thinking)": False,
    "思考预算(thinking_budget)": None,
    "停止词集(stop)": [],
    "SiliconFlow": {"APIkey": ""},
    "DeepSeek": {"APIkey": ""},
    "对话": [{"role": "system", "content": ""}]
}

config = {}
messages = []

def load_config():
    global config, messages
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = DEFAULT_CONFIG.copy()
    messages = config.get("对话", [{"role": "system", "content": ""}])
    # 确保系统提示词存在
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": ""})

def save_config():
    config["对话"] = messages
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

load_config()

# ---------- AI 聊天核心（流式回调） ----------
class AIChat:
    def __init__(self, callback=None):
        """
        callback: 函数，接收 (chunk_type, content) 
                  chunk_type: 'reasoning' 或 'content' 或 'done'
        """
        self.callback = callback
        self.stop_flag = False

    def stop(self):
        self.stop_flag = True

    def chat(self, prompt):
        """在后台线程中运行"""
        threading.Thread(target=self._run, args=(prompt,), daemon=True).start()

    def _run(self, prompt):
        model = config["模型"]
        max_mem = config["最大记忆"]
        max_tokens = config["生成上限(max_tokens)"]
        temperature = config["创意温度(temperature)"]
        top_p = config["核心词集(top_p)"]
        top_k = config["候选项数(top_k)"]
        frequency_penalty = config["重复惩罚(frequency_penalty)"]
        enable_thinking = config["推理模式(enable_thinking)"]
        thinking_budget = config["思考预算(thinking_budget)"]
        stop = config["停止词集(stop)"]

        if model in ['deepseek-chat', 'deepseek-reasoner']:
            base_url = "https://api.deepseek.com"
            site = "DeepSeek"
        else:
            base_url = "https://api.siliconflow.cn/v1"
            site = "SiliconFlow"

        url = f"{base_url}/chat/completions"
        api_key = config[site].get("APIkey", "")
        headers = {"Authorization": f"Bearer {api_key}"}

        global messages
        messages.append({"role": "user", "content": prompt})

        data = {
            "messages": messages,
            "model": model,
            "stream": True,
        }
        if max_tokens: data["max_tokens"] = max_tokens
        if temperature is not None: data["temperature"] = temperature
        if top_p is not None: data["top_p"] = top_p
        if frequency_penalty is not None: data["frequency_penalty"] = frequency_penalty
        if stop: data["stop"] = stop
        if enable_thinking:
            if site == "SiliconFlow":
                data["enable_thinking"] = enable_thinking
            else:
                data["thinking"] = {"type": "enabled"}
        if site == "SiliconFlow":
            if top_k: data["top_k"] = top_k
            if thinking_budget: data["thinking_budget"] = thinking_budget

        try:
            response = requests.post(url, headers=headers, json=data, stream=True, timeout=60)
            if response.status_code != 200:
                if self.callback:
                    self.callback('error', f"HTTP {response.status_code}: {response.text}")
                return

            full_content = ""
            for chunk in response.iter_lines():
                if self.stop_flag:
                    break
                if chunk:
                    chunk_str = chunk.decode('utf-8').replace('data: ', '')
                    if chunk_str == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(chunk_str)
                        delta = chunk_data['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        reasoning = delta.get('reasoning_content', '')
                        if reasoning and self.callback:
                            self.callback('reasoning', reasoning)
                        if content and self.callback:
                            self.callback('content', content)
                            full_content += content
                    except:
                        continue

            # 保存助手回复
            messages.append({"role": "assistant", "content": full_content})
            if len(messages) > max_mem * 2 + 1:
                messages[:] = [messages[0]] + messages[-max_mem*2:]
            save_config()

            if self.callback:
                self.callback('done', full_content)

        except Exception as e:
            if self.callback:
                self.callback('error', str(e))

    @staticmethod
    def get_balance():
        model = config["模型"]
        site = "DeepSeek" if model in ['deepseek-chat', 'deepseek-reasoner'] else "SiliconFlow"
        base_url = "https://api.deepseek.com" if site == "DeepSeek" else "https://api.siliconflow.cn/v1"
        url = f"{base_url}/user/balance" if site == "DeepSeek" else f"{base_url}/user/info"
        headers = {"Authorization": f"Bearer {config[site].get('APIkey', '')}"}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if site == "DeepSeek":
                return float(resp.json()["balance_infos"][0]["total_balance"])
            else:
                return float(resp.json()["data"]["balance"])
        except:
            return None