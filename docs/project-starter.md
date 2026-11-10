# Project starter / 项目内试用

The small starter installs the six portable method Skills, four role templates and the working agreements in a fresh project. The full environment route in the root README also restores the complete user Skill set and pinned tool environment.

轻量入口适合先在一个项目试方法。它放入六个便携方法 Skills、四类角色和工作约定。需要完整用户技能与工具环境时，从首页的完整复现入口开始。

```powershell
python -B bootstrap.py --target ../my-workflow-project
python -B bootstrap.py --target ../my-workflow-project --apply
codex -C ../my-workflow-project
```

The preview lists 11 files. Apply creates a new directory and rejects an existing one. Model access and service connections use the reader's environment. Keep the toolbox checkout available for its separate harness commands.

预览会列出 11 个文件，执行时只创建新目录。模型与服务连接使用读者自己的环境。核心工具仍从工具箱仓库调用，具体入口见[工具说明](../config/tooling/README.md)。
