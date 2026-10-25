# 9S61_G650 桌面备份与恢复

## 先确认恢复范围

本目录对应已完成 Home 接管和优化的创维／酷开 **9S61_G650，Android 8.0.0 / SDK 26**。
这四份备份恢复 `com.coocaa.tvhome` 桌面 APK、外部布局配置和猫咪壁纸。
它们没有包含整机固件、分区、系统精简清单、系统设置、ADB 密钥、桌面私有偏好、应用账号或影视仓数据。
恢复后应用图标仍取决于电视上实际安装的应用，不能凭这些 ZIP 重新完成整机优化。

仓库本身构建的是 Home shim（`com.ccos.tv.homepage`），ZIP 内 `launcher.apk` 来自另一个项目
[Clean Your TV](https://github.com/Gathin23/cleanyourtv)，不是本仓库构建输出。
恢复已优化电视的桌面时，沿用现有 shim；不要顺手执行根 README 的初装或卸载 Home 接管步骤。

## 选择备份

| ID | 原始备份时间（北京时间） | 内容 |
|---|---|---|
| `glass` | 2026-10-25 09:41 | 单张亲昵猫咪图、通透玻璃、原始细字体 |
| `readable` | 2026-10-25 10:07 | 单张图；时间60sp、日期20sp、应用标题26sp；清晰无衬线和轻阴影 |
| `rotation` | 2026-10-25 10:14 | 清晰字版；三图按顺序、约15分钟一张 |
| **`rotation-short-label`** | **2026-10-25 10:20** | **当前推荐：三图轮换，影视仓V3显示为“影视仓”** |

四个 ZIP 原始内容和字节未改写，Release 附件使用 ASCII 文件名，原中文文件名记录在
[`backups.json`](backups.json)。ZIP 放 [Releases](https://github.com/Jsu-4/coocaa-home-shim/releases/tag/tv-backups-2026-10-25)，
配置放 [`configs/`](configs/)，整包哈希见 [`SHA256SUMS`](SHA256SUMS)。
GitHub 官方建议用 [Releases 分发二进制文件](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)，
这样仓库克隆不必携带多份重复图片和安装包，AI 仍能读取完整索引和配置。

“玻璃模式”有固定半透明材质，会覆盖普通底栏的 `dock_opacity`；配置的30不能解释成玻璃本身30%不透明。
壁纸轮换由电视本地桌面处理，只在首页可见时更新；其他应用中到期，返回首页时更新，电脑无需保持在线。
图片不移动，三图切换间隔不是视频播放或屏保间隔。

## AI 恢复流程

### 1. 选择、下载并校验

除用户明确选择其他 ID，沿用 `recommended_profile`。Python 3.9+，仅使用标准库：

```bash
python3 tools/tv_backup.py list
python3 tools/tv_backup.py prepare rotation-short-label
```

默认下载到忽略的 `.local/tv-backups/`，校验整包 SHA-256、所有成员和文件清单后，解压为一个新目录。
已下载 ZIP 可以离线校验：

```bash
python3 tools/tv_backup.py verify rotation-short-label --archive /path/to/backup.zip
python3 tools/tv_backup.py prepare rotation-short-label --archive /path/to/backup.zip
```

工具只准备本地文件，不连接或修改电视。哈希以 Git 中索引为准，而不是仅信任 ZIP 内自己携带的清单。
校验失败时停止恢复；不要重新计算一个哈希替换索引来让失败通过。

### 2. 确认目标电视和当前安装

从用户当前网络或电视设置取得地址，不假设历史 IP 仍有效。
以下变量只是操作示例；将 `SERIAL` 替换为实际 `adb devices -l` 显示的设备标识，
将 `INCOMING` 替换为 prepare 命令打印的目录。

```bash
SERIAL='<电视IP>:5555'
INCOMING='/path/printed/by/prepare'
adb connect "$SERIAL"
adb -s "$SERIAL" get-state
adb -s "$SERIAL" shell getprop ro.product.manufacturer
adb -s "$SERIAL" shell getprop ro.product.model
adb -s "$SERIAL" shell getprop ro.build.version.release
adb -s "$SERIAL" shell getprop ro.build.version.sdk
adb -s "$SERIAL" shell pm path com.coocaa.tvhome
```

完成标准：设备已授权，型号 `9S61_G650`、SDK `26`，已有可用的 `com.coocaa.tvhome`。
型号不符、连接未授权、桌面缺失时，先调查实际状态，不套用此设备的初装和恢复命令。
若电脑既有 ADB 服务无法连接但网络正常，可为本次会话使用单独服务端口；所有命令一致添加 `-P <端口>`。

### 3. 保存恢复前状态

在安装和替换文件前，创建唯一的本地快照目录，并保存当前 APK 路径与文件：

```bash
STAMP=$(date +%Y%m%d-%H%M%S)
SNAPSHOT=".local/tv-snapshots/$STAMP"
REMOTE='/sdcard/Android/data/com.coocaa.tvhome/files'
mkdir -p "$SNAPSHOT"
adb -s "$SERIAL" shell pm path com.coocaa.tvhome
# 将上一步实际返回的 package: 后路径填入下一条；存在多个 split APK 时停止这套单 APK 流程。
adb -s "$SERIAL" pull '<当前安装APK的绝对路径>' "$SNAPSHOT/launcher-before.apk"
adb -s "$SERIAL" pull "$REMOTE" "$SNAPSHOT/files-before"
adb -s "$SERIAL" shell settings get secure enabled_accessibility_services > "$SNAPSHOT/accessibility-services.txt"
adb -s "$SERIAL" shell settings get secure accessibility_enabled > "$SNAPSHOT/accessibility-enabled.txt"
adb -s "$SERIAL" exec-out screencap -p > "$SNAPSHOT/before.png"
```

完成标准：APK和现有外部目录均成功取回，配置可读，记录了哪些键辅助服务原本启用。
这些是本地私人快照，不上传仓库。安装和 force-stop 可能让桌面自身的键辅助服务停用；
如原本启用了此类服务，按实际前后状态恢复，保留其他应用的辅助服务。

### 4. 保留数据更新桌面，再替换整套布局

先用 Android SDK 的 `apksigner verify --print-certs` 检查准备好的和当前 APK。
备份证书 SHA-256 见 `backups.json`，应为 `ad494274898bc92275455e4b8ffd8d28d86e39ef1384d4cf43fbf402155c2175`。
当前包证书不同则停止，保留当前安装；不要卸载来绕过签名问题。

```bash
adb -s "$SERIAL" install -r "$INCOMING/launcher.apk"
```

**只有返回 `Success` 才执行后续命令。** 安装失败时保留旧包，先解决具体错误。
四份 APK 都是版本2.7 / versionCode 8；未来若版本更高导致拒绝降级，先判断兼容性，不擅自加 `-d`。

保留整套旧目录，再放入本次完整布局，避免单张备份混入上次三图集合：

```bash
PARKED="/sdcard/Android/data/com.coocaa.tvhome/files-before-$STAMP"
adb -s "$SERIAL" shell am force-stop com.coocaa.tvhome
# 确认 PARKED 不存在后再执行 mv；同名目录已存在时换一个唯一 STAMP。
adb -s "$SERIAL" shell ls -ld "$PARKED"
adb -s "$SERIAL" shell mv "$REMOTE" "$PARKED"
adb -s "$SERIAL" shell mkdir -p "$REMOTE"
adb -s "$SERIAL" push "$INCOMING/layout/." "$REMOTE/"
adb -s "$SERIAL" shell am start -W -n com.coocaa.tvhome/com.gathin.tvhome.MainActivity
```

任何一步失败都停止顺序执行，按下一节回滚。新配置的修改时间会触发桌面主题重新加载。
不要直接把新单张配置盖到保留 `wallpapers/` 的目录中，否则仍可能显示旧集合。

### 5. 验证，必要时回滚

恢复完成至少确认：

1. `am start -W` 返回 `Status: ok`，前台是 `com.coocaa.tvhome/com.gathin.tvhome.MainActivity`。
2. 将电视端配置取回，与索引对应 `configs/<ID>.json` 比较；对壁纸文件做 SHA-256 校验。
3. 实机截图检查时间、日期、玻璃底栏、壁纸及应用显示名称；四方向导航正常。
4. 从设置返回首页，必要时请用户按一次物理 Home；注入按键不证明真实遥控器接管正常。
5. 三图轮换曾以1分钟测试间隔确认显示和切换，最终15分钟已回读确认；没有等待完整45分钟循环。
   需要重新验证计时时，可短暂改1分钟测试，结束后恢复15分钟并回读。

失败时先保留失败现场目录，然后保留数据安装本地 `launcher-before.apk`；安装成功后停止桌面，
将新 `files/` 移到另一个唯一的 `files-failed-*` 名称，把 `PARKED` 移回 `files/` 并重新启动旧桌面。
如果保留数据安装被拒绝，停止并说明错误，不做卸载、清数据、刷机、root 或批量系统包操作。
检查原有键辅助服务状态，恢复确实受此次操作影响的部分。

## 源码来源与复现

备份桌面来自 `Gathin23/cleanyourtv` 的提交 `eb0131a32fd8567086f39002f1782f7c1b078ca6`。
`glass` 使用该版本的原始布局；其他三份使用 [`patches/readable-typography.patch`](patches/readable-typography.patch)。
按该源项目要求使用 JDK17、Android SDK34，在源项目根目录应用补丁，然后到 `launcher/` 构建：

```bash
git apply /path/to/readable-typography.patch
cd launcher
./gradlew -PlauncherApplicationId=com.coocaa.tvhome testReleaseUnitTest lintRelease assembleRelease
```

补丁与包名参数复现源码改动；原构建使用本机调试签名。私钥不在仓库或 ZIP 中，
重建 APK 在其他电脑上通常会得到不同证书，不能承诺可直接覆盖现有安装。
需要恢复原安装时优先使用校验通过的归档 APK。

上游 Home shim 和 Clean Your TV 采用 MIT 许可；AndroidX 等依赖沿用其各自许可。
猫咪图片由用户提供，随个人恢复包保存。此处未对其他人作额外的图片授权声明。
