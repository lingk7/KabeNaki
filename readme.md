# Unity角色立绘提取工具 / Unity Character Sprite Extraction Tool

[中文](#中文) | [English](#english)

---

## 中文

### 魔法少女的魔女审判角色立绘提取工具

一个专门为《魔法少女的魔女审判》(manosaba)游戏设计的Unity角色立绘提取工具，支持从Unity bundle文件中提取、合成和管理角色精灵。

### 功能特点

✨ **智能文件识别**
- 自动区分角色文件和生物文件
- 支持多种处理模式：自动检测、仅提取精灵、完整提取

🎨 **高级精灵合成**
- 修复cheek精灵暗色问题，确保色彩准确
- 支持深度排序和自定义层级
- 实时预览合成效果
- 透明背景支持

🌐 **多语言界面**
- 支持中文和FiXmArge魔女语
- 实时语言切换

📊 **完整数据提取**
- 提取精灵图像和元数据
- 生成层级结构图
- 保存JSON格式的提取数据

🖼️ **可视化界面**
- 直观的精灵选择界面
- 分类显示角色部件
- 实时预览和缩放功能

### 使用方法

1. **选择文件**
   - 点击"选择Bundle文件"
   - 导航到: `manosaba_game\manosaba_Data\StreamingAssets\aa\StandaloneWindows64\naninovel-characters_assets_naninovel\characters`

2. **选择处理模式**
   - 自动检测：根据文件名智能选择模式
   - 仅提取精灵：快速提取所有精灵图像
   - 完整提取：提取精灵+层级数据

3. **精灵选择与合成**
   - 在左侧面板选择要合成的精灵部件
   - 调整深度排序（可选）
   - 实时预览合成效果

4. **保存结果**
   - 保存合成图像为PNG格式
   - 导出提取数据和层级信息

### 输出文件结构
extraction/
├── sprites/ # 提取的精灵图像
├── extraction_data.json # 完整提取数据
├── sprite_data.json # 精灵元数据
└── hierarchy.txt # 层级结构信息

text
### 系统要求

- Python 3.8+
- Windows 10/11 (推荐)
- 至少4GB可用内存

### 安装依赖

```bash
pip install UnityPy pillow numpy
运行方法
bash
python tkinter_app.py
注意事项
确保有足够的磁盘空间存放提取的文件

首次运行可能需要较长时间初始化

建议关闭其他大型应用程序以获得最佳性能

Tkinter通常随Python一起安装，如遇问题请确保安装正确

English
Manosaba Character Sprite Extraction Tool
A specialized Unity character sprite extraction tool designed for the "Manosaba" game, supporting extraction, composition, and management of character sprites from Unity bundle files.

Features
✨ Smart File Recognition

Automatic distinction between character files and creature files

Multiple processing modes: Auto-detect, Sprites Only, Full Extraction

🎨 Advanced Sprite Composition

Fixed cheek sprite dark color issues for accurate colors

Depth sorting and custom layer support

Real-time preview

Transparent background support

🌐 Multilingual Interface

Support for Chinese and FiXmArge magical girl language

Real-time language switching

📊 Complete Data Extraction

Extract sprite images and metadata

Generate hierarchy structure diagrams

Save extraction data in JSON format

🖼️ Visual Interface

Intuitive sprite selection interface

Categorized display of character parts

Real-time preview and zoom functionality

Usage
Select File

Click "Select Bundle File"

Navigate to: manosaba_game\manosaba_Data\StreamingAssets\aa\StandaloneWindows64\naninovel-characters_assets_naninovel\characters

Choose Processing Mode

Auto Detect: Intelligently selects mode based on filename

Sprites Only: Quick extraction of all sprite images

Full Extraction: Sprites + hierarchy data

Sprite Selection & Composition

Select sprite parts to compose in left panel

Adjust depth sorting (optional)

Real-time preview of composition

Save Results

Save composite images as PNG

Export extraction data and hierarchy information

Output File Structure
text
extraction/
├── sprites/              # Extracted sprite images
├── extraction_data.json  # Complete extraction data
├── sprite_data.json      # Sprite metadata
└── hierarchy.txt         # Hierarchy structure information
System Requirements
Python 3.8+

Windows 10/11 (Recommended)

Minimum 4GB available RAM

Install Dependencies
bash
pip install UnityPy pillow numpy
How to Run
bash
python tkinter_app.py
Notes
Ensure sufficient disk space for extracted files

Initial run may take longer for initialization

Recommended to close other large applications for optimal performance

Tkinter usually comes with Python, ensure proper installation if issues occur

License
MIT License - Feel free to use and modify for your projects.

Contributing
Feel free to submit issues and enhancement requests!

Disclaimer
This tool is for educational and personal use only. Please respect the intellectual property rights of game developers.
