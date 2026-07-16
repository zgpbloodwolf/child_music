"""儿童音乐后端服务主包。

模块划分:
- config:从 .env 读取配置(端口/存储根/公网 URL/管理 token/CORS)
- database:SQLAlchemy 引擎、会话工厂、ORM 基类
- models:ORM 模型(categories / sub_categories / songs)
- schemas:Pydantic 请求/响应模型(字段 camelCase 对齐前端 TS 契约)
- deps:依赖注入(get_db / verify_admin_token)
- services:文件落盘(storage)、元数据查询与 URL 拼接(meta)
- routers:只读查询(catalog)、管理写操作(admin)
"""
