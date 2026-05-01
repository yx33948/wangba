# 卡密验证系统说明文档

## 概述

本集成采用**在线激活 + 服务端签发离线票据**机制：

- 首次激活/补票据时向服务器在线验证
- 日常运行优先使用本地缓存的服务端签名票据
- 客户端仅保存服务端公钥，不再保存共享 `API_SECRET_KEY`
- 网络抖动时，只要本地票据未过期，自动化仍可继续运行

- 在线验证服务器：`https://baota.yx33948.top/api/license.php`
- 验证超时：15 秒
- 最大重试次数：3 次
- 服务端拒绝后冷却期：5 分钟（避免反复请求）

### 地址/IP 配置文件

- 客户端地址配置：`netcafe_automation/license_server_endpoints.json`
- 客户端公钥文件：`netcafe_automation/license_ticket_public_key.pem`
- 宝塔端运行配置：`license-server/license_server_runtime.json`
- 宝塔端私钥文件：`license-server/keys/license_ticket_private.pem`
- 宝塔端公钥文件：`license-server/keys/license_ticket_public.pem`

后续更换服务器时，优先修改上述配置文件，不需要再回代码里改域名或 IP。

### 同步脚本

宝塔端提供两个辅助脚本：

```bash
python tools/sync_client_license_assets.py
python tools/rotate_license_ticket_keys.py
```

- `sync_client_license_assets.py`
  - 根据 `license_server_runtime.json` 生成客户端 `license_server_endpoints.json`
  - 同步服务端公钥到客户端 `license_ticket_public_key.pem`
- `rotate_license_ticket_keys.py`
  - 重生成服务端签名私钥/公钥
  - 自动调用同步脚本，把新公钥同步到客户端

典型迁移步骤：

1. 修改宝塔端 `license_server_runtime.json` 里的新域名/IP
2. 如需换签名密钥，执行 `python tools/rotate_license_ticket_keys.py`
3. 如果只换服务器地址、不换密钥，执行 `python tools/sync_client_license_assets.py`
4. 重新部署客户端目录中的：
   - `license_server_endpoints.json`
   - `license_ticket_public_key.pem`

---

## 一、卡密格式

| 类型 | 格式 | 示例 |
|------|------|------|
| 正式卡密 | `XXXXXXXXXXXXXXXXXXXX-YYYYMMDD`（20位+8位日期） | `NETCAFEA1B2C3D4E5F6G7-20261231` |
| 试用卡密（带日期） | `TRIALXXXXXXXXXXXXXXXXX-YYYYMMDD`（17位+8位日期） | `TRIAL1234567890123456-20260405` |
| 试用卡密（无日期） | `TRIALXXXXXXXXXXXXXXXXX`（17位） | `TRIAL1234567890123456` |

> 日期后缀 `YYYYMMDD` 为到期日期，本地解析为当天 23:59:59 截止。

---

## 二、验证流程

### 2.1 系统启动时

```
HA 启动 → async_setup() → 调用 license_mgr.get_license_status()
  ├─ 本地检查：expire_date 是否过期（硬性截止）
  ├─ 在线验证：向服务器发送 verify 请求（权威来源）
  │   ├─ 成功 → 同步服务端到期日期到本地缓存 → is_valid = True
  │   └─ 失败 → 根据失败原因判断：
  │       ├─ 明确拒绝（不存在/已撤销/已过期/激活次数用完）→ is_valid = False
  │       └─ 网络异常 → 回退本地缓存判断
  └─ is_valid = False → 立即调用 _pause_automation() 暂停所有自动化
```

### 2.2 定时检查（每 10 分钟）

```
async_track_time_interval(10分钟) → _check_license_callback()
  ├─ 获取最新 license_status
  ├─ 有效 → 无效 → 打印 "卡密已过期" → 调用 _pause_automation()
  ├─ 即将到期（<=7天）→ 打印警告日志
  └─ 无效 → 有效 → 调用 _resume_automation() 恢复自动化
```

### 2.3 设备扫描时（每 5 秒）

```
_update_devices() 定时回调
  ├─ 检查 automation_paused 标志 → True 则直接跳过扫描
  └─ 调用 license_mgr.verify_license()
      ├─ 无效 → 打印警告 → 调用 _pause_automation() → 跳过扫描
      └─ 有效 → 正常执行设备扫描
```

### 2.4 配置加载时

```
async_setup_entry() → 调用 license_mgr.verify_license()
  ├─ 无效 → 打印错误 → return False（阻止加载配置条目）
  └─ 有效 → 正常创建设备和实体
```

### 2.5 Config Flow 界面

```
用户进入集成配置 → async_step_user()
  ├─ is_valid = True → 显示正常配置界面（表单/CSV选择）
  └─ is_valid = False → 跳转到 async_step_activate_license() 激活界面
```

---

## 三、暂停与恢复机制

### 3.1 暂停自动化 (`_pause_automation`)

触发条件：卡密过期、无效、或在线验证明确拒绝。

执行操作：
1. 设置 `automation_paused = True`
2. 停止设备跟踪定时器（`update_listener`）
3. 清除所有设备的 `_last_seen`，设置 `_reachable = False`
4. 通过 coordinator 通知所有实体更新为离线状态

### 3.2 恢复自动化 (`_resume_automation`)

触发条件：卡密重新激活成功、或延期成功。

执行操作：
1. 清除 `automation_paused` 标志
2. 重新启动设备跟踪定时器
3. 重新加载所有配置条目恢复实体

---

## 四、激活卡密的方法

### 方法 1：Config Flow 界面（推荐）

在 HA 界面中：**设置 → 设备与服务 → 网吧智能自动化 → 配置 → 卡密管理**，输入卡密即可。

首次添加集成时，如果检测到卡密无效，会自动跳转到激活界面。

### 方法 2：Service 调用

在 **开发者工具 → 服务** 中调用：

```yaml
service: netcafe_automation.activate_license
data:
  license_key: "NETCAFEA1B2C3D4E5F6G7-20261231"
  device_id: ""  # 可选
```

激活成功后会自动检查 `automation_paused` 状态，如果处于暂停则自动恢复。

### 方法 3：自动化脚本

```yaml
automation:
  - alias: "激活卡密"
    trigger:
      - trigger: homeassistant
        event: start
    action:
      - action: netcafe_automation.activate_license
        data:
          license_key: "YOUR_LICENSE_KEY"
```

---

## 五、其他卡密相关服务

### 查询卡密状态

```yaml
service: netcafe_automation.get_license_status
```

### 停用卡密

```yaml
service: netcafe_automation.deactivate_license
```

### 在线延期卡密

```yaml
service: netcafe_automation.renew_license
data:
  extra_days: 30
```

### 创建试用卡密（管理员用）

```yaml
service: netcafe_automation.create_trial_license
data:
  hours: 72
  notes: "客户A试用3天"
```

---

## 六、卡密状态传感器

集成提供 3 个传感器实体，可用于仪表盘监控：

| 传感器 | 说明 | 示例值 |
|--------|------|--------|
| `sensor.卡密到期时间` | 到期日期时间 | `2026-12-31 23:59:59` |
| `sensor.卡密状态` | 当前状态 | `有效` / `已过期` / `无效` |
| `sensor.卡密剩余天数` | 剩余天数 | `30`（天） |

传感器每 10 分钟自动更新，包含 `days_remaining`、`hours_remaining`、`is_valid`、`is_expired` 等属性。

---

## 七、验证冷却机制

当在线验证返回明确的拒绝状态（HTTP 403/404/410）时，系统会进入 **5 分钟冷却期**，期间不再向服务器发送验证请求，而是使用本地已签发的服务端凭证判断。

冷却期仅在 `verify` 操作中生效，用户主动激活（`activate`）不受冷却限制。

---

## 八、关键代码位置

| 文件 | 说明 |
|------|------|
| `license_manager.py` | 卡密管理核心逻辑（验证、激活、延期、存储） |
| `license_middleware.py` | 装饰器，用于在自动化操作前拦截检查 |
| `__init__.py` | 暂停/恢复自动化、定时检查、服务注册 |
| `config_flow.py` | 配置流程中的卡密激活界面 |
| `sensor.py` | 卡密状态传感器（到期时间、状态、剩余天数） |
| `device_tracker.py` | 设备跟踪实体（含 `automation_paused` 兜底检查） |
