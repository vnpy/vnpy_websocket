import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Optional
import asyncio
import threading

import aiohttp

from vnpy.trader.utility import get_file_logger


class WebsocketClient:
    """
    Websocket API

    After creating the client object, use start() to run worker and ping threads.
    The worker thread connects websocket automatically.

    Use stop to stop threads and disconnect websocket before destroying the client
    object (especially when exiting the programme).

    Default serialization format is json.

    Callbacks to overrides:
    * unpack_data
    * on_connected
    * on_disconnected
    * on_packet
    * on_error

    After start() is called, the ping thread will ping server every 60 seconds.

    If you want to send anything other than JSON, override send_packet.
    """

    def __init__(self):
        """Constructor"""
        self.host = None

        self._ws = None

        self.session: aiohttp.ClientSession = aiohttp.ClientSession()
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.thread: threading.Thread = None

        self.proxy_host = None
        self.proxy_port = None
        self.ping_interval = 60  # seconds
        self.header = {}

        self.logger: Optional[logging.Logger] = None

        # For debugging
        self._last_sent_text = None
        self._last_received_text = None

    def init(
        self,
        host: str,
        proxy_host: str = "",
        proxy_port: int = 0,
        ping_interval: int = 60,
        header: dict = None,
        log_path: Optional[str] = None,
    ):
        """
        初始化客户端
        """
        self.host = host
        self.ping_interval = ping_interval  # seconds
        if log_path is not None:
            self.logger = get_file_logger(log_path)
            self.logger.setLevel(logging.DEBUG)

        if header:
            self.header = header

        if proxy_host and proxy_port:
            self.proxy = f"http://{proxy_host}:{proxy_port}"

    def start(self):
        """
        启动客户端

        连接成功后会自动调用on_connected回调函数，

        请等待on_connected被调用后，再发送数据包。
        """
        # 如果目前没有任何事件循环在运行，则启动后台线程
        if not self.loop.is_running():
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
        # 否则直接在事件循环中加入新的任务
        else:
            asyncio.run_coroutine_threadsafe(self._run(), self.loop)

    def stop(self):
        """
        停止客户端。
        """
        if self._ws:
            coro = self._ws.close()
            asyncio.run_coroutine_threadsafe(coro, self.loop)

        if self.loop.is_running():
            self.loop.stop()

    def join(self):
        """
        等待后台线程退出。
        """
        if self.thread and self.thread.is_alive():
            self.thread.join()

    def send_packet(self, packet: dict):
        """
        发送数据包字典到服务器。

        如果需要发送非json数据，请重载实现本函数。
        """
        text = json.dumps(packet)
        self._record_last_sent_text(text)

        coro = self._ws.send_str(text)
        asyncio.run_coroutine_threadsafe(coro, self.loop)
        self._log('sent text: %s', text)

    def _log(self, msg, *args):
        """记录日志信息"""
        logger = self.logger
        if logger:
            logger.debug(msg, *args)

    def run(self):
        """
        在后台线程中运行的主函数
        """
        if not self.loop.is_running():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        asyncio.run_coroutine_threadsafe(self._run(), self.loop)

    async def _run(self):
        """
        在事件循环中运行的主协程
        """
        self._ws = await self.session.ws_connect(
            self.host,
            proxy=self.proxy,
            verify_ssl=False
        )

        self.on_connected()

        async for msg in self._ws:
            text = msg.data
            print("recv", text)

            self._record_last_received_text(text)

            try:
                data = self.unpack_data(text)
            except ValueError as e:
                print("websocket unable to parse data: " + text)
                raise e

            self._log('recv data: %s', data)
            self.on_packet(data)

    @staticmethod
    def unpack_data(data: str):
        """
        对字符串数据进行json格式解包

        如果需要使用json以外的解包格式，请重载实现本函数。
        """
        return json.loads(data)

    @staticmethod
    def on_connected():
        """
        Callback when websocket is connected successfully.
        """
        pass

    @staticmethod
    def on_disconnected():
        """
        Callback when websocket connection is lost.
        """
        pass

    @staticmethod
    def on_packet(packet: dict):
        """
        Callback when receiving data from server.
        """
        pass

    def on_error(self, exception_type: type, exception_value: Exception, tb):
        """
        Callback when exception raised.
        """
        sys.stderr.write(
            self.exception_detail(exception_type, exception_value, tb)
        )
        return sys.excepthook(exception_type, exception_value, tb)

    def exception_detail(
        self, exception_type: type, exception_value: Exception, tb
    ):
        """
        Print detailed exception information.
        """
        text = "[{}]: Unhandled WebSocket Error:{}\n".format(
            datetime.now().isoformat(), exception_type
        )
        text += "LastSentText:\n{}\n".format(self._last_sent_text)
        text += "LastReceivedText:\n{}\n".format(self._last_received_text)
        text += "Exception trace: \n"
        text += "".join(
            traceback.format_exception(exception_type, exception_value, tb)
        )
        return text

    def _record_last_sent_text(self, text: str):
        """
        Record last sent text for debug purpose.
        """
        self._last_sent_text = text[:1000]

    def _record_last_received_text(self, text: str):
        """
        Record last received text for debug purpose.
        """
        self._last_received_text = text[:1000]
