# 1.1.1版本

1. 基于mypy完善代码类型提示

# 1.1.0版本

1. 替换aiohttp异步通讯模式，改为使用websocket-client多线程模式
2. 替换使用pyproject.toml配置
3. ruff和mypy代码质量优化

# 1.0.6版本

1. 在Windows系统上必须使用Selector事件循环，否则可能导致程序崩溃
2. 客户端停止时，确保关闭所有会话
3. 等待异步关闭任务完成后，才停止事件循环
4. 增加默认的60秒超时自动断线重连

# 1.0.5版本

1. 修复aiohttp的代理参数proxy传空时必须为None的问题

# 1.0.4版本

1. 对Python 3.10后asyncio的支持修改