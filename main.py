import asyncio
import random

from mistletoe.latex_token import Math
from slack_sdk.models.messages.message import message

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core import AstrBotConfig
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent


@register("astrbot_plugin_dont_poke_my_master", "Xc_Star", "当主人被戳一戳，或者自己被戳一戳触发回复", "1.0.0")
class DontPokeMyMaster(Star):
    def __init__(self, context: Context, config: AstrBotConfig):

        # 获取配置文件
        # 对自己的称呼
        self.name = config.get("name")
        # 主人列表
        self.master_list = config.get("master_list")
        # 戳主人触发概率
        self.trigger_probability = config.get("trigger_probability")
        # 戳主人模板列表
        self.message_template = config.get("message_template")
        # 被戳回复概率
        self.re_poke_probability = config.get("re_poke_probability")
        # 被戳回复模板列表
        self.re_poke_template = config.get("re_poke_template")

        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def dont_poke_my_master(self, event: AstrMessageEvent):
        """监听并响应戳一戳事件"""
        # 仅处理aiocqhttp平台的事件
        if event.get_platform_name() != "aiocqhttp":
            return

        raw_message = getattr(event.message_obj, "raw_message", None)

        # 检查是否为戳一戳事件
        if not raw_message or raw_message.get('post_type') != 'notice' or raw_message.get('notice_type') != 'notify' or raw_message.get('sub_type') != 'poke':
            return

        # 获取事件相关信息
        bot_id = raw_message.get('self_id')
        sender_id = raw_message.get('user_id')
        target_id = raw_message.get('target_id')
        group_id = raw_message.get('group_id')

        # 防止自戳导致死循环
        if sender_id == bot_id:
            return

        # 如果被戳对象是机器人
        if target_id == bot_id:
            message = await self.dont_poke_me()
            if message:
                yield event.plain_result(message)
                await self.do_poke_back(event, sender_id, group_id, 1)
            return

        # 如果被戳对象是主人
        if str(target_id) in self.master_list:
            # 概率回复
            if float(self.trigger_probability) <= random.random():
                return

            # 获取一个随机模板
            template: str = random.choice(self.message_template)

            # 分割模板
            message_list = template.split("|")

            # 发生模板消息
            for message in message_list:
                yield event.plain_result(message)
                await self.do_poke_back(event, sender_id, group_id, 3)

    async def dont_poke_me(self):
        # 概率回复
        if float(self.re_poke_probability) <= random.random():
            return None
        # 随机回复
        message = random.choice(self.re_poke_template)
        # 替换名字
        return message.format(name=self.name)

    async def do_poke_back(self, event: AiocqhttpMessageEvent, user_id: int, group_id: int, times: int):
        """执行反戳操作"""
        client = event.bot
        payloads = {"user_id": user_id}
        if group_id:
            payloads["group_id"] = group_id

        try:
            await client.api.call_action('send_poke', **payloads)
            await asyncio.sleep(times)
        except Exception as e:
            logger.error(f"反戳失败: {e}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
