# 智慧网吧 `netcafe_automation`

适用于 Home Assistant 的自定义集成，用来管理网吧包厢设备、CSV 批量导入、授权卡密，以及前端控制页面。

## 主要功能

- 支持通过配置流程添加集成
- 支持手动录入包厢与 IP
- 支持 CSV 批量导入、导出、更新
- 提供卡密激活、延期、停用、状态查询
- 提供天气位置配置
- 包含 `www` 前端资源，可用于网吧控制界面

## 安装方式

### 方式一：HACS 自定义仓库

1. 打开 HACS
2. 进入“集成”
3. 右上角菜单选择“自定义仓库”
4. 仓库地址填写：

```text
https://github.com/yx33948/wangba
```

5. 类型选择 `Integration`
6. 安装后重启 Home Assistant

### 方式二：手动安装

将本目录复制到：

```text
config/custom_components/netcafe_automation
```

重启 Home Assistant 后，在“设置 -> 设备与服务”中添加“智慧网吧”。

## 首次配置

集成支持两种初始导入方式：

- 单个添加包厢与 IP
- 粘贴 CSV 内容批量导入

CSV 至少需要两列：

```csv
ip_address,room_name
192.168.1.101,1号包厢
192.168.1.102,2号包厢
```

配置过程中还可以：

- 激活卡密
- 配置天气位置

## 提供的服务

当前包含这些常用服务：

- `netcafe_automation.reload_from_csv`
- `netcafe_automation.export_csv`
- `netcafe_automation.import_csv_from_file`
- `netcafe_automation.import_csv_direct`
- `netcafe_automation.clear_all_data`
- `netcafe_automation.clear_all_device_trackers`
- `netcafe_automation.activate_license`
- `netcafe_automation.get_license_status`
- `netcafe_automation.deactivate_license`
- `netcafe_automation.renew_license`
- `netcafe_automation.create_trial_license`

## 目录说明

- `www/`：实际发布用的前端资源
- `www_dev/`：开发资源
- `www_release/`：发布构建产物
- `brand/`：品牌图标资源
- `translations/`：多语言文本

## 已知说明

- `www_dev/` 和 `www_release/` 目前也在仓库中，HACS 可以安装，但仓库体积会偏大
- 若后续只保留运行所需内容，建议优先保留 `www/`

