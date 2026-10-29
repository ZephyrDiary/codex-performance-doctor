# Git Checks / Git 检查

仅检查授权工作区。枚举隐藏 `.git` 目录和文件；不要跟随符号链接、junction 或 reparse point，不递归进入 Git 对象目录，也不要自动跳过可能包含嵌套仓库的项目目录。权限错误应记录为未覆盖区域。 / Enumerate hidden `.git` directories and files in the authorized workspace without following links or recursing into Git internals. Report inaccessible areas as coverage gaps.

## Metadata / 元数据

- 对 `.git` 目录检查 `HEAD`、`config`、`objects`、`refs`；缺项是线索，不是可删除证明。 / Check these entries, but missing files alone do not authorize disposal.
- `.git` 文件可能是合法 worktree 或 submodule 的 `gitdir:` 指针；相对路径以该文件所在目录解析。 / Resolve Git pointer files relative to their parent directory.
- 先解析 `.git` 指针及 `commondir`，只读取授权范围内的元数据。若目标或链接位于范围外，先报告路径并征得授权，再执行 Git 命令。 / First resolve pointer and common-directory paths without reading outside the authorized scope. Obtain consent before running Git against external targets.
- 再运行下列只读定位命令。将 Git 解析的目录与该候选 `.git` 对比，防止自动向上找到父仓库而误判成功。 / Then compare resolved Git directories with the candidate to avoid accidentally recognizing an ancestor repository.

```text
git --no-optional-locks -C "<project>" rev-parse --absolute-git-dir
git --no-optional-locks -C "<project>" rev-parse --git-common-dir
git --no-optional-locks -C "<project>" rev-parse --is-inside-work-tree
```

对解析出的 Git/common/object 目录再次做路径范围校验；检查 `objects/info/alternates` 和会改变 Git 路径的环境变量，外部对象库也需先授权。全部相关路径均已获准后，才运行对象计数及递归大小扫描： / Recheck resolved Git/common/object paths, including alternates and Git path environment overrides. Only count objects or recurse after all relevant paths are authorized:

```text
git --no-optional-locks -C "<project>" count-objects -v
```

不要用 `safe.directory=*` 绕过安全检查。 / Do not bypass ownership checks.

## Size And Temporary Objects / 大小和临时对象

统计各 `.git` 或已授权 common directory 的总字节、文件数、`tmp_pack_*` 与 `tmp_obj_*` 数量、字节和最早/最新修改时间。共享目录只计一次，扫描遇到链接不跟随。对规模过大的扫描设时间上限并报告不完整结果。 / Measure bytes, files and temporary-object counts/ages; deduplicate shared directories and bound expensive scans.

巨大的 pack 文件可能正常；临时文件可能来自正在进行的 clone/fetch/repack。可短间隔复查大小/数量并检查相关 Git 进程，但不结束进程。 / Large packs may be legitimate and temporary objects may belong to active operations; observe changes and relevant processes without stopping them.

`rev-parse` 成功只验证基本可识别性，不是对象完整性证明。确需完整性检查时说明成本并征得同意后运行 `git fsck --full`，不要加 `--lost-found`。不要默认运行 `gc`、`prune` 或 repack。 / Basic recognition is not full object integrity. Obtain consent for expensive `fsck --full`; never use `--lost-found` or run cleanup implicitly.

只有再次确认目录确实为空、不是指针/共享仓库且用户授权移动后，才可将异常空 `.git` 移至同一工作区内唯一命名的隔离目录；验证源路径、目标路径及移动结果，记录恢复位置。非空元数据不自动处理，任何删除均需另行同意。 / Quarantine only a rechecked empty, nonshared directory with explicit move consent and verified paths; never automatically remove nonempty metadata.
