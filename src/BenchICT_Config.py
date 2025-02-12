import json
import yaml
import os
from datetime import datetime
import logging
import copy
import sys

class CaseProcessor:
    def __init__(self, config_path='../config/test_case_template.json'):
        # 获取脚本所在的目录
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        # 获取 BenchICT_Scripts 目录
        self.bench_ict_dir = os.path.dirname(self.script_dir)
        # 获取 BenchICT_Scripts 的父目录
        self.parent_dir = os.path.dirname(self.bench_ict_dir)
        
        # 构造配置文件的完整路径
        full_config_path = os.path.normpath(os.path.join(self.script_dir, config_path))
        
        # 检查配置文件是否存在
        if not os.path.exists(full_config_path):
            raise FileNotFoundError(f"Configuration file not found: {full_config_path}")
        
        # 从配置文件加载路径和测试用例模板
        with open(full_config_path, 'r') as config_file:
            self.config = json.load(config_file)
        
        self.paths = self.config['paths']
        self.test_case_template = self.config['test_case_template']
        
        # 调整所有路径
        for key, path in self.paths.items():
            if path.startswith('../'):
                # 对于以 '../' 开头的路径，从 BenchICT_Scripts 的父目录开始
                self.paths[key] = os.path.normpath(os.path.join(self.parent_dir, path[3:]))
            elif path.startswith('./'):
                # 对于以 './' 开头的路径，从 BenchICT_Scripts 目录开始
                self.paths[key] = os.path.normpath(os.path.join(self.bench_ict_dir, path[2:]))
            else:
                # 对于其他路径，假设它们是相对于 BenchICT_Scripts 目录的
                self.paths[key] = os.path.normpath(os.path.join(self.bench_ict_dir, path))
        
        self.TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.OUTPUT_JSON = os.path.join(self.paths['OUTPUT_DIR'], f"generated_json_{self.TIMESTAMP}.json")
        self.LOG_FILE = os.path.join(self.paths['LOG_DIR'], f"BenchICT_Config_{self.TIMESTAMP}.txt")
        
        self._setup_logging()
        self._setup_output_dir()

    def _setup_logging(self):
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)
        logging.basicConfig(filename=self.LOG_FILE, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

    def _setup_output_dir(self):
        os.makedirs(os.path.dirname(self.OUTPUT_JSON), exist_ok=True)

    def load_bag_info(self):
        try:
            with open(self.paths['BAG_JSON_PATH'], 'r') as file:
                data = json.load(file)
                bag_md5s = data.get('bag_md5s', [])
                bag_info = {bag_md5s[i]: float(bag_md5s[i+1]) for i in range(0, len(bag_md5s), 2)}
                return bag_info
        except Exception as e:
            logging.error(f"Error reading bag.json: {str(e)}")
            raise

    def process_topic_list(self, topic_list_file):
        topics = []
        if os.path.exists(topic_list_file):
            with open(topic_list_file, 'r') as file:
                topics = [line.split()[1] for line in file if line.startswith('topic')]
        else:
            logging.warning(f"Warning: topic_list file {topic_list_file} does not exist.")
        return topics

    def process_extend_file(self, extend_file):
        output_topics, topic_remaps, forward_topics = [], [], []
        
        if os.path.exists(extend_file):
            with open(extend_file, 'r') as file:
                for line in file:
                    if line.startswith('send'):
                        output_topics.append(line.split()[1])
                    elif line.startswith('forward'):
                        topic = line.split()[1]
                        topic_remaps.append({"from": topic, "to": f"/mfl_fake{topic}"})
                        forward_topics.append(topic)
        else:
            logging.warning(f"Warning: extend file {extend_file} does not exist.")
        
        return {
            "output_topics": output_topics,
            "topic_remaps": topic_remaps,
            "forward_topics": forward_topics
        }

    def process_yaml(self, yaml_file, bag_info):
        case_code = os.path.splitext(os.path.basename(yaml_file))[0]
        logging.info(f"Processing file: {yaml_file}")
        logging.info(f"Case code: {case_code}")

        if not os.path.exists(yaml_file):
            logging.warning(f"Warning: {yaml_file} does not exist. Skipping.")
            return None

        with open(yaml_file, 'r') as file:
            yaml_data = yaml.safe_load(file)

        mfl_case_path = yaml_data.get('mfl_case_path')
        mfl_extend_path = yaml_data.get('mfl_extend_path')
        bag_md5 = yaml_data.get('bag_md5')
        play_topic_list = yaml_data.get('play_topic_list')

        if not all([mfl_case_path, mfl_extend_path, bag_md5, play_topic_list]):
            error_message = f"Error: Unable to extract required information from {yaml_file}."
            logging.error(error_message)
            raise ValueError(error_message)

        if bag_md5 not in bag_info:
            error_message = f"Error: bag_md5 {bag_md5} not found in bag.json. Unable to find trigger time for case {case_code}."
            logging.error(error_message)
            raise ValueError(error_message)

        trigger_time = bag_info[bag_md5]

        extend_file = os.path.join(self.paths['BASE_PATH'], mfl_extend_path)
        topic_list_file = os.path.join(self.paths['BASE_PATH'], play_topic_list)

        extend_info = self.process_extend_file(extend_file)
        input_topics = self.process_topic_list(topic_list_file)

        test_case_info = copy.deepcopy(self.test_case_template['test_suite_info']['test_case_infos'][0])
        test_case_info['case_code'] = case_code
        test_case_info['bag_urls'] = [bag_md5]
        test_case_info['config']['topic_remaps'] = extend_info['topic_remaps']
        test_case_info['config']['function_simulator']['input_topic_list'] = list(set(input_topics + extend_info["forward_topics"] + ["/simulator/load_mfl_case", "/clock", "/mla/egopose"]) - 
                                                                                  set(extend_info["output_topics"] + ["/simulator/result"]) |
                                                                                  set(["/simulator/load_mfl_case", "/clock"]))
        test_case_info['config']['function_simulator']['output_topic_list'] = list(set(extend_info["output_topics"] + ["/simulator/result"]))
        test_case_info['mfl_function_spec']['spec_names'][0]['path'] = f"cases/{mfl_case_path}" if not mfl_case_path.startswith("cases/") else mfl_case_path
        test_case_info['mfl_function_spec']['spec_names'][0]['extend_path'] = f"cases/{mfl_extend_path}" if not mfl_extend_path.startswith("cases/") else mfl_extend_path
        test_case_info['mfl_function_spec']['spec_names'][0]['trigger_time'] = trigger_time

        logging.info(f"Added information for {case_code} to output JSON")
        return test_case_info

    def process(self):
        try:
            logging.info("Script execution started")
            
            bag_info = self.load_bag_info()

            with open(self.paths['CASE_LIST_JSON'], 'r') as file:
                case_list = json.load(file)['case_list']

            output_json = copy.deepcopy(self.test_case_template)
            output_json['test_suite_info']['test_case_infos'] = []

            for yaml_file in case_list:
                full_yaml_path = os.path.join(self.paths['YAML_DIR'], yaml_file)
                test_case_info = self.process_yaml(full_yaml_path, bag_info)
                if test_case_info:
                    output_json['test_suite_info']['test_case_infos'].append(test_case_info)

            with open(self.OUTPUT_JSON, 'w') as outfile:
                json.dump(output_json, outfile, indent=2)

            logging.info(f"Generated JSON file saved to {self.OUTPUT_JSON}")
            logging.info(f"Log file saved to {self.LOG_FILE}")

        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            logging.error(f"Error type: {type(e).__name__}")
            logging.error(f"Error occurred in {e.__traceback__.tb_frame.f_code.co_filename}, line {e.__traceback__.tb_lineno}")
            sys.exit(1)  # 终止程序

        finally:
            logging.info("Script execution completed")

if __name__ == "__main__":
    try:
        processor = CaseProcessor()
        processor.process()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please make sure the configuration file exists and is accessible.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)