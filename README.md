# 智慧网吧

这是一个用于 Home Assistant 的网吧自动化自定义集成仓库，当前集成域名为 `netcafe_automation`。

## 仓库结构

```text
custom_components/netcafe_automation
```

HACS 和手动安装都应使用这个集成目录。

## 安装

### HACS 自定义仓库

1. 打开 HACS
2. 进入“集成”
3. 右上角选择“自定义仓库”
4. 添加仓库：

```text
https://github.com/yx33948/wangba
```

5. 类型选择 `Integration`
6. 搜索并安装“智慧网吧”
7. 重启 Home Assistant

### 手动安装

将 `custom_components/netcafe_automation` 复制到：

```text
config/custom_components/netcafe_automation
```

然后重启 Home Assistant。

## 配置方式

安装后到 Home Assistant：

```text
设置 -> 设备与服务 -> 添加集成 -> 智慧网吧
```

支持：

- 手动添加包厢设备
- CSV 批量导入
- 卡密激活与管理
- 天气位置配置

## 相关链接

- 文档：[https://github.com/yx33948/wangba](https://github.com/yx33948/wangba)
- 问题反馈：[https://github.com/yx33948/wangba/issues](https://github.com/yx33948/wangba/issues)

