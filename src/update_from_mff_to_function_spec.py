import os
import sys
import json
import subprocess
from datetime import datetime
import logging

# 配置信息
MFF_REPO = "/mnt/data/mff"
MFF_BRANCH = "BYUNS/rc/main"
FUNCTION_SPEC_REPO = "/mnt/data/function_spec"
FUNCTION_SPEC_BRANCH = "mff_hmi_main_check"
SOURCE_PATH = os.path.join(MFF_REPO, "hmi_function_test/adaptor/aion_a02")
DEST_PATH = os.path.join(FUNCTION_SPEC_REPO, "BYUNS")

class RepoSynchronizer:
    def __init__(self, config_path='../config/test_case_template.json'):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.bench_ict_dir = os.path.dirname(self.script_dir)
        self.parent_dir = os.path.dirname(self.bench_ict_dir)
        
        full_config_path = os.path.normpath(os.path.join(self.script_dir, config_path))
        
        if not os.path.exists(full_config_path):
            raise FileNotFoundError(f"Configuration file not found: {full_config_path}")
        
        with open(full_config_path, 'r') as config_file:
            self.config = json.load(config_file)
        
        self.paths = self.config['paths']
        
        for key, path in self.paths.items():
            if path.startswith('../'):
                self.paths[key] = os.path.normpath(os.path.join(self.parent_dir, path[3:]))
            elif path.startswith('./'):
                self.paths[key] = os.path.normpath(os.path.join(self.bench_ict_dir, path[2:]))
            else:
                self.paths[key] = os.path.normpath(os.path.join(self.bench_ict_dir, path))

        self.TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.LOG_FILE = os.path.join(self.paths['LOG_DIR'], f"RepoSync_{self.TIMESTAMP}.log")
        
        self.setup_logging()

        # 使用全局配置
        self.MFF_REPO = MFF_REPO
        self.MFF_BRANCH = MFF_BRANCH
        self.FUNCTION_SPEC_REPO = FUNCTION_SPEC_REPO
        self.FUNCTION_SPEC_BRANCH = FUNCTION_SPEC_BRANCH
        self.SOURCE_PATH = SOURCE_PATH
        self.DEST_PATH = DEST_PATH

    def setup_logging(self):
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)
        logging.basicConfig(filename=self.LOG_FILE, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        logging.getLogger('').addHandler(console)

    def log(self, message):
        logging.info(message)

    def run_command(self, command, cwd=None):
        try:
            process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command, stdout, stderr)
            return stdout.strip()
        except subprocess.CalledProcessError as e:
            self.log(f"Error executing command: {e}")
            self.log(f"Error output: {e.stderr}")
            raise

    def update_repository(self, repo_path, branch_name):
        self.log(f"Updating repository: {repo_path}, branch: {branch_name}")
        self.run_command(['git', 'checkout', branch_name], repo_path)
        self.run_command(['git', 'pull'], repo_path)

    def synchronize_files(self):
        self.log("Starting to synchronize files...")
        self.run_command(['rsync', '-av', '--delete', f"{self.SOURCE_PATH}/", self.DEST_PATH])
        self.log("File synchronization completed")

    def commit_changes(self):
        self.log("Committing changes...")
        dest_folder = os.path.basename(self.DEST_PATH)
        self.run_command(['git', 'add', self.DEST_PATH], self.FUNCTION_SPEC_REPO)
        try:
            self.run_command(['git', 'diff', '--cached', '--quiet'], self.FUNCTION_SPEC_REPO)
            self.log("No changes to commit in the function_spec repository")
        except subprocess.CalledProcessError:
            commit_message = f"Synchronized from the mff repository ({self.MFF_BRANCH}) to {dest_folder} {datetime.now().strftime('%Y-%m-%d')}"
            self.run_command(['git', 'commit', '-m', commit_message], self.FUNCTION_SPEC_REPO)

    def push_changes(self):
        self.log(f"Pushing changes to {self.FUNCTION_SPEC_BRANCH}...")
        self.run_command(['git', 'push', 'origin', self.FUNCTION_SPEC_BRANCH], self.FUNCTION_SPEC_REPO)

    def process(self):
        try:
            self.log("Script execution started")

            # 显示将要操作的分支并请求确认
            print(f"The following branches will be operated on:")
            print(f"mff repository: {self.MFF_BRANCH}")
            print(f"function_spec repository: {self.FUNCTION_SPEC_BRANCH}")
            if not self.get_user_confirmation("Are these branches correct?"):
                self.log("User canceled the operation because the branches are incorrect")
                return

            # 检查仓库是否存在
            for repo in [self.MFF_REPO, self.FUNCTION_SPEC_REPO]:
                if not os.path.exists(repo):
                    self.log(f"Error: The repository path does not exist: {repo}")
                    return
                if not os.path.exists(os.path.join(repo, '.git')):
                    self.log(f"Error: {repo} is not a valid git repository")
                    return

            # 确保目标文件夹存在
            os.makedirs(self.DEST_PATH, exist_ok=True)

            # 更新仓库
            self.update_repository(self.MFF_REPO, self.MFF_BRANCH)
            self.update_repository(self.FUNCTION_SPEC_REPO, self.FUNCTION_SPEC_BRANCH)

            # 显示将要同步的路径并请求确认
            print(f"Files will be synchronized from {self.SOURCE_PATH} to {self.DEST_PATH}")
            if not self.get_user_confirmation("Continue?"):
                self.log("User canceled the synchronization operation")
                return

            # 同步文件
            self.synchronize_files()

            # 提交更改
            self.commit_changes()

            # 再次确认 push 操作
            print(f"About to push the changes to the {self.FUNCTION_SPEC_BRANCH} branch of the function_spec repository")
            if not self.get_user_confirmation("Continue?"):
                self.log("User canceled the push operation")
                return

            # 推送更改
            self.push_changes()

            self.log(f"Changes have been committed and pushed to the {os.path.basename(self.DEST_PATH)} folder of the function_spec repository (Branch: {self.FUNCTION_SPEC_BRANCH})")
            self.log("Synchronization operation completed")

        except Exception as e:
            self.log(f"An error occurred: {str(e)}")
        finally:
            self.log("Script execution completed")

    def get_user_confirmation(self, prompt):
        while True:
            response = input(f"{prompt} (y/n): ").lower()
            if response in ['y', 'n']:
                return response == 'y'
            print("Please enter 'y' or 'n'.")

if __name__ == "__main__":
    try:
        synchronizer = RepoSynchronizer()
        synchronizer.process()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)