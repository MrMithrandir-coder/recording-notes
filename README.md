# Recording Notes

面向大学课程与实验室组会的本地录音转写、术语校正和结构化笔记工作流。

项目使用 [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper)
在 Apple Silicon Mac 上转写音频，再由 Codex 结合时间戳、课件、论文、代码和
术语表生成可追溯的课程笔记或组会纪要。设计重点是数理、量子信息和计算机
内容：专业词汇保持规范，公式不能从模糊口述中臆造。

## 特性

- 本地转写：原始录音无需上传到语音识别服务。
- 技术场景优化：默认使用 `mlx-community/whisper-large-v3-turbo`，支持中文
  与中英混合内容。
- 术语提示：内置数理、物理、量子信息、计算机和机器学习词汇，可按课程或
  课题组继续扩充。
- 可追溯输出：同时生成纯文本、带时间戳 Markdown、SRT 和含逐词置信度的
  JSON。
- 两类笔记模板：课程笔记关注概念、定理、推导与复习；组会纪要区分观察、
  解释、建议、决策和待办。
- 公式保真：只有材料或上下文能够唯一确定时才恢复 LaTeX，否则保留口述并
  标记 `【公式待核验，HH:MM:SS】`。
- 隐私友好：录音、材料、转写结果、生成笔记、模型和虚拟环境默认被 Git
  忽略。

## 工作流

```text
录音 / 视频
    │
    ▼
MLX Whisper + 专业术语提示
    │
    ├── .txt             纯文本
    ├── .timestamps.md   带时间戳转写
    ├── .srt             字幕与回听定位
    └── .json            逐词时间戳、置信度和运行元数据
    │
    ▼
Codex + 课件 / 论文 / 代码 / 板书图片 / 术语规范
    │
    ├── .course-notes.md 课程笔记
    └── .lab-meeting.md  组会纪要
```

## 环境要求

- Apple Silicon Mac。
- Python 3.10 或更高版本。
- FFmpeg 与 `ffprobe`。
- 首次下载 Whisper 模型时需要网络；下载完成后可离线转写。

使用 Homebrew 安装系统依赖：

```bash
brew install ffmpeg python@3.13
```

本地 Whisper 转写不需要 OpenAI API Key。Codex 只会处理你明确交给它的
转写文本和材料。

## 快速开始

进入仓库并创建隔离的 Python 环境：

```bash
cd recording-notes
./bin/setup
./bin/transcribe --doctor
```

`./bin/setup` 只在仓库中创建 `.venv`，不会替换系统 Python。默认模型在
第一次实际转写时从 Hugging Face 下载；未完成的下载可以继续。

将录音放入 `recordings/`，然后运行：

```bash
./bin/transcribe "recordings/2026-09-03-量子信息课程.m4a"
```

一次转写多个文件：

```bash
./bin/transcribe recordings/lecture-01.m4a recordings/lecture-02.m4a
```

常用选项：

```bash
# 英语录音
./bin/transcribe --language en recordings/seminar.m4a

# 自动检测语言
./bin/transcribe --language auto recordings/discussion.m4a

# 快速测试用小模型；正式技术内容仍建议使用默认大模型
./bin/transcribe --model mlx-community/whisper-small-mlx recordings/smoke-test.m4a

# 确认后覆盖已有的同名输出
./bin/transcribe --force recordings/lecture-01.m4a
```

完整参数：

```bash
./bin/transcribe --help
```

## 输出文件

默认输出到 `transcripts/`：

| 文件 | 用途 |
|---|---|
| `<名称>.txt` | 快速阅读和全文搜索 |
| `<名称>.timestamps.md` | 为笔记中的重要结论提供时间戳证据 |
| `<名称>.srt` | 配合播放器回听 |
| `<名称>.json` | 保存模型、音频哈希、时长、逐词时间戳和置信度；不记录本机绝对路径 |

如果任意同名输出已经存在，脚本会停止，避免意外覆盖。只有明确需要重新转写
时才使用 `--force`。

## 专业术语配置

通用术语位于 `glossary/asr-terms.txt`。每次转写前，将本门课程或课题组的
专有词追加到 `glossary/custom-terms.txt`，一行一个：

```text
量子近似优化算法 / Quantum Approximate Optimization Algorithm / QAOA
张量网络 / tensor network
教师或报告人姓名 / English spelling
项目代号 Aurora-7
数据集 ImageNet-1K
函数 calculate_partition_function
变量 rho_A / 约化密度矩阵
```

建议优先添加：

1. 课程名、教师、报告人和实验室成员姓名。
2. 论文作者、算法、数据集、设备和项目代号。
3. 容易听错的中英文专业词及缩写。
4. 包、模块、类、函数、变量和配置字段的准确大小写。
5. 本课程采用的符号、单位和特定中文译法。

不要把整份讲义复制进 ASR 提示词。课件、论文、代码和板书图片应放在
`materials/`，交给 Codex 做交叉核验。详细标准见
`glossary/standards.md`。

## 使用 Codex 生成笔记

### 课程笔记

完成转写后，可以对 Codex 说：

```text
请处理 recording-notes/transcripts/2026-09-03-量子信息课程的转写，
结合 materials 中同名或同日期的课件，生成课程笔记。核验公式、符号、
专业术语、数值和单位，并检查 JSON 中的低置信度词。所有不确定内容保留
时间戳并列入“需人工回听/核验”。
```

### 实验室组会

```text
请处理 recording-notes/transcripts 中最新的组会转写，结合 materials 中
对应的论文、图表和代码生成组会纪要。严格区分观察、解释、建议、决策和
待办；不得猜测负责人、截止时间、实验参数或结论。
```

Codex 的项目级质量规则在 `AGENTS.md`，完整任务提示位于
`templates/codex-prompts.md`。生成结果默认写入 `notes/`。

## 公式与符号

语音无法稳定表达复杂公式，尤其是上下标、分式、积分范围、矩阵维度和希腊
字母。项目采用以下证据优先级：

1. 课件、板书照片、论文或代码中的原式。
2. 转写上下文与明确的符号定义。
3. 仅有口述、但写法仍然唯一的简单公式。
4. 无法唯一确定时保留口述，并标记 `【公式待核验，HH:MM:SS】`。

逐词置信度只用于决定优先回听哪些位置。低置信度不等于错误，高置信度也不
能证明公式、专名、数值或代码标识符正确。

## 目录结构

```text
recording-notes/
├── AGENTS.md                 Codex 项目级质量规则
├── README.md
├── config.json               Whisper 默认配置
├── bin/
│   ├── setup                 创建环境并安装依赖
│   ├── transcribe            命令入口
│   └── transcribe.py         转写与多格式输出实现
├── glossary/
│   ├── asr-terms.txt         通用 ASR 术语提示
│   ├── custom-terms.txt      课程或实验室专有词
│   └── standards.md          术语、符号、单位与公式规范
├── materials/                课件、论文、代码、图片与实验材料
├── notes/                    Codex 生成的笔记
├── recordings/               原始录音或视频
├── templates/
│   ├── codex-prompts.md
│   ├── course-notes.md
│   └── lab-meeting.md
├── tests/
└── transcripts/              Whisper 输出
```

## 测试与诊断

环境诊断：

```bash
./bin/transcribe --doctor
```

运行不需要模型的单元测试：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

常见问题：

- 首次运行停在下载阶段：保持网络和电源稳定，重新执行同一命令即可续传。
- 技术词识别不准：先把标准写法加入 `glossary/custom-terms.txt`，再用
  `--force` 重新转写。
- 中英文识别异常：明确指定 `--language zh`、`--language en`，或使用
  `--language auto`。
- 提示 FFmpeg 缺失：运行 `brew install ffmpeg` 后重新执行诊断。
- 输出已存在：确认确实需要替换后再添加 `--force`。

## 隐私与数据管理

仓库默认不会提交以下内容：

- `recordings/` 中的原始录音。
- `materials/` 中的课件、论文和实验材料。
- `transcripts/` 中的转写与时间戳。
- `notes/` 中生成的课程和组会笔记。
- `.venv/`、模型缓存和运行日志。

不要把 API Key、访问令牌、未公开论文、受试者信息或其他敏感数据写进
配置、模板和术语表。推送前仍应检查 `git status` 和暂存内容。

## 当前限制

- 说话人分离尚未实现，多人组会需要结合上下文或议程确认发言者。
- Whisper 术语提示只能改善识别概率，不能保证专业词一定正确。
- 仅靠音频无法可靠还原复杂公式；提供课件或板书图片会显著提高笔记质量。
- 当前转写实现针对 Apple Silicon 与 MLX，其他平台需要更换 Whisper 后端。

## 许可证

本项目基于 [MIT License](LICENSE) 开源。你可以使用、修改和再分发代码，
但需保留原始版权与许可证声明。
