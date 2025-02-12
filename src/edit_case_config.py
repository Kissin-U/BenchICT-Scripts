import json
import os
import logging
from datetime import datetime

class JsonModifier:
    def __init__(self, config_path='../config/test_case_template.json'):
        # 获取脚本所在的目录
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        # 获取 BenchICT_Scripts 目录
        self.bench_ict_dir = os.path.dirname(self.script_dir)
        
        # 构造配置文件的完整路径
        full_config_path = os.path.normpath(os.path.join(self.script_dir, config_path))
        
        # 检查配置文件是否存在
        if not os.path.exists(full_config_path):
            raise FileNotFoundError(f"Configuration file not found: {full_config_path}")
        
        # 从配置文件加载路径
        with open(full_config_path, 'r') as config_file:
            self.config = json.load(config_file)
        
        self.paths = self.config['paths']
        
        # 调整所有路径
        for key, path in self.paths.items():
            if path.startswith('../'):
                # 对于以 '../' 开头的路径，从 BenchICT_Scripts 的父目录开始
                self.paths[key] = os.path.normpath(os.path.join(os.path.dirname(self.bench_ict_dir), path[3:]))
            elif path.startswith('./'):
                # 对于以 './' 开头的路径，从 BenchICT_Scripts 目录开始
                self.paths[key] = os.path.normpath(os.path.join(self.bench_ict_dir, path[2:]))
            else:
                # 对于其他路径，假设它们是相对于 BenchICT_Scripts 目录的
                self.paths[key] = os.path.normpath(os.path.join(self.bench_ict_dir, path))
        
        self.TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._setup_logging()

    def _setup_logging(self):
        os.makedirs(self.paths['LOG_DIR'], exist_ok=True)
        log_file = os.path.join(self.paths['LOG_DIR'], f"json_modification_{self.TIMESTAMP}.log")
        logging.basicConfig(filename=log_file, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info(f"Log file created at: {log_file}")

    @staticmethod
    def check_duplicates(case, topic_type, topics):
        existing_input_topics = case["config"]["function_simulator"]["input_topic_list"]
        existing_output_topics = case["config"]["function_simulator"]["output_topic_list"]
        existing_topics = existing_input_topics if topic_type == "input" else existing_output_topics
        other_topics = existing_output_topics if topic_type == "input" else existing_input_topics
        duplicates = []
        for topic in topics:
            if topic in existing_topics:
                duplicates.append((topic, f"{topic_type} 列表内重复"))
            elif topic in other_topics:
                duplicates.append((topic, f"与 { 'output' if topic_type == 'input' else 'input' } 列表重复"))
        return duplicates

    def modify_topic_lists(self, json_data, case_codes, action, topic_type, topics):
        if case_codes == ['all']:
            case_codes = [case["case_code"] for case in json_data["test_suite_info"]["test_case_infos"]]

        for case in json_data["test_suite_info"]["test_case_infos"]:
            if case["case_code"] in case_codes:
                if action == 'add':
                    duplicates = self.check_duplicates(case, topic_type, topics)
                    if duplicates:
                        logging.warning(f"测试用例 {case['case_code']} 存在重复Topic:")
                        for topic, reason in duplicates:
                            logging.warning(f"  - Topic {topic}: {reason}")
                        logging.warning("请先解决重复问题再进行添加操作。")
                        continue
                topic_list = case["config"]["function_simulator"][f"{topic_type}_topic_list"]
                original_list = topic_list.copy()
                if action == 'add':
                    for topic in topics:
                        if topic not in topic_list:
                            topic_list.append(topic)
                elif action == 'remove':
                    for topic in topics:
                        if topic in topic_list:
                            topic_list.remove(topic)
                # 记录日志
                logging.info(f"测试用例: {case['case_code']}, 操作: {action}, Topic列表类型: {topic_type}, "
                             f"修改内容: {topics}, 原始内容: {original_list}")

        return json_data

    def run(self):
        # 获取 JSON 文件路径
        while True:
            file_path = input("请输入 JSON 文件的绝对路径：")
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                break
            except FileNotFoundError:
                logging.error(f"未找到文件: {file_path}，请重新输入。")
            except json.JSONDecodeError:
                logging.error(f"无法解析 JSON 文件: {file_path}，请重新输入。")

        while True:
            # 获取要修改的测试用例代码
            case_codes_input = input("请输入要修改的测试用例代码（多个代码用逗号分隔，输入 'all' 表示所有测试用例）：")
            case_codes = [code.strip() for code in case_codes_input.split(',')]

            # 获取操作类型
            while True:
                action = input("请输入操作类型（add 表示添加，remove 表示移除）：").strip().lower()
                if action not in ['add', 'remove']:
                    logging.warning("无效的操作类型，请输入 'add' 或 'remove'。")
                else:
                    break

            # 获取Topic列表类型
            while True:
                topic_type = input("请输入Topic列表类型（input 表示 input_topic_list，output 表示 output_topic_list）：").strip().lower()
                if topic_type not in ['input', 'output']:
                    logging.warning("无效的Topic列表类型，请输入 'input' 或 'output'。")
                else:
                    break

            # 获取要操作的Topic列表
            print("提示：输入Topic时无需带引号。")
            topics_input = input("请输入要操作的Topic列表（多个Topic用逗号分隔）：")
            topics = [topic.strip().strip('"') for topic in topics_input.split(',')]

            # 执行修改操作
            data = self.modify_topic_lists(data, case_codes, action, topic_type, topics)

            # 询问是否继续
            continue_choice = input("是否继续修改？(y/n)：").strip().lower()
            if continue_choice != 'y':
                break

        # 将修改后的数据写回文件
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            logging.info("JSON 文件已成功修改并保存。")
        except Exception as e:
            logging.error(f"保存文件时出错: {e}")

if __name__ == "__main__":
    try:
        modifier = JsonModifier()
        modifier.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please make sure the configuration file exists and is accessible.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")