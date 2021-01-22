# 上外自动健康打卡脚本

**免责声明：本脚本仅用于学习与交流目的，禁止使用此脚本打卡。请自行通过企业微信手动打卡，并填写真实数据。**

## 使用方法

*本文假定读者了解如何搭建 Python 运行环境以及基本的命令行使用方法。若否，请善用搜索引擎。*

1. 下载脚本。两种方法：

   1. 点击页面最上方绿色的“Code”按钮，然后点击“Download ZIP”。下载后解压。

   2. 通过 `git`：

      ```
      git clone https://github.com/shniubobo/sisudaka.git
      cd sisudaka
      ```

2. （可选）创建虚拟环境。

3. 安装依赖：

   ```
   pip install -r requirements.txt
   ```

4. 复制 [`config.example.py`](config.example.py)，并重命名为 `config.py`，然后根据下文修改其中的配置。

5. 运行脚本：

   ```
   ./sisudaka.py
   ```

## 配置文件

文件中主要有两个配置需要修改，已通过注释标出。

- `ID` 填写学号。

- `RULES` 是答题的规则。按文件中的说明修改引号内的内容即可。

  <details>
    <summary>如果你想了解更多的话……</summary>

    字典中的键用于匹配问题，键对应的值则是答案。对于选择题，字典的值用于匹配答案；对于填空题，字典的值会全部作为答案提交。脚本只会回答没有提供默认答案的题目（目前共 3 题），因此规则也只需提供这 3 题的答案即可。

    字典的键接受 `str`，而值接受 `str` 或返回值是 `str` 的 `Callable`。

    体温的示例答案是一个函数，每次调用会随机生成一个 36~37 度之间的温度。
  </details>

其余部分如需修改请自行阅读脚本代码。

## 贡献

如遇 bug，请将日志与复现方式提交至 [Issues](https://github.com/shniubobo/sisudaka/issues)。

提交代码前请通过 `flake8` 检查一下代码风格。

有问题也欢迎在 [Issues](https://github.com/shniubobo/sisudaka/issues) 中提出。

## 许可

本项目以 GNU AGPLv3 发布。详见 [`LICENSE.txt`](LICENSE.txt)。

```
上外自动健康打卡脚本
Copyright (C) 2021 shniubobo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
