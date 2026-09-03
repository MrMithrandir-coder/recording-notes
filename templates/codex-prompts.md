# Codex 任务提示

## 课程笔记

```text
请处理 recording-notes/transcripts 中指定课程录音的转写。

必须先读取：
1. recording-notes/AGENTS.md
2. recording-notes/templates/course-notes.md
3. recording-notes/glossary/standards.md
4. recording-notes/glossary/asr-terms.txt
5. recording-notes/glossary/custom-terms.txt

同时检查 recording-notes/materials 中名称或日期相符的课件、讲义、代码、
板书图片或论文。按概念依赖重组内容，保留关键时间戳。重点核验公式、
上下标、符号定义、适用条件、数值、单位、英文术语和代码标识符。
读取同名 .json 的逐词置信度，把低置信度技术词和公式口述优先列入核验；
置信度只能作为回听线索，不能单独作为纠错依据。

若公式无法由转写与材料唯一确定，保留口述并写
“【公式待核验，HH:MM:SS】”，不得猜测。不得把补充解释写成教师原话。
生成结果写入 recording-notes/notes，文件名与转写同名并以
.course-notes.md 结尾。
```

## 实验室组会

```text
请处理 recording-notes/transcripts 中指定组会录音的转写。

必须先读取：
1. recording-notes/AGENTS.md
2. recording-notes/templates/lab-meeting.md
3. recording-notes/glossary/standards.md
4. recording-notes/glossary/asr-terms.txt
5. recording-notes/glossary/custom-terms.txt

结合 recording-notes/materials 中名称或日期相符的论文、图表、代码、实验
记录或议程。严格区分观察、解释、假设、质疑、建议、决策和待办。重点
核验数据集、样品、仪器、软件版本、参数、边界条件、指标、误差和单位。
读取同名 .json 的逐词置信度，把低置信度专名、参数、代码标识符和公式
口述优先列入核验；置信度只能作为回听线索，不能单独作为纠错依据。

不得猜测参与者、负责人、截止时间、实验参数或结论；未明确时写“未指定”。
所有决策、待办、关键结果和争议附时间戳。生成结果写入
recording-notes/notes，文件名与转写同名并以 .lab-meeting.md 结尾。
```

## 术语表增量维护

```text
检查本次转写和材料中反复出现、容易误识别且尚未收录的专有名词。只根据
可靠材料或明确上下文，将确认后的标准写法追加到
recording-notes/glossary/custom-terms.txt；不确定项只列入笔记的“术语与
转写疑点”，不要写入术语表。
```
