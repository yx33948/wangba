# netcafe_automation 项目复刻 Skill

## 目标

这份文档用于复刻 `C:\Users\Administrator\Desktop\软件版网吧系统\netcafe_automation` 项目的核心功能与业务实现逻辑。

范围只包含：

- 功能模块
- 数据结构
- 页面行为
- 前后端接口关系
- 自动化业务规则
- 鉴权 / 卡密 / 天气 / 存储 / 房间映射逻辑

明确排除：

- `1.css` 里的视觉风格、美化、动效、布局细节

---

## 1. 项目本质

这是一个运行在 **Home Assistant** 内的自定义集成，核心职责是：

1. 通过 CSV 维护“电脑 IP -> 包厢”的映射。
2. 将每台电脑生成 `device_tracker` 实体，用在线状态表示包厢占用。
3. 自动识别或手动绑定每个包厢的空调 / 灯光 / 新风实体。
4. 根据包厢占用状态，执行空调、灯光、新风的自动化联动。
5. 提供一个 Web 总控台（`1.html + 1.js`）用于查看状态、手动控制、配置系统。
6. 提供一个分机小控端（subcontrol）给包厢端或局域网终端使用。
7. 通过卡密系统控制整个集成是否可用。

一句话概括：

**这是一个“基于包厢占用状态驱动环境设备联动”的网吧中控系统。**

---

## 2. 文件夹职责总览

### 根目录核心 Python 模块

- `__init__.py`
  - 集成入口
  - 注册服务
  - 启动扫描定时器
  - 启动 / 暂停自动化
  - 注册所有 Web API 和静态页面入口

- `config_flow.py`
  - Home Assistant 配置流
  - 导入 / 校验 CSV
  - 首次安装配置
  - 天气配置初始化
  - 激活卡密后的恢复逻辑

- `room_control.py`
  - 项目最核心的业务层
  - 房间配置默认值、归一化、自动识别、自动化执行、运行时日志、分机权限控制都在这里

- `device_tracker.py`
  - 为每台电脑创建 `device_tracker`
  - 在线状态来自扫描器结果

- `scanner.py`
  - 扫描 IP 在线状态
  - 管理离线确认、ARP / ping 等探测结果

- `coordinator.py`
  - 给 `device_tracker` 提供协调器

- `sensor.py`
  - 暴露卡密状态、月份、天气等传感器

- `button.py`
  - 提供“一键清除所有 device_tracker”按钮实体

- `storage_manager.py`
  - 文件存储层
  - 管理 CSV、rooms、config 的 JSON / CSV 文件

- `license_manager.py`
  - 卡密校验、激活、续期、试用逻辑

- `license_middleware.py`
  - 自动化动作前的卡密校验辅助

- `weather_service.py`
  - 天气查询与天气地区搜索

### `www/` 前端目录

- `1.html`
  - 主控制台页面骨架

- `1.js`
  - 主控制台全部功能逻辑

- `1.css`
  - 纯样式，复刻业务时可忽略

- `subcontrol_app.html`
  - 分机小控端页面

- `automation_config.html`
  - 自动化配置相关页面

- `index.html` / `index2.html`
  - 其他展示入口

- `www/__init__.py`
  - 不是普通前端文件，而是 **Web API / 页面路由层**
  - 负责把 `1.html`、`1.js`、接口 `/api/netcafe/...` 暴露给前端

---

## 3. 系统核心数据模型

## 3.1 CSV 映射

最原始的数据来源是 CSV：

- 字段：`ip_address`, `room_name`
- 含义：一台电脑 IP 属于哪个包厢

这个 CSV 是整个项目的基础，因为：

1. 它决定生成哪些 `device_tracker`
2. 它决定每个包厢有哪些电脑
3. 它是后续“包厢占用判断”的默认基础

---

## 3.2 房间运行数据（rooms_data）

项目会把 CSV 解析成“房间 -> 电脑列表”的结构，典型含义是：

- 一个房间名
- 多台电脑
- 每台电脑对应：
  - `entity_id`
  - `ip_address`
  - 在线状态
  - 最近在线时间

这个结构被用于：

- 设备追踪
- 房间占用判断
- 仪表盘房间列表

---

## 3.3 系统配置（system config）

前端“设置中心”最终保存的是统一系统配置，核心结构为：

- `rooms`
  - 每个房间一份配置
- `dashboard`
  - 仪表盘能耗配置等
- `ui`
  - 品牌名、主题、Logo
- `global_settings`
  - 全局联动策略、默认季节参数、实体筛选规则、分机信任配置

### 每个房间配置的关键内容

- `entities`
  - `ac`
  - `lights`
  - `fresh_air`

- `entity_filters`
  - 空调 / 灯光 / 新风识别的包含与排除关键词

- `lighting_presets`
  - `full_on`
  - `half_on`
  - `full_off`

- `modes`
  - `selected_season`
  - `summer`
  - `winter`
  - `custom`

- `automation`
  - 总开关
  - 触发模式：`device_tracker` / `sensor` / `hybrid`
  - 空调自动开关
  - 灯光自动开关
  - 新风自动开关
  - 延迟时间
  - 温度上下限
  - 工作时段

- `subcontrol`
  - 分机是否启用
  - 是否允许改温度
  - 是否允许改模式
  - 是否允许控灯
  - 是否继承总控温度限制

---

## 3.4 运行时状态（runtime）

`room_control.py` 里维护一个运行时 store，至少包含：

- 每个房间当前是否占用
- 每个房间待执行的延时任务
- 空调手动覆盖截止时间
- 最近运行日志

这个 runtime 不只是缓存，它直接影响：

- 自动化是否触发
- 延迟动作是否取消
- 手动控制后多久恢复自动策略

---

## 4. 系统启动逻辑

## 4.1 `async_setup`

集成加载时会做这些事：

1. 初始化 `hass.data[DOMAIN]`
2. 初始化扫描器 `scanner`
3. 初始化 `automation_paused = False`
4. 注册定时扫描任务
5. 注册 CSV / 卡密 / 清理等服务
6. 注册总控台、分机、天气等全部 HTTP 视图

## 4.2 `async_setup_entry`

配置项加载时会做这些事：

1. 校验卡密
2. 卡密无效则暂停自动化并阻止配置项加载
3. 初始化 Hub 设备
4. 从 `StorageManager` 读取 CSV
5. 从 CSV 解析包厢与电脑
6. 为每台电脑准备 `DeviceData` 和 coordinator
7. 初始化房间控制运行时
8. 转发加载：
   - `device_tracker`
   - `button`
   - `sensor`

---

## 5. 电脑在线状态 -> 包厢占用 的实现逻辑

这是项目最重要的基础链路。

## 5.1 电脑在线检测

扫描器周期性更新每台电脑的：

- 是否可达
- 最近在线时间
- 连续失败次数
- 最后探测方式

然后 coordinator 把这个结果同步给 `device_tracker`。

## 5.2 默认占用逻辑

如果一个房间内任意电脑在线，则该房间默认可视为“有人”。

## 5.3 可配置占用逻辑

项目支持三种触发模式：

- `device_tracker`
  - 用电脑在线状态判断有人 / 无人

- `sensor`
  - 用 `sensor` / `binary_sensor` 判断有人 / 无人

- `hybrid`
  - 两者任一命中都算有人

### 占用判断流程

1. 读取房间自动化配置中的 `trigger_mode`
2. 查找显式指定的实体
3. 如果没显式指定，则按关键词匹配相关实体
4. 判断这些实体是否处于“有人”状态
5. 如果没有任何匹配结果，则回退到电脑在线数判断

### 传感器被认为“有人”的状态

以下状态被视为 active：

- `home`
- `on`
- `online`
- `connected`
- `present`
- `occupied`
- `detected`

数值型状态则以 `> 0` 判定为 active。

---

## 6. 房间实体绑定逻辑

项目要把每个房间绑定到：

- 1 台空调
- 多个灯光
- 1 个新风

## 6.1 绑定来源顺序

优先级大致是：

1. 用户在配置中显式保存的实体
2. 按“房间分组识别”自动推断的实体
3. 按“房间名 + 实体名相似度”自动推断的实体
4. 再应用全局 / 房间级关键词过滤

## 6.2 自动识别思路

`room_control.py` 做了大量房间名归一化处理，例如：

- 去掉“空调”、“灯带”、“新风”等后缀
- 统一包厢 / 包间 / 房 / 区 等叫法
- 提取房间号
- 识别单双三四人房、VIP 房等
- 用关键字和房号推断某实体属于哪个包厢

## 6.3 灯光识别特点

灯光是多选实体，因此：

- 空调 / 新风通常只取最佳匹配一个
- 灯光会保留多个候选
- `half_on` 预设默认取前半部分灯

---

## 7. 自动化业务逻辑

## 7.1 自动化触发时机

每次设备扫描完成后，都会调用：

- `async_process_room_automation(hass)`

它会比较：

- 当前占用状态
- 上一次占用状态

只有发生变化才触发自动化调度。

## 7.2 “有人”时的动作

当包厢从无人变有人：

1. 记录运行日志
2. 检查总自动化开关
3. 检查是否在工作时段内
4. 如果允许：
   - 空调按季节模式自动开启
   - 灯光执行到店预设
   - 新风自动开启
5. 每个动作都支持独立延迟

## 7.3 “无人”时的动作

当包厢从有人变无人：

- 空调延迟关闭
- 灯光执行离店预设
- 新风延迟关闭

## 7.4 手动覆盖逻辑

如果用户手动控制了空调：

1. 记录“手动覆盖”状态
2. 自动化短时间内不再覆盖空调
3. 到达恢复时间后，如果房间仍有人且允许自动化，则恢复自动设定

这个设计避免了：

- 用户刚手动调温
- 自动化立刻把设置改回去

---

## 8. 房间动作执行模型

前端不会直接调用 HA 原始服务，而是统一调用：

- `/api/netcafe/panel/room/action`

后端由 `async_execute_room_action()` 解析业务动作。

支持的核心动作包括：

- 空调
  - `ac_turn_on`
  - `ac_turn_off`
  - `ac_set_temperature`
  - `ac_set_hvac_mode`
  - `ac_set_fan_mode`
  - `ac_apply_season`

- 灯光
  - `light_apply_preset`
  - `light_toggle`
  - `light_set_brightness`
  - `light_set_color_temperature`
  - `light_set_color`

- 新风
  - `fresh_air_turn_on`
  - `fresh_air_turn_off`
  - `fresh_air_set_mode`
  - `fresh_air_set_percentage`

后端动作层的价值是：

1. 统一前端调用协议
2. 屏蔽 HA 各域服务差异
3. 在动作前插入权限 / 卡密 / 分机限制
4. 自动写运行日志
5. 支持 `persist` 把部分动作顺带写回配置

---

## 9. 卡密系统逻辑

卡密不是点缀，而是整个系统的总开关。

## 9.1 卡密无效时

系统会：

1. 阻止配置项加载
2. 暂停自动化
3. 停止扫描定时器
4. 把所有追踪实体标记为离线
5. 锁定面板核心接口

## 9.2 卡密有效时

系统会：

1. 恢复自动化
2. 恢复扫描任务
3. 重新刷新状态

## 9.3 卡密相关能力

通过服务或 API 支持：

- 激活
- 查询状态
- 停用
- 续期
- 创建试用卡密

前端顶部有 license badge，页面加载时也会单独读卡密状态。

---

## 10. 面板鉴权逻辑

主控台不是靠 Home Assistant 原生登录，而是走一套**远程账号体系**。

## 10.1 登录模型

前端通过：

- `/api/netcafe/panel/auth/login`
- `/api/netcafe/panel/auth/register`
- `/api/netcafe/panel/auth/session`

与远程认证服务通信。

## 10.2 token 机制

token 结构是：

- `payload.signature`

校验项包括：

- 版本号
- 过期时间
- 用户名
- license_key
- HMAC 签名

## 10.3 页面访问策略

- 面板公开页面可以打开
- 但大多数数据接口必须通过 `_require_panel_auth`
- 未登录时前端会跳回登录页

## 10.4 登录后卡密同步

登录成功后，会用登录用户带回的 `license_key` 尝试同步本地卡密状态。

这意味着：

**账号系统和卡密系统是耦合的。**

---

## 11. 分机 subcontrol 逻辑

这是项目的第二个控制端。

## 11.1 目标

给包厢本地终端或局域网终端提供一个受限控制页，只允许控制“自己房间”的设备。

## 11.2 访问控制

分机访问有两种通过方式：

1. 已有 HA 用户身份
2. 命中总控配置的局域网白名单 CIDR

否则拒绝访问。

## 11.3 分机房间识别

分机会把自己的本地 IP 传给：

- `/api/netcafe/subcontrol/bootstrap`

后端根据：

- IP
- CSV 中的电脑映射

推断当前终端属于哪个包厢，再下发该包厢的可控能力。

## 11.4 分机动作限制

分机不是全权限，房间配置的 `subcontrol` 决定：

- 能不能开关空调
- 能不能改温度
- 能不能改空调模式
- 能不能改风速
- 能不能控灯
- 是否强制遵循总控的季节策略

---

## 12. 天气系统逻辑

天气是仪表盘环境信息的一部分。

## 12.1 数据来源

`weather_service.py` 使用 `weather.com.cn` 相关接口获取：

- 当前天气
- 温度
- 湿度
- 风力
- 生活指数

## 12.2 配置流程

总控设置页支持：

1. 输入关键字搜索地区
2. 选择地区 `area_id`
3. 保存天气域名与地区配置

对应接口：

- `POST /api/netcafe/panel/weather/search`
- `GET/POST /api/netcafe/panel/weather/config`
- `GET /api/netcafe/weather?city=...`

---

## 13. `1.html` 的页面功能骨架

`1.html` 只做结构容器，本身不承载业务判断；真实逻辑几乎都在 `1.js`。

## 13.1 页面主结构

分为三层：

1. 左侧侧栏
   - 页面切换入口
   - 首页总览
   - 包厢管理
   - 空调控制
   - 灯光管理
   - 环境控制
   - 系统设置

2. 顶部状态栏
   - 页面标题
   - 天气
   - 时间
   - 连接状态
   - 卡密状态
   - 当前用户
   - 刷新按钮

3. 主内容区
   - `page-dashboard`
   - `page-room`
   - `page-ac`
   - `page-light`
   - `page-fan`
   - `page-settings`

## 13.2 弹窗结构

页面里预置了 `statusModal`，用于显示：

- 房间详细状态
- 空调控制详情
- 灯光详情
- 新风详情

所以 `1.html` 的定位可以概括为：

**一个多页面单页应用的壳子 + 若干挂载点。**

---

## 14. `1.js` 的功能分层

`1.js` 是整个总控前端的业务核心。

## 14.1 状态中心

`state` 统一保存：

- `overview`
- `config`
- `entities`
- `diagnostics`
- `license`
- `weather`
- `energyHistory`
- `dailySummary`
- 当前页
- 当前房间
- 当前设置子页
- 当前主题
- 当前用户 token
- 刷新状态
- 筛选条件
- settings 草稿

这是一个典型的“无框架单文件状态管理”实现。

## 14.2 基础能力层

主要负责：

- HTML 转义
- 时间格式化
- 配置默认值与归一化
- 主题设置
- 本地存储读写
- 品牌设置
- 房间配置 / 全局配置合并

## 14.3 API 调用层

核心函数是：

- `requestJson(path, options)`

它负责：

- 拼接 API 地址
- 自动带 token
- 统一处理 401 / 403 / license 锁定 / 普通错误

## 14.4 认证层

包括：

- 恢复登录状态
- 获取当前 session
- 注销
- 登录后同步页面状态

## 14.5 页面渲染层

按页面拆成：

- `renderDashboard()`
- `renderRoomPage()`
- `renderAcPage()`
- `renderLightPage()`
- `renderFanPage()`
- `renderSettingsPage()`

每个页面都是：

1. 从 `state` 取数据
2. 计算摘要
3. 拼接 HTML
4. 注入对应的容器

## 14.6 弹窗控制层

通过：

- `openStatusModal()`
- `closeStatusModal()`

给房间详情和设备详情做统一弹窗承载。

## 14.7 动作层

核心入口：

- `performRoomAction(roomId, action, value, persist)`
- `batchRoomAction(target, action, value, persist)`

前端所有控制按钮最终都归到这里。

## 14.8 刷新层

核心函数：

- `reloadAll(showToast)`

职责：

1. 拉 overview
2. 拉系统配置
3. 拉实体候选
4. 拉 diagnostics
5. 拉天气
6. 拉能耗汇总
7. 重新渲染所有页面

并且有：

- 自动刷新
- 失败退避重试
- 设置页暂停自动刷新

---

## 15. `1.html / 1.js` 页面功能说明

## 15.1 首页总览 `dashboard`

功能包括：

- 包厢总数、有人房间数
- 空调 / 灯光 / 新风在线与开启统计
- 在线终端统计
- 系统健康度
- 房间卡片总览
- 快捷联控
- 能耗信息
- 运行日志
- 天气与时间显示

业务来源：

- `GET /api/netcafe/panel/overview`
- `GET /api/netcafe/panel/license/status`
- `GET /api/netcafe/weather`

## 15.2 包厢管理 `room`

功能包括：

- 按房间展示状态
- 展示电脑在线数、空调、灯光、新风状态
- 打开房间详情弹窗
- 在卡片内执行快捷动作
- 房间筛选

## 15.3 空调控制 `ac`

功能包括：

- 列出所有绑定空调的房间
- 查看温度、模式、风速
- 开关机
- 调温
- 切换 hvac mode
- 切换 fan mode
- 应用季节模式

## 15.4 灯光管理 `light`

功能包括：

- 列出所有绑定灯光的房间
- 单灯开关
- 调亮度
- 调色温
- 调颜色
- 执行灯光预设

## 15.5 环境控制 `fan`

功能包括：

- 列出所有绑定新风的房间
- 开关机
- 调档位
- 调风量百分比

## 15.6 系统设置 `settings`

功能包括：

- 全局设置
  - 品牌
  - 主题
  - 全局实体识别关键词
  - 全局自动化默认规则
  - 全局季节参数
  - 分机白名单

- 房间设置
  - 当前房间设备自动识别结果
  - 房间实体过滤词
  - 房间自动化规则
  - 房间空调季节模式
  - 房间分机权限

- 账户设置
  - 当前登录状态

- HA 设置 / 关于 / 诊断
  - 查看系统摘要
  - 下载诊断日志
  - 查看房间识别、缓存、运行日志

---

## 16. 前端实际依赖的核心接口

## 页面与静态资源

- `/api/netcafe/1.html`
- `/api/netcafe/1.js`
- `/api/netcafe/1.css`

## 鉴权

- `POST /api/netcafe/panel/auth/login`
- `POST /api/netcafe/panel/auth/register`
- `GET /api/netcafe/panel/auth/session`

## 卡密

- `GET /api/netcafe/panel/license/status`
- `POST /api/netcafe/panel/license/activate`

## 总览 / 配置 / 诊断

- `GET /api/netcafe/panel/overview`
- `GET /api/netcafe/panel/config/system`
- `POST /api/netcafe/panel/config/system`
- `GET /api/netcafe/panel/entities`
- `GET /api/netcafe/panel/diagnostics`
- `GET /api/netcafe/panel/history`

## 房间动作

- `POST /api/netcafe/panel/room/action`

## 原始服务代理

- `POST /api/netcafe/panel/service/{domain}/{service}`

## 天气

- `GET /api/netcafe/weather`
- `GET /api/netcafe/panel/weather/config`
- `POST /api/netcafe/panel/weather/config`
- `POST /api/netcafe/panel/weather/search`

## 分机

- `GET /api/netcafe/subcontrol/bootstrap`
- `GET /api/netcafe/subcontrol/mapping`
- `POST /api/netcafe/subcontrol/action`
- `GET /api/netcafe/subcontrol/license/status`
- `POST /api/netcafe/subcontrol/license/activate`

---

## 17. 存储实现逻辑

`StorageManager` 在 HA 配置目录下维护：

- `netcafe_data/{entry_id}_import.csv`
- `netcafe_data/{entry_id}_rooms.json`
- `netcafe_data/{entry_id}_config.json`

作用分别是：

- CSV 原始导入文件
- 房间解析结果缓存
- 前端保存的系统配置

配置保存的关键原则：

1. 配置项按 `entry_id` 分隔
2. 前端统一写入标准化后的 `config`
3. 运行时改动不会直接替代持久配置，除非显式 `persist`

---

## 18. 复刻时必须保留的关键业务约束

如果你要完整复刻，下面这些不能丢：

1. **CSV 是源头**
   - 不是房间表、不是数据库，而是 `IP -> room_name`

2. **房间占用有回退逻辑**
   - 优先按 trigger mode 匹配实体
   - 匹配不到再回退到电脑在线数

3. **房间设备绑定必须支持“自动识别 + 手动覆盖”**

4. **自动化必须基于“状态变化”触发，而不是每轮扫描直接执行**

5. **手动控制空调后必须有覆盖期**

6. **前端动作不能直接暴露 HA 原始服务，必须走房间动作层**

7. **卡密无效时必须锁系统**

8. **分机必须只能控自己的房间，且要受权限限制**

9. **前端设置保存时要做默认值补齐和归一化**

10. **诊断能力必须保留**
   - 这是排查“为什么只识别到一个房间”“为什么设备没匹配上”的关键

---

## 19. 推荐复刻顺序

建议按这个顺序做：

1. 先复刻 CSV 导入和 `device_tracker` 生成
2. 再复刻房间记录与占用判断
3. 再复刻 `room_control` 的房间配置结构
4. 再复刻设备自动识别与手动绑定
5. 再复刻房间动作执行层
6. 再复刻占用变化驱动的自动化调度
7. 再复刻 `www/__init__.py` 的 API 层
8. 最后复刻 `1.html + 1.js` 的总控台
9. 卡密和分机权限建议尽早保留接口位，后补实现也行

---

## 20. 最短复刻定义

如果你只做最小可运行版，至少要有：

1. CSV 导入
2. 包厢 -> 电脑映射
3. 设备在线检测
4. 房间占用判断
5. 房间绑定空调 / 灯光 / 新风
6. 房间动作 API
7. 前端 6 个主页面容器
8. `reloadAll()` 数据拉取与渲染
9. 自动化联动

这样就能复刻出项目的业务骨架。

---

## 21. 结论

这个项目不是单纯的“智能家居控制台”，而是一个由以下几层叠起来的系统：

1. **IP 设备追踪层**
2. **房间抽象层**
3. **设备自动绑定层**
4. **占用驱动自动化层**
5. **总控台 / 分机控制层**
6. **卡密与远程账号层**

其中真正的核心不在 UI，而在：

- `room_control.py`
- `__init__.py`
- `www/__init__.py`
- `1.js`

如果复刻时优先还原这四层之间的关系，项目就能基本复原。
