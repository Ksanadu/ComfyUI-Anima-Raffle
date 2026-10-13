# ComfyUI-Anima-Raffle

![Anima Style Explorer](assets/banner.jpg)

将 [Anima Style Explorer](https://github.com/fulletLab/comfyui-anima-style-nodes) 与 [ComfyUI-Raffle](https://github.com/rainlizard/ComfyUI-Raffle) 整合为一个 ComfyUI 节点包，提供风格与角色浏览、Auto Cycle 轮换、标签抽签及 Anima/SD 标签格式切换。

An integrated ComfyUI node pack combining Anima Style Explorer and ComfyUI-Raffle, with character sex filters, Auto Cycle, and Anima/SD tag formatting.

整合版本：`1.1.0`。本项目是独立社区 fork，保留原有节点名称和接口。

## 新增功能

### 1. Character Sex：角色分类与筛选

Characters 页签在排序选项（Popularity、Uniqueness、A - Z）右侧提供 `Character Sex`。Auto Cycle Settings 中也提供同名选项，两处均默认 **Female**。

分类读取角色完整的 **trigger + tags**，不受当前选择的 `Trigger` 或 `Trigger + tags` 插入模式影响：

| 选项 | 分类规则 |
| --- | --- |
| Female | 含 `1girl`，且不含 `1boy` |
| Male | 含 `1boy`，且不含 `1girl` |
| Others | 同时含两者，或两者都不含 |

浏览器与 Auto Cycle 的筛选可分别设置。Auto Cycle 的筛选同时适用于 `Characters only` 和 `Styles + Characters`；`Styles only` 不受影响。循环过程中切换分类，下一轮会从新的角色池抽取，并替换上一轮的角色标签。

### 2. Raffle：Anima / SD 标签格式

Raffle 主面板新增 `tag_form` 下拉菜单：

| 选项 | 示例 | 行为 |
| --- | --- | --- |
| Anima | `best_quality` → `best quality` | 将抽取标签中的所有下划线替换为空格 |
| SD（默认） | `best_quality` | 保留原有下划线格式，兼容原工作流 |

格式转换同时应用于 **Raffled output** 和 **Unfiltered**。抽签种子、标签池筛选、输出标签顺序及 **Debug info** 均不改变，不需要额外的下划线替换节点。

### 3. Anima Style Explorer (Text)

保留新增的纯文本节点：输入多行提示词，原样输出 `STRING` 类型的 `text`，无需连接 CLIP。可使用风格浏览器、随机风格和提示词补全，再接入独立文本编码或其他文本处理节点。

## 包含的节点

| 节点名称 | 输出 | 用途 |
| --- | --- | --- |
| Anima Style Explorer | `CONDITIONING` | 浏览风格与角色，并用 CLIP 编码提示词 |
| Anima Style Explorer (Text) | `STRING` | 浏览与编辑提示词，直接输出文本 |
| Raffle | 三个 `STRING` | 输出筛选后的标签、未筛选标签和调试信息 |
| Preview History (Raffle) | 图片预览界面 | 保存并显示最近生成的图片 |
| Tag Category Strength (Raffle) | 两个 `STRING` | 按标签类别调整权重，输出标签和调试信息 |
| Curved Rescale CFG (Raffle) | `MODEL` | 为模型应用曲线 CFG 重缩放 |

Anima 节点位于 `Anima` 分类；Raffle、预览和权重节点位于 `Raffle` 相关分类，CFG 节点位于 `advanced/model`。

## 安装

在 `ComfyUI/custom_nodes/` 目录中执行：

```bash
git clone https://github.com/Ksanadu/ComfyUI-Anima-Raffle.git
```

也可以下载仓库 ZIP，解压为 `ComfyUI/custom_nodes/ComfyUI-Anima-Raffle/`。目录内应直接包含 `__init__.py`、`js/`、`data/` 和 `lists/`。

如需安装依赖，请使用**实际运行 ComfyUI 的 Python 环境**，在本节点包目录执行：

```bash
python -m pip install -r requirements.txt
```

然后重启 ComfyUI，并刷新浏览器页面以加载前端更新。

本包使用原版节点的注册名称和 `/anima` 路由。安装整合包时，将原版 `comfyui-anima-style-nodes`、`ComfyUI-Raffle` 及此前安装的整合包移出 `custom_nodes`，避免重复加载。已有工作流继续使用原有节点名称。

### 从此前的 fork 更新

仓库已从 `Ksanadu/comfyui-anima-style-nodes` 改名为 `Ksanadu/ComfyUI-Anima-Raffle`。在已有克隆目录中更新远程地址：

```bash
git remote set-url origin https://github.com/Ksanadu/ComfyUI-Anima-Raffle.git
git pull --ff-only
```

## 使用示例

### 风格或角色直接编码

```text
CheckpointLoader --(clip)--> Anima Style Explorer --(conditioning)--> KSampler
```

在节点内编辑提示词，打开 `Style Browser`，选择风格或角色。角色卡片支持 `Trigger` 和 `Trigger + tags`，艺术家标签保持 `@artist` 格式。

### 纯文本节点与 Raffle 组合

```text
Anima Style Explorer (Text) --(text)----\
                                       文本拼接节点 --> CLIP Text Encode --> KSampler
Raffle --(Raffled output)--------------/                      ^
CheckpointLoader ---------------------------(clip)----------|
```

文本拼接节点由你的工作流提供。使用 Anima 时将 Raffle 的 `tag_form` 设为 **Anima**；需要下划线标签时设为 **SD**。Raffle 的 `negative_prompt` 可连接负面提示词字符串，用于从最终输出中移除相应标签。

### Auto Cycle

打开 Auto Cycle Settings，设置：

- **Rotate**：Styles only、Characters only 或 Styles + Characters。
- **Character Insert**：Trigger 或 Trigger + tags。
- **Character Sex**：Female、Male 或 Others，默认 Female。
- **Artists / Characters**：每轮选取的艺术家或角色数量。
- **Subject Tag**：保留提示词，或指定人物数量标签。
- **Images**：每组选中标签重复排队的次数。
- **Random**：均匀随机或按图片数量加权。
- **Resume after stop**：停止后是否保留循环进度。

点击 Play 开始排队，点击 Stop 停止后续循环排队。风格标签与角色标签分别管理。

### Raffle 筛选

`use_general`、`use_questionable`、`use_sensitive` 和 `use_explicit` 控制参与抽取的内置标签列表。

`taglists_must_include` 要求候选列表包含所有指定标签；`exclude_taglists_containing` 排除包含任一指定标签的整个候选列表。`exclude_tag_categories`、`filter_out_tags` 和 `negative_prompt` 控制最终输出中的标签。筛选过严时，可根据 Debug info 中的标签池数量调整设置。

## 保留的原版功能

- 本地风格数据、提示词补全和随机风格。
- Animadex Styles 与 Characters 页签、触发词和描述标签。
- 风格添加与替换弹窗、可编辑 Prompt Preview、Swipe Mode 和收藏。
- Update Styles、可选远程预览和本地预览下载。
- 使用用户提供的 Fullet API Key 发布提示词或多图拼图。
- Raffle 内置标签列表、类别筛选、历史预览、类别权重及曲线 CFG。

标签数据与 Raffle 抽取可离线使用。远程预览默认关闭；索引更新、预览下载和 Fullet 发布需要联网。API Key 不写入工作流，保存方式由原有本地会话设置控制。

## 整合修复与验证

本次整合修复了 Raffle 字符串断行造成的 Python 语法错误，补齐六个节点的注册、`WEB_DIRECTORY` 和实际路由注册调用，并让纯文本节点在修改标题后仍能获得前端控件。

验证包括真实 ComfyUI 加载器、六个节点输入定义、前端资源注册、本机路由、实际 Raffle 数据，以及历史预览、类别权重与 CFG 的基本执行。浏览器中验证了三类角色筛选和 Auto Cycle 的角色替换。

回归测试可在仓库目录执行：

```bash
python -m unittest discover -s tests -p "test_*.py"
node --test tests/character_filters.test.mjs
```

包含四项 Raffle 回归测试和三项角色分类测试。验证未执行完整模型出图。

## 来源与致谢

- [fulletLab/comfyui-anima-style-nodes](https://github.com/fulletLab/comfyui-anima-style-nodes)：Anima Style Explorer 及其浏览、循环和联网功能。
- [rainlizard/ComfyUI-Raffle](https://github.com/rainlizard/ComfyUI-Raffle)：Raffle、历史预览、类别权重和曲线 CFG。
- [ThetaCursed Anima Style Explorer](https://thetacursed.github.io/Anima-Style-Explorer) 与 [Anima-Assets](https://github.com/ThetaCursed/Anima-Assets)：原有风格数据与预览资源。
- [Animadex](https://animadex.net)：可选艺术家与角色索引。

原作者、数据整理者和参考图片创作者的署名与来源予以保留。整合维护：Ksanadu。

## 许可

仓库保留 Anima Style Explorer 原版的 MIT [LICENSE](LICENSE)。Raffle 代码及标签数据来源见其[上游仓库](https://github.com/rainlizard/ComfyUI-Raffle)；上游许可声明和各数据来源的适用条款分别保留。
