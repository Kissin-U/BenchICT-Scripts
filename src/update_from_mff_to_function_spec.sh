#!/bin/bash

# 配置信息，便于修改
# 设置日志文件
LOG_FILE="/mnt/data/BenchICT_Scripts/log"

# 设置本地仓库路径和分支名 
# 本工具使用绝对路径！
MFF_REPO="/mnt/data/mff"
MFF_BRANCH="BYUNS/rc/main"
FUNCTION_SPEC_REPO="/mnt/data/function_spec"
FUNCTION_SPEC_BRANCH="mff_hmi_main_check"

# 设置源路径和目标路径
SOURCE_PATH="$MFF_REPO/hmi_function_test/adaptor/aion_a02"
DEST_PATH="$FUNCTION_SPEC_REPO/BYUNS"

# 记录日志的函数
log() {
    local message="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $message" >> "$LOG_FILE"
}

# 更新仓库的函数
update_repository() {
    local repo_path="$1"
    local branch_name="$2"

    cd "$repo_path" || {
        log "Error: Failed to change directory to $repo_path"
        exit 1
    }

    if ! git rev-parse --verify "$branch_name" &>/dev/null; then
        log "Error: The branch $branch_name does not exist in the repository at $repo_path"
        exit 1
    fi

    if ! git checkout "$branch_name"; then
        log "Error: Failed to checkout branch $branch_name in the repository at $repo_path"
        exit 1
    fi

    if ! git pull; then
        log "Error: Failed to pull latest changes from branch $branch_name in the repository at $repo_path"
        exit 1
    fi

    log "The repository at $repo_path has been updated (Branch: $branch_name)"
}

# 显示将要操作的分支并请求确认
echo "The following branches will be operated on:"
echo "mff repository: $MFF_BRANCH"
echo "function_spec repository: $FUNCTION_SPEC_BRANCH"
read -p "Are these branches correct? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "User canceled the operation because the branches are incorrect"
    exit 1
fi

# 检查仓库是否存在
if [ ! -d "$MFF_REPO" ]; then
    log "Error: The mff repository path does not exist: $MFF_REPO"
    exit 1
fi

if [ ! -d "$FUNCTION_SPEC_REPO" ]; then
    log "Error: The function_spec repository path does not exist: $FUNCTION_SPEC_REPO"
    exit 1
fi

# 检查是否为有效的 git 仓库
if [ ! -d "$MFF_REPO/.git" ]; then
    log "Error: $MFF_REPO is not a valid git repository"
    exit 1
fi

if [ ! -d "$FUNCTION_SPEC_REPO/.git" ]; then
    log "Error: $FUNCTION_SPEC_REPO is not a valid git repository"
    exit 1
fi

# 确保目标文件夹存在
mkdir -p "$DEST_PATH"

# 更新 mff 仓库
update_repository "$MFF_REPO" "$MFF_BRANCH"

# 更新 function_spec 仓库
update_repository "$FUNCTION_SPEC_REPO" "$FUNCTION_SPEC_BRANCH"

# 显示将要同步的路径并请求确认
echo "Files will be synchronized from $SOURCE_PATH to $DEST_PATH"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "User canceled the synchronization operation"
    exit 1
fi

# 同步文件
log "Starting to synchronize files..."
if ! rsync -av --delete "$SOURCE_PATH/" "$DEST_PATH/"; then
    log "Error: Failed to synchronize files from $SOURCE_PATH to $DEST_PATH"
    exit 1
fi
log "File synchronization completed"

# 提交更改到 function_spec 仓库
cd "$FUNCTION_SPEC_REPO" || {
    log "Error: Failed to change directory to $FUNCTION_SPEC_REPO"
    exit 1
}

# 获取目标路径的最后一级目录名
DEST_FOLDER=$(basename "$DEST_PATH")
git add "$DEST_PATH"

if git diff --cached --quiet; then
    log "No changes to commit in the function_spec repository"
else
    if ! git commit -m "Synchronized from the mff repository ($MFF_BRANCH) to $DEST_FOLDER $(date +%Y-%m-%d)"; then
        log "Error: Failed to commit changes in the function_spec repository"
        exit 1
    fi
fi

# 再次确认 push 操作
echo "About to push the changes to the $FUNCTION_SPEC_BRANCH branch of the function_spec repository"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "User canceled the push operation"
    exit 1
fi

if ! git push origin "$FUNCTION_SPEC_BRANCH"; then
    log "Error: Failed to push changes to the $FUNCTION_SPEC_BRANCH branch of the function_spec repository"
    exit 1
fi

log "Changes have been committed and pushed to the $DEST_FOLDER folder of the function_spec repository (Branch: $FUNCTION_SPEC_BRANCH)"
log "Test synchronization operation completed"