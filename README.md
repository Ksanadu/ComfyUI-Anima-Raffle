# ComfyUI-Anima-Raffle

将 [Anima Style Explorer](https://github.com/fulletLab/comfyui-anima-style-nodes) 与 [ComfyUI-Raffle](https://github.com/rainlizard/ComfyUI-Raffle) 整合为一个 ComfyUI 节点包，提供风格与角色浏览、Auto Cycle 轮换、角色与艺术家抽签及 Anima/SD 标签格式切换。

An integrated ComfyUI node pack combining Anima Style Explorer and ComfyUI-Raffle, with artist and character raffles, character sex filters, Auto Cycle, and Anima/SD tag formatting.

整合版本：`1.9.0`。本项目是独立社区 fork，保留原有节点类型标识和接口。

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

### 2. Raffle Scene：Anima / SD 标签格式

**Raffle Scene** 主面板提供 `tag_form` 下拉菜单：

`1.6.2` 将原 **Raffle** 节点的显示名称改为 **Raffle Scene**，位于 **Anima Raffle** 分类。内部类型标识仍为 `Raffle`，已有工作流可继续加载。

Since version 1.6.2, the original Raffle node is displayed as **Raffle Scene** under **Anima Raffle**. Its internal `Raffle` identifier is retained for existing workflows.

| 选项 | 示例 | 行为 |
| --- | --- | --- |
| Anima | `best_quality` → `best quality` | 将普通词组标签的下划线替换为空格，保留颜文字 |
| SD（默认） | `best_quality` | 保留原有下划线格式，兼容原工作流 |

格式转换同时应用于 **Raffled output** 和 **Unfiltered**。抽签种子、标签池筛选、输出标签顺序及 **Debug info** 均不改变，不需要额外的下划线替换节点。

`1.2.1` 修复了 Raffle 的 `tag_form` 在 F5 刷新或重新打开工作流后重置的问题。Anima 和 SD 选择均可保留，已有工作流可直接加载。

`^_^`、`o_o`、`>_<`、`@_@`、`T_T` 等颜文字保留原样。角色 `Trigger + tags` 的插入与复制也使用相同的保留规则；颜文字仍可通过负面提示词或标签过滤选项移除。

### 3. Anima Style Explorer (Text)

保留新增的纯文本节点：输入多行提示词，原样输出 `STRING` 类型的 `text`，无需连接 CLIP。可使用风格浏览器、随机风格和提示词补全，再接入独立文本编码或其他文本处理节点。

### 4. Raffle Character

在 `Anima Raffle` 分类中提供 **Raffle Character**，直接从 Anima Style Explorer 的 Animadex 角色索引抽取角色，不需要连接输入节点。主面板提供八项控件：

| 控件 | 默认值 | 行为 |
| --- | --- | --- |
| seed | `0` | 相同角色索引、筛选条件和种子得到相同角色 |
| taglists_must_include | 空 | 角色的 trigger + tags 必须包含所有指定标签 |
| filter_out_tags | 空 | 角色包含任一指定标签时，排除整个角色 |
| tag_form | Anima | Anima 输出空格标签，SD 输出下划线标签；颜文字保留原样 |
| character_sex | Female | Female、Male、Others 及三种组合，各类别规则与浏览器和 Auto Cycle 一致 |
| output_mode | trigger+tags | `trigger+tags` 输出完整提示词；`trigger` 只输出角色 trigger |
| top_n | `0` | 先完成性别与标签筛选，再从 Popularity 最高的前 N 位中抽取；0 使用全部匹配角色 |
| character_count | `1` | 每次抽取的不同角色数量，可填写正整数；不超过最终抽签池大小 |

两个输入框使用逗号或换行分隔标签，支持默认的空格写法，也兼容下划线写法及大小写差异。例如 `taglists_must_include` 填入 `touhou, blue eyes`，只会抽取完整 trigger + tags 同时包含 `touhou` 和 `blue eyes` 的角色。`filter_out_tags` 填入 `red eyes, long hair`，会排除包含其中任一标签的角色。

两框均为空时，从当前 Character Sex 对应的角色池随机抽取。默认 Female 并不包含 Male 或 Others。

`1.9.0` 新增 `character_count` 抽取数量整数栏，默认 `1`，没有 6 个的限制。先完成性别、必需标签与排除标签筛选，再应用 `top_n`，最后从该角色池中不放回地抽取指定数量。例如 `top_n = 10`、`character_count = 3`，会从最热门的十位匹配角色中抽取三位不同角色。

多个角色按抽中顺序用逗号合并到 **Raffled output** 和 **Unfiltered**：`trigger` 模式合并各角色的完整 trigger，`trigger+tags` 模式合并各自完整的 trigger + tags，继续使用 Anima / SD 格式并保留颜文字。Debug info 显示抽取数量与逐个角色名单。指定数量超过最终角色池大小时，节点会提示减少数量或调整筛选 / `top_n`，不会重复抽取或悄悄减少数量。默认抽取 1 个时保留原有 seed 的角色和文本结果。

Version 1.9.0 adds the positive integer `character_count` control (default `1`, not limited to six). Draws select distinct characters after sex/tag filtering and Top N. Selected triggers or complete trigger + tags are joined with commas in both text outputs, preserving Anima/SD formatting and emoticons. Debug info lists every selected character. Requests exceeding the final pool size report an error instead of repeating characters or reducing the count. A count of one preserves existing seeded selections.

`1.8.0` 为 **Raffle Character** 新增三种性别组合：

| 选项 | 抽取范围 |
| --- | --- |
| Female+Male | 合并 Female 与 Male，不包含 Others |
| Female+Others | 合并 Female 与 Others，不包含 Male |
| Female+Male+Others | 三类全部参与 |

组合选项按角色合并候选池，保留原有标签条件筛选；`top_n` 在合并并筛选后的整个候选池中按 Popularity 截取前 N 位，再随机抽取。Others 仍包含同时有 `1girl` 和 `1boy`、或两者都没有的角色。默认仍为 Female，浏览器和 Auto Cycle 的性别选单保持原有三项。

Version 1.8.0 adds **Female+Male**, **Female+Others**, and **Female+Male+Others** to Raffle Character. Each option draws from the union of its named categories, with existing tag filters still applied. Top N limits the combined matching pool by popularity before seeded sampling. The default remains Female; browser and Auto Cycle options are unchanged.

`1.7.0` 新增 `top_n` 整数栏。例如必需标签填写 `touhou, blue eyes`、`top_n` 填 `10` 时，先筛出符合当前性别、必需标签与排除标签的角色，再按本地作品数量 `works` 从高到低排序，仅从前十位中随机抽取。匹配不足 N 位时使用全部匹配角色；数量相同时保持索引中的原有顺序。默认 `0` 不限制范围，也保留原有候选顺序和 seed 抽取结果。Debug info 显示匹配角色总数和实际抽签池大小。

Version 1.7.0 adds the integer `top_n` control (default `0`). Sex and include/exclude tag filters run first; a positive value then limits the draw to the N most popular matching characters by local work count. Fewer than N matches uses all matches, and ties retain index order. Zero preserves the full matching pool and existing seeded selections. Debug info reports both matching and final draw pool sizes.

保留三个输出口：**Raffled output** 和 **Unfiltered** 都输出 `output_mode` 选定的内容，按 `tag_form` 格式化。两者相同，因为此节点的标签条件用于筛选角色。**Debug info** 显示角色索引数量、候选池数量、种子、条件、输出模式和抽中角色。

`1.5.0` 新增的 `output_mode` 默认保持完整 **trigger + tags**，兼容已有工作流。选择 `trigger` 时，仍用完整 trigger + tags 检查性别、必需标签和排除标签，抽取结果不变，只减少输出内容。trigger 自身含有的作品名等逗号分隔内容会完整保留。例如 `touhou, blue eyes` 仍可筛选东方蓝眼角色，但输出中只保留该角色原有的 trigger。

**Raffle Character** offers `trigger+tags` (default) and `trigger` output modes. Both modes use the full trigger + tags for sex and tag filtering and select the same character for the same seed. Trigger mode outputs only the complete original trigger, formatted for Anima or SD.

角色数据与 Characters 页签共用本地索引。可在该页签使用 Update Styles 更新角色索引，再改变 seed 重新抽取。没有匹配角色时，节点会提示调整条件，不会绕过筛选条件抽取其他角色。

### 5. Preview History：一键清空

**Preview History (Raffle)** 新增 **Clear History** 按钮。点击即可删除该节点包保存的历史图片和对应的临时缩略图，并清空所有 Preview History 节点的预览，无需排队执行工作流。

历史目录由所有 Preview History 节点共用，因此按钮会清空共用历史。只删除该节点生成的 `history_*.png` 与 `PreviewHistory_Item_*.png`，其他文件和 Save Image 保存的出图不受影响。清空后可继续积累新历史；如果工作流仍在出图，后续生成的图片会重新进入历史。

**Preview History (Raffle)** now includes a **Clear History** button. One click clears its shared image history and temporary thumbnails and updates all Preview History previews immediately, without queuing the workflow. Other files and Save Image outputs are preserved; subsequent generations start a new history.

### 6. Prompt Snapshot：随图片保存提示词

**Prompt Snapshot (Raffle)** 接收 `text`，只读显示本次实际输入的完整提示词，并将原文保存到当前图片的工作流中。以后把该 PNG 拖回 ComfyUI，节点从图片内的记录恢复显示，不会读取另一个工作流的文本预览缓存，也会忽略旧任务迟到的显示更新。空格、换行、中文和颜文字均原样保留。

建议放在图片保存路径上，确保先记录提示词，再保存图片：

```text
最终正面提示词 --(text)--> Prompt Snapshot (Raffle)
VAE Decode ----(images)--> Prompt Snapshot (Raffle) --(images)--> Save Image
```

`text` 输出原样直通；`images` 输入可选，图片输出也原样直通。请将与 CLIP 编码相同的最终文本接入 `text`，将图片输出接入 Save Image。图片已接入时，不要把本节点的文本输出接回同一条出图路径的 CLIP 编码，否则会形成循环。

只接文本时可作为保存状态的文本预览使用；要确保记录写入出图文件，请使用上面的图片连线。节点每次排队都重新写入当前工作流的记录，图片路径上的上游模型缓存仍可使用。修改其他控件不会自动改写已记录的文本，重新运行节点才会更新。

使用保留 ComfyUI 工作流元数据的 PNG；关闭元数据保存或去掉图片元数据后无法恢复。该功能只保存安装后经此节点记录的新图片，无法补回旧图里缺失的提示词。

`1.4.1` 修复切换到其他工作流页签后，出图记录仍显示上一张提示词的问题。后台同步写入 PNG 工作流和 ComfyUI 任务历史的工作流副本；前端按每次排队的独立标识接收后台结果，切回页签时可恢复对应记录。保存与任务历史同步不依赖该工作流是否正在页面上显示。

**Prompt Snapshot (Raffle)** captures the exact received prompt in each image's embedded workflow. Reloading that PNG restores its own read-only text, with no dependence on another workflow's preview cache. Connect the final prompt to `text`, route VAE Decode through the node's `images` input/output into Save Image, and keep PNG workflow metadata enabled. Text and images pass through unchanged.

Version 1.4.1 also updates the workflow copy kept in ComfyUI task history and restores results received while another workflow tab is active. Prompt recording and task-history synchronization run on the server independently of the currently visible tab.

### 7. Raffle Artist

`1.5.0` 新增的 **Raffle Artist** 现位于 `Anima Raffle` 分类，共用 Anima Style Explorer 的本地 Theta 与 Animadex 艺术家索引，自动去重并排除角色记录，无需联网或连接输入节点。

| 控件 | 默认值 | 行为 |
| --- | --- | --- |
| seed | `0` | Random 的随机种子；Sequential 的组序号，从 0 开始 |
| mode | Random | `Random` 随机抽取；`Sequential` 按所选排列分组遍历 |
| artist_count | `1` | 每次抽取 1–6 位不同的艺术家 |
| tag_form | Anima | Anima 输出 `@artist name`；SD 输出 `artist_name`，不加 `@` |
| sort_by | A–Z | Sequential 的排列方式：Popularity、Uniqueness、A–Z、Shuffle |
| sort_order | Ascending | 每种排列均支持 Ascending（升序）和 Descending（降序） |
| shuffle_seed | `0` | 固定 Shuffle 的整库排列；改变此值会重新洗牌，不会自动递增 |

保留 **Raffled output**、**Unfiltered** 和 **Debug info** 三个输出口。前两项均为逗号分隔的艺术家标签；第三项显示本地艺术家池数量、模式、排序、种子、数量与抽中名单。切换 Anima / SD 只改变格式，不改变抽中的艺术家。

`1.6.0` 新增四种顺序排列与各自的升降序：

| sort_by | Ascending（升序） | Descending（降序） |
| --- | --- | --- |
| Popularity | 作品数量从少到多 | 作品数量从多到少 |
| Uniqueness | 独特度评分从低到高 | 独特度评分从高到低 |
| A–Z | 名称 A–Z | 名称 Z–A |
| Shuffle（洗牌遍历） | 从固定洗牌序列的开头向后遍历 | 从同一洗牌序列的末尾向前遍历 |

作品数量使用本地 `works`，独特度使用本地 `uniqueness_score`，统计值相同时按名称 A–Z 稳定排序。缺失或无效的统计值在升序和降序中都排到最后；官方记录中明确没有独特度评分的艺术家也按缺失处理。排序选项只影响 Sequential，Random 继续使用原有种子随机抽取逻辑。新增控件放在原有控件之后，默认 A–Z 升序，已有工作流的抽取结果保持不变。

Sequential 模式中，`seed = 0` 取第一组，`seed = 1` 取下一组，到末尾自动绕回开头。例如每次取 2 位时，依次取第 1–2、3–4、5–6 位。将 seed 的 **control_after_generate** 设为 **increment**，即可每次运行自动轮换下一组。Random 模式设为 **randomize** 可持续随机抽取，设为 **fixed** 可复现同一结果。单次抽取不会重复艺术家；跨次抽取可以再次遇到同一位艺术家。更新索引或修改数量后，同一 seed 对应的结果可能改变。

洗牌遍历时，保持 **shuffle_seed 固定**，让 **seed 递增**，即可连续遍历同一份随机排列，一轮内不重复，到末尾后循环。修改 shuffle_seed 才会生成另一份排列；仅切换升降序会反转同一份排列。重新打开工作流时，相同索引和设置可复现同一位置。

可将 Raffle Artist 的输出与 Raffle Scene、Raffle Character 的输出交给文本拼接节点，再送入 CLIP Text Encode。

**Raffle Artist** draws 1–6 distinct artists per run from the shared local artist index. Choose Random for seeded sampling or Sequential for batches with wraparound. Version 1.6.0 adds Popularity, Uniqueness, A–Z, and Shuffle ordering, each with Ascending and Descending directions. Popularity uses local work counts and Uniqueness uses local scores; missing metrics stay last and ties use A–Z names. Shuffle uses a separate fixed `shuffle_seed`; Descending reverses the same permutation. Keep `shuffle_seed` fixed and set the main seed's **control_after_generate** to **increment** to traverse consecutive batches without reshuffling. Sorting controls affect Sequential only; defaults preserve existing A–Z workflows. Anima outputs `@artist name`; SD outputs `artist_name` without `@`. The three outputs remain Raffled output, Unfiltered, and Debug info.

## 本地角色文本数据

角色名称、trigger、描述 tags、作品系列和数量统计已保存在本地 `data/animadex_index.json`。**Characters 浏览、Character Sex 筛选、Auto Cycle 角色轮换和 Raffle Character 抽取均直接读取本地文本，不需要连接 Animadex。**

`1.4.2` 于 **2026-10-17** 导入官网当前提供的官方角色 CSV（导出版本 `1780120177`），共 **36,492 条角色**；按 trigger + tags 分类为 Female **22,720**、Male **4,649**、Others **9,123**。相比旧库新增 2,199 条、移除 8 条旧记录，并保留 15,879 条艺术家记录。来源与校验信息见 `data/character_data_source.json`。

本次只下载文本数据。角色预览图片不是离线文本抽取的必需项；原有预览地址保留，新角色未额外下载预览。7,679 条官方记录未提供描述 tags，保留其 trigger，不自动编造标签。更新数据后，既有 seed 对应的抽取结果可能随角色池变化。

36,492 character records are bundled locally from the official Animadex CSV export downloaded on 2026-10-17. Character browsing, sex/tag filtering, Auto Cycle, and Raffle Character work offline. This update downloads text only and preserves the existing artist index. See `data/character_data_source.json` for provenance.

## 包含的节点

| 节点名称 | 输出 | 用途 |
| --- | --- | --- |
| Anima Style Explorer | `CONDITIONING` | 浏览风格与角色，并用 CLIP 编码提示词 |
| Anima Style Explorer (Text) | `STRING` | 浏览与编辑提示词，直接输出文本 |
| Raffle Scene | 三个 `STRING` | 输出筛选后的场景标签、未筛选标签和调试信息 |
| Raffle Character | 三个 `STRING` | 按标签和性别抽取角色，可输出 trigger + tags 或仅 trigger |
| Raffle Artist | 三个 `STRING` | 顺序或随机抽取 1–6 位艺术家，支持四种升降序排列与 Anima / SD 格式 |
| Preview History (Raffle) | 图片预览界面 | 保存并显示最近生成的图片，支持一键清空共用历史 |
| Prompt Snapshot (Raffle) | `STRING`、`IMAGE` | 随图片工作流保存提示词，重新打开图片时恢复只读显示 |
| Tag Category Strength (Raffle) | 两个 `STRING` | 按标签类别调整权重，输出标签和调试信息 |
| Curved Rescale CFG (Raffle) | `MODEL` | 为模型应用曲线 CFG 重缩放 |

从 `1.6.1` 起，以上九个节点统一位于右键添加节点菜单的 **Anima Raffle** 分类，包含两个 Anima Style Explorer 节点、Raffle Scene、角色与艺术家抽签、历史预览、提示词快照、标签权重与 CFG 节点。节点类型标识、接口及已有工作流保持兼容。

Since version 1.6.1, all nine nodes appear together under **Anima Raffle** in ComfyUI's Add Node menu. Node identifiers and interfaces remain compatible with existing workflows.

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

本包使用原版节点的类型标识和 `/anima` 路由。安装整合包时，将原版 `comfyui-anima-style-nodes`、`ComfyUI-Raffle` 及此前安装的整合包移出 `custom_nodes`，避免重复加载。已有工作流继续使用原有节点类型标识。

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

### 纯文本节点与 Raffle Scene 组合

```text
Anima Style Explorer (Text) --(text)----\
                                       文本拼接节点 --> CLIP Text Encode --> KSampler
Raffle Scene --(Raffled output)--------/                      ^
CheckpointLoader ---------------------------(clip)----------|
```

文本拼接节点由你的工作流提供。使用 Anima 时将 Raffle Scene 的 `tag_form` 设为 **Anima**；需要下划线标签时设为 **SD**。Raffle Scene 的 `negative_prompt` 可连接负面提示词字符串，用于从最终输出中移除相应标签。

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

### Raffle Scene 筛选

`use_general`、`use_questionable`、`use_sensitive` 和 `use_explicit` 控制参与抽取的内置标签列表。

`taglists_must_include` 要求候选列表包含所有指定标签；`exclude_taglists_containing` 排除包含任一指定标签的整个候选列表。`exclude_tag_categories`、`filter_out_tags` 和 `negative_prompt` 控制最终输出中的标签。筛选过严时，可根据 Debug info 中的标签池数量调整设置。

### Raffle Character 工作流

```text
Raffle Character --(Raffled output)--> CLIP Text Encode --(conditioning)--> KSampler
                                           ^
CheckpointLoader ----------------(clip)----|
```

也可以将输出与 Raffle Scene 的场景标签或其他提示词用文本拼接节点组合后再编码。Raffle Character 的 `filter_out_tags` 排除整个角色，Raffle Scene 的同名控件只移除最终输出标签。

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

验证包括真实 ComfyUI 加载器、九个节点输入定义、前端资源注册、本机路由、实际 Raffle 与角色和艺术家索引数据，以及历史预览、类别权重与 CFG 的基本执行。浏览器中验证了三类角色筛选和 Auto Cycle 的角色替换。

回归测试可在仓库目录执行：

```bash
python -m unittest discover -s tests -p "test_*.py"
node --test tests/*.test.mjs
```

真实 PNG 快照测试使用 ComfyUI 的 Python 环境执行，最后一个参数为 ComfyUI 根目录：

```bash
python tests/check_prompt_snapshot_comfy.py /path/to/ComfyUI
```

包含七项 Raffle 回归测试、二十九项 Raffle Character 测试、二十项 Raffle Artist 测试、三项角色分类测试、三项前端标签格式测试、九项历史清空与接口测试、五项清空按钮测试，以及十项提示词快照测试和九项快照恢复测试。角色测试覆盖仅 trigger 输出时的完整标签筛选；艺术家测试覆盖四种升降序排列、缺失评分、固定洗牌遍历、顺序分组、循环、种子复现、去重与格式转换。清空测试只使用临时文件，覆盖删除范围、缓存失效、并发出图、请求授权和前端预览更新。快照还使用真实 ComfyUI 执行器、PromptQueue 与 Save Image 验证连续出图、缓存命中、PNG 元数据回读，以及不依赖前端显示的任务历史记录。验证未执行完整模型出图。

## 来源与致谢

- [fulletLab/comfyui-anima-style-nodes](https://github.com/fulletLab/comfyui-anima-style-nodes)：Anima Style Explorer 及其浏览、循环和联网功能。
- [rainlizard/ComfyUI-Raffle](https://github.com/rainlizard/ComfyUI-Raffle)：Raffle、历史预览、类别权重和曲线 CFG。
- [ThetaCursed Anima Style Explorer](https://thetacursed.github.io/Anima-Style-Explorer) 与 [Anima-Assets](https://github.com/ThetaCursed/Anima-Assets)：原有风格数据与预览资源。
- [Animadex](https://animadex.net)：可选艺术家与角色索引。

原作者、数据整理者和参考图片创作者的署名与来源予以保留。整合维护：Ksanadu。

## 许可

仓库保留 Anima Style Explorer 原版的 MIT [LICENSE](LICENSE)。Raffle 代码及标签数据来源见其[上游仓库](https://github.com/rainlizard/ComfyUI-Raffle)；上游许可声明和各数据来源的适用条款分别保留。
