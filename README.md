# BenchICT_toolchain

本路径包含 BenchICT 的工具链和配置文件。以下是主要组件及其功能列表：

1. **BenchICT_Config.py**
   - 一键生成 BenchICT 的 json 文件。

2. **test_case_template.json**
   - BenchICT_Config.py 的配置文件。

3. **Edit_Case_Config.py**
   - 一键修改 BenchICT 的 json 文件的小工具。

4. **extract_bag_md5s.py**
   - 一键从 yaml 文件中提取 case 的 bag 的 md5。
   - 注意：时间戳需要自行配置。

5. **update_from_mff_to_function_spec.py**
   - 一键从本地 mff 分支同步到 function_spec 仓库的指定分支。
   - 注意：此脚本使用绝对路径。

6. **bag.json**
   - bag 的配置文件。
   - 需要运行 extract_bag_md5s.py 才能生成。
   - 需要手动补充 trigger time。

7. **路径配置**
   - 除了 update_from_mff_to_function_spec.sh 使用绝对路径外，其他脚本均使用相对路径。

8. **配置文件**
   - 注意需要先从template路径下将模板文件手动复制到config中哦！

## 更多信息

更详细的信息请参考 [BenchICT 文档的第六章](https://momenta.feishu.cn/wiki/SAUkwJSHyiweGhkSbCHcAT7tnlh)。