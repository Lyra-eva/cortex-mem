# 监控告警系统

## 快速启动

### 1. 安装 Prometheus + Grafana

```bash
# macOS
brew install prometheus grafana

# 启动 Prometheus
prometheus --config.file=monitoring/prometheus.yml

# 启动 Grafana
grafana-server --config=/usr/local/etc/grafana/grafana.ini
```

### 2. 访问界面

- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)

### 3. 配置 Grafana

1. 添加 Prometheus 数据源 (http://localhost:9090)
2. 导入仪表板（推荐 ID: 10280 - Prometheus Stats）

## 监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| `up` | 服务在线状态 | <1 触发宕机告警 |
| `request_errors_total` | 错误总数 | 错误率>10% 触发 |
| `request_duration_seconds` | 响应时间 | P95>1s 触发 |
| `memory_total` | 记忆总数 | 增长>100 条/小时 |

## 告警渠道

当前配置为本地告警，可扩展：

- **邮件告警:** 配置 SMTP
- **钉钉/飞书:** Webhook
- **Telegram:** Bot API

## 自定义指标

在 `embedding_server.py` 中添加 Prometheus metrics:

```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('request_total', 'Total requests')
REQUEST_LATENCY = Histogram('request_duration_seconds', 'Request latency')
```
