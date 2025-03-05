import os
import time
import requests
import json
from dotenv import load_dotenv
from dataclasses import dataclass
import backoff
from src.utils.logging_config import setup_logger, SUCCESS_ICON, ERROR_ICON, WAIT_ICON

# 设置日志记录
logger = setup_logger('api_calls')


@dataclass
class ChatMessage:
    content: str


@dataclass
class ChatChoice:
    message: ChatMessage


@dataclass
class ChatCompletion:
    choices: list[ChatChoice]


# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')

# 加载环境变量
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    logger.info(f"{SUCCESS_ICON} 已加载环境变量: {env_path}")
else:
    logger.warning(f"{ERROR_ICON} 未找到环境变量文件: {env_path}")

# 验证环境变量
api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")
base_url = os.getenv("GEMINI_BASE_URL")

if not api_key:
    logger.error(f"{ERROR_ICON} 未找到 GEMINI_API_KEY 环境变量")
    raise ValueError("GEMINI_API_KEY not found in environment variables")
if not model:
    model = "gemini-1.5-flash"
    logger.info(f"{WAIT_ICON} 使用默认模型: {model}")


@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=5,
    max_time=300,
    giveup=lambda e: "AFC is enabled" not in str(e)
)
def generate_content_with_retry(model, contents, config=None):
    """带重试机制的内容生成函数"""
    try:
            logger.info(f"{WAIT_ICON} Calling XiaoAI API...")
            logger.debug(f"Request content: {contents}")

            data = {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个顶尖的股票分析师"  # 系统消息
                    },
                    {
                        "role": "user",
                        "content": contents  # 用户消息
                    }
                ],
                "stream": False,  # 是否流式返回
                "model": model,  # 模型名称
                "temperature":  0.5,  # 温度参数
                "presence_penalty": 0,  # 存在惩罚
                "frequency_penalty":0,  # 频率惩罚
                "top_p":1  # Top-p 采样
            }
            headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            }

            response = requests.post(base_url, headers=headers, json=data)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)


            try:
                logger.info(f"{SUCCESS_ICON} API call successful")
                logger.debug(f"Response: {response.text[:500]}...")
                return response
            except json.JSONDecodeError:
                logger.error(f"{ERROR_ICON} 无法解析 JSON 响应: {response.text}")
                raise

    except requests.exceptions.RequestException as e:
        logger.error(f"{ERROR_ICON} API request failed: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"{ERROR_ICON} Invalid JSON response: {e}")
        raise
    except Exception as e:
        logger.error(f"{ERROR_ICON} An unexpected error occurred: {e}")
        raise



def get_chat_completion(messages, model=None, max_retries=2, initial_retry_delay=1):
    """Gets chat completion results, including retry logic."""
    try:
        if model is None:
            model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        logger.info(f"{WAIT_ICON} 使用模型: {model}")
        logger.debug(f"消息内容: {messages}")

        for attempt in range(max_retries):
            try:
                # 转换消息格式
                prompt = ""
                system_instruction = None

                for message in messages:
                    role = message["role"]
                    content = message["content"]
                    if role == "system":
                        system_instruction = content
                    elif role == "user":
                        prompt += f"User: {content}\n"
                    elif role == "assistant":
                        prompt += f"Assistant: {content}\n"

                # 准备配置
                config = {}
                if system_instruction:
                    config['system_instruction'] = system_instruction

                # 调用 API
                response = generate_content_with_retry(
                    model=model,
                    contents=prompt.strip(),
                    config=config
                )

                if response is None:
                    logger.warning(
                        f"{ERROR_ICON} 尝试 {attempt + 1}/{max_retries}: API 返回空值")
                    if attempt < max_retries - 1:
                        retry_delay = initial_retry_delay * (2 ** attempt)
                        logger.info(f"{WAIT_ICON} 等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    return None

                # 转换响应格式
                chat_message = ChatMessage(content=response.text)
                chat_choice = ChatChoice(message=chat_message)
                completion = ChatCompletion(choices=[chat_choice])

                logger.debug(f"API 原始响应: {response.text}")
                logger.info(f"{SUCCESS_ICON} 成功获取响应")
                return completion.choices[0].message.content

            except Exception as e:
                logger.error(
                    f"{ERROR_ICON} 尝试 {attempt + 1}/{max_retries} 失败: {str(e)}")
                if attempt < max_retries - 1:
                    retry_delay = initial_retry_delay * (2 ** attempt)
                    logger.info(f"{WAIT_ICON} 等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"{ERROR_ICON} 最终错误: {str(e)}")
                    return None

    except Exception as e:
        logger.error(f"{ERROR_ICON} get_chat_completion 发生错误: {str(e)}")
        return None
