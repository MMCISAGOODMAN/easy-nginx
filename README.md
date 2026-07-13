# Easy Nginx - Nginx 可视化配置工具

面向不懂 Nginx 语法的普通开发者/站长，通过可视化表单填写，自动生成合法的 nginx.conf 配置文件。

## 项目目录结构

```
easy-nginx/
├── app.py                      # Flask 主程序入口
├── config.py                   # 应用配置
├── requirements.txt            # Python 依赖
├── README.md                   # 项目说明
├── data/
│   └── sites.json              # 站点配置数据（本地存储）
├── backups/                    # 配置文件备份（带时间戳）
├── nginx_output/               # 生成的 Nginx 配置文件
├── ssl_certs/                  # SSL 证书存储
├── core/
│   ├── __init__.py
│   ├── generator.py            # Nginx 配置生成核心逻辑
│   ├── validator.py            # 表单数据校验
│   ├── nginx_manager.py        # nginx -t / reload / version
│   └── storage.py              # sites.json 读写与备份
├── schemas/
│   └── site.schema.json        # 站点配置 JSON Schema
├── templates/
│   ├── base.html               # 页面基础模板
│   ├── index.html              # 站点列表页
│   ├── site_form.html          # 新建/编辑分步表单
│   └── nginx/
│       └── site.conf.j2        # Nginx 配置 Jinja2 模板
└── static/
    ├── css/
    │   └── style.css           # 样式（蓝白灰主色调）
    └── js/
        └── form.js             # 表单交互逻辑
```

## 快速开始

### 1. 安装依赖

```bash
cd easy-nginx
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 启动应用

```bash
python app.py
```

浏览器访问 http://127.0.0.1:5000

### 3. 生产环境配置（可选）

通过环境变量自定义：

```bash
# 将生成的配置输出到系统 Nginx 目录
export NGINX_OUTPUT_DIR=/etc/nginx/sites-enabled

# 指定 nginx 可执行文件路径
export NGINX_BIN=/usr/sbin/nginx

# 监听地址和端口
export HOST=0.0.0.0
export PORT=8080

python app.py
```

> 注意：写入 `/etc/nginx/sites-enabled/` 需要 root 权限。

## 功能说明

| 功能 | 说明 |
|------|------|
| 站点列表 | 卡片网格展示所有站点，显示名称、域名、端口、运行状态 |
| 分步表单 | 4 步引导：基本信息 → 网站文件 → 转发规则 → 性能与高级 |
| 预览配置 | 弹窗显示生成的 nginx.conf 纯文本 |
| 保存配置 | 保存到文件并自动执行 `nginx -t` 语法检查 |
| 重启 Nginx | 保存后执行 `nginx -s reload` |
| 自动备份 | 每次保存自动备份旧配置到 `backups/` 目录 |
| 一键回滚 | 恢复到上一个备份版本 |
| 目录浏览 | 选择服务器上的网站根目录 |
| SSL 证书 | 支持上传 HTTPS 证书和私钥 |

## 转发规则 → Nginx 映射表

界面中全程不出现 `location`、`upstream`、`proxy_pass` 等专业术语。以下是用户填写的「转发规则」与底层 Nginx 指令的对应关系：

| 界面字段 | 生成的 Nginx 指令 | 说明 |
|----------|-------------------|------|
| 触发路径 + **以...开头** | `location /api/ { ... }` | 前缀匹配，匹配以该路径开头的所有请求 |
| 触发路径 + **以...结尾** | `location ~ \.jpg$ { ... }` | 正则匹配，匹配以该后缀结尾的请求 |
| 触发路径 + **完全匹配** | `location = /exact { ... }` | 精确匹配，仅匹配完全相同的路径 |
| 处理方式：**返回静态文件** | `try_files $uri $uri/ =404;` | 从网站根目录返回对应的静态文件 |
| 处理方式：**转发到后端服务** | `proxy_pass http://127.0.0.1:8080;` | 将请求转发到指定的后端地址 |
| 保留原始域名（开启） | `proxy_set_header Host $host;` | 转发时保留浏览器地址栏中的域名 |
| 超时时间 | `proxy_connect_timeout 30s;` 等 | 设置与后端通信的超时时间 |
| 处理方式：**重定向到其他地址** | `return 301 https://example.com;` | 将访问者跳转到目标地址 |
| 允许列出目录（开启） | `autoindex on;` | 无默认页时显示目录中的文件列表 |
| 启用 Gzip 压缩 | `gzip on; gzip_types ...;` | 压缩文本类响应以节省带宽 |
| 静态文件缓存时间 | `expires 7d;` | 设置浏览器缓存静态资源的时长 |
| 限制 IP 访问 | `allow 1.2.3.4; deny all;` | 仅允许列表中的 IP/网段访问 |
| 自定义额外配置 | 原样插入 server 块内 | 高级用户直接写入 Nginx 指令 |

### 匹配方式详解

```
用户填写                    生成的 location
─────────────────────────────────────────────
/api/    + 以...开头    →   location /api/ { }
.jpg     + 以...结尾    →   location ~ \.jpg$ { }
/login   + 完全匹配      →   location = /login { }
```

### 处理方式详解

```
用户选择                    生成的配置块
─────────────────────────────────────────────
返回静态文件            →   try_files $uri $uri/ =404;
转发到后端服务          →   proxy_pass http://后端地址;
                            proxy_set_header Host $host; (如开启)
                            proxy_*_timeout 超时秒数;
重定向到其他地址        →   return 301 目标地址;
```

## 配置文件格式

站点数据存储在 `data/sites.json`，格式参见 `schemas/site.schema.json`。

示例：

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "我的博客",
  "domains": "blog.example.com",
  "port": 80,
  "https_enabled": false,
  "root_dir": "/var/www/blog",
  "index_file": "index.html",
  "autoindex": false,
  "rules": [
    {
      "trigger_path": "/api/",
      "match_type": "prefix",
      "action": "proxy",
      "backend_address": "127.0.0.1:3000",
      "preserve_host": true,
      "timeout": 30
    }
  ],
  "worker_connections": 1024,
  "gzip_enabled": true,
  "cache_duration": "7d",
  "ip_whitelist": "",
  "custom_config": ""
}
```

## 备份与回滚

- 每次保存配置时，旧版本自动备份到 `backups/{site_id}_{时间戳}.conf`
- 编辑页面底部点击「↩️ 回滚上一版」可恢复到最近的备份
- 回滚后自动执行 `nginx -t` 语法检查

## 模拟模式

如果系统未安装 Nginx，工具自动进入模拟模式：
- 版本显示为「未安装（模拟模式）」
- 保存和重载操作正常完成，但不会真正执行 nginx 命令
- 配置文件仍会生成到 `nginx_output/` 目录

## 技术栈

- **后端**：Python 3.10+ / Flask
- **模板引擎**：Jinja2（Web 页面 + Nginx 配置生成）
- **前端**：原生 HTML/CSS/JavaScript
- **数据存储**：本地 JSON 文件
- **完全离线**：不调用任何外部 API

## License

MIT
