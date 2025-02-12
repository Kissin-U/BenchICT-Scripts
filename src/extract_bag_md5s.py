import json
import os
from datetime import datetime
import logging

class BagMD5Extractor:
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
        
        # 从配置文件加载路径
        with open(full_config_path, 'r') as config_file:
            self.config = json.load(config_file)
        
        self.paths = self.config['paths']
        
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
        
        # 设置 BAG_JSON_PATH 和 OUTPUT_JSON
        self.BAG_JSON_PATH = self.paths.get('BAG_JSON_PATH')
        if not self.BAG_JSON_PATH:
            logging.warning("BAG_JSON_PATH is not defined in the configuration file")
        
        self.TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.OUTPUT_JSON = os.path.join(self.paths['OUTPUT_DIR'], "bag.json")
        self.LOG_FILE = os.path.join(self.paths['LOG_DIR'], f"extract_bag_md5s_{self.TIMESTAMP}.txt")
        
        self._setup_logging()
        self._setup_output_dir()

    def _setup_logging(self):
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)
        logging.basicConfig(filename=self.LOG_FILE, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

    def _setup_output_dir(self):
        os.makedirs(os.path.dirname(self.OUTPUT_JSON), exist_ok=True)

    def process(self):
        try:
            logging.info("Script execution started")
            print("Script execution started")
            
            if not os.path.exists(self.paths['CASE_LIST_JSON']):
                raise FileNotFoundError(f"The {self.paths['CASE_LIST_JSON']} file does not exist.")

            # 读取现有的 bag.json 文件（如果存在）
            existing_bags = {}
            if self.BAG_JSON_PATH and os.path.exists(self.BAG_JSON_PATH):
                with open(self.BAG_JSON_PATH, 'r') as infile:
                    existing_data = json.load(infile)
                    for bag in existing_data.get('bags', []):
                        existing_bags[bag['md5']] = bag

            with open(self.paths['CASE_LIST_JSON'], 'r') as file:
                case_list = json.load(file)['case_list']

            new_bags = []
            logging.info("Starting to process YAML files:")
            print("Starting to process YAML files:")
            for yaml_file in case_list:
                full_path = os.path.join(self.paths['YAML_DIR'], yaml_file)
                logging.info(f"Processing file: {full_path}")
                if os.path.exists(full_path):
                    with open(full_path, 'r') as file:
                        for line in file:
                            if line.startswith('bag_md5:'):
                                md5 = line.split(':')[1].strip()
                                if md5 not in existing_bags:
                                    new_bag = {"md5": md5, "trigger_time": "None"}
                                    existing_bags[md5] = new_bag
                                    new_bags.append(new_bag)
                                    logging.info(f"Found new bag_md5: {md5}")
                                    print(f"Found new bag_md5: {md5}")
                                else:
                                    logging.info(f"Found existing bag_md5: {md5}")
                                break
                else:
                    logging.warning(f"Warning: The file {full_path} does not exist.")
                    print(f"Warning: The file {full_path} does not exist.")

            # 将字典转换回列表
            all_bags = list(existing_bags.values())

            # 检查是否找到任何md5值
            if not all_bags:
                logging.warning("Warning: No bag_md5 values were found.")
                print("Warning: No bag_md5 values were found.")
                output_json = {"bags": []}
            else:
                output_json = {"bags": all_bags}

            # 写入JSON文件
            with open(self.OUTPUT_JSON, 'w') as outfile:
                json.dump(output_json, outfile, indent=2)

            logging.info("Generated JSON content:")
            logging.info(json.dumps(output_json, indent=2))

            md5_count = len(all_bags)
            new_md5_count = len(new_bags)
            logging.info(f"Processing completed. The bag information has been saved to {self.OUTPUT_JSON}")
            logging.info(f"A total of {md5_count} bags were found, including {new_md5_count} new bags.")
            print(f"Processing completed. The bag information has been saved to {self.OUTPUT_JSON}")
            print(f"A total of {md5_count} bags were found, including {new_md5_count} new bags.")

        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            logging.error(f"Error type: {type(e).__name__}")
            logging.error(f"Error occurred in {e.__traceback__.tb_frame.f_code.co_filename}, line {e.__traceback__.tb_lineno}")
            print(f"An error occurred: {str(e)}")

        finally:
            logging.info("Script execution completed")
            logging.info(f"The generated JSON file has been saved to {self.OUTPUT_JSON}")
            logging.info(f"The log file has been saved to {self.LOG_FILE}")
            print("Script execution completed")
            print(f"The generated JSON file has been saved to {self.OUTPUT_JSON}")
            print(f"The log file has been saved to {self.LOG_FILE}")

if __name__ == "__main__":
    try:
        extractor = BagMD5Extractor()
        extractor.process()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please make sure the configuration file exists and is accessible.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")