# AI 工作入口

- 修改 Home shim 源码时，先读根目录 `README.md` 的原项目说明。
- 用户要求恢复电视桌面、切换备份、调整猫咪壁纸或排版时，先读
  `devices/skyworth-9s61-g650/README.md`，按其中流程核对设备、选择备份、校验和保存现状，再实施恢复。
- 备份索引以该目录的 `backups.json` 为准；当前推荐项是 `rotation-short-label`。
- 这些是特定电视的桌面备份。恢复范围不包括整机固件、应用账号、影视仓配置或此前精简的系统组件。
- ZIP 放在该索引指向的 Releases 附件中。Git 内维护索引、配置、源码补丁和校验工具。
- 本仓库的 shim 与备份中的 launcher 是两个 APK。保留这两个项目的包名、来源和恢复范围区别。
- 运行恢复相关检查：`python3 -m unittest discover -s tests -v`。
