"""
Test
A Class Widgets plugin.
"""

from ClassWidgets.SDK import CW2Plugin, PluginAPI
import socket
import json
import time
from loguru import logger
import threading


class Plugin(CW2Plugin):
    def __init__(self, api: PluginAPI):
        super().__init__(api)
        # 新增服务器实例变量
        self.server = None
        # 其他初始化代码...
        self.last_heartbeat = 0
        self.notification_provider = None
        self.connection_check_thread = None
        self.stop_connection_check = threading.Event()
        # 请在此导入第三方库 / Import third-party libraries here

    def on_load(self):
        super().on_load()
        
        self.notification_provider = self.api.notification.register_provider(
            provider_id=self.pid,
            name="TeachConnect",
            icon="icon.png"
		)

        # 创建服务器实例并保存为成员变量
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.connect(("frp.freezing.top", 11224))
            self.server.setblocking(False)  # 非阻塞模式
            self.last_heartbeat = time.time()
            logger.info("开始接收消息")

            if not self.connection_check_thread or not self.connection_check_thread.is_alive():
                self.stop_connection_check.clear()
                self.connection_check_thread = threading.Thread(target=self._check_connection, daemon=True)
                self.connection_check_thread.start()
                logger.info("✓ 已启动连接检查线程")

        except Exception:
            self.server = None
            
    def update_messages(self):
        current_time = time.time()
        
        if self.server is None:
            self.on_load()
            return
        try:
            if current_time - self.last_heartbeat > 7:
                try:
                    self.server.setblocking(False)  # 非阻塞模式
                    self.server.send(b'ping')
                    self.last_heartbeat = current_time
                except:
                    self.server = None
                    return

            data = self.server.recv(1024)
            if data:
                if data != b'pong':
                    try:
                        msg = json.loads(data.decode("utf-8"))
                        name = msg.get("name", "未知")
                        message = msg.get("message", "无内容")
                        
                        self.notification_provider.push(
                            level=1,
                            title=name,
                            message=message,
                            duration=0,
                            closable=False
                        )
                    except json.JSONDecodeError:
                        logger.error("接收到无法解析的消息")
                    except Exception as e:
                        logger.error(f"处理消息时发生错误: {e}")
                else:
                    print("收到心跳回复")
                    return

        except BlockingIOError:
            pass  # 没有新连接时正常继续
        except Exception as e:
            logger.error(f"接收消息时发生错误: {e}")


    def on_unload(self):
        print(f"Test unloaded")

    def _check_connection(self):
        """定期检查连接状态"""
        while not self.stop_connection_check.is_set():
            try:
                if self.server is None:
                    logger.info("🔄 重新连接服务器...")
                    self.on_load()
                
                # 定期调用 update_messages
                self.update_messages()
                
                time.sleep(2)  # 每2秒检查一次
            except Exception as e:
                logger.error(f"连接检查出错: {e}")
                time.sleep(5)  # 出错时等待更长时间
