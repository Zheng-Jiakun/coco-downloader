# Resource Compilation Tools

本目录包含用于编译 Qt 资源文件的工具脚本。

## pyrcc5 - Qt Resource Compiler

### 什么是 pyrcc5？

`pyrcc5` 是 PyQt5 的资源编译器，用于将 `.qrc` 资源文件（包含图片、图标、样式表等）编译为 Python 模块。

### 使用方法

#### 方法 1：使用包装脚本（推荐）

```bash
# 编译单个 qrc 文件
python tools/compile_rc.py app/resource/resource.qrc -o app/common/resource.py

# 如果有多个资源文件
python tools/compile_rc.py app/resource/icons.qrc -o app/common/icons_rc.py
```

#### 方法 2：直接使用 Python 模块

```bash
python -m PyQt5.pyrcc_main app/resource/resource.qrc -o app/common/resource.py
```

#### 方法 3：创建批处理脚本

在项目根目录运行：
```bash
# Windows
python tools/make_compile_script.py

# 然后直接使用
./compile_resources.bat   # Windows
./compile_resources.sh    # Linux/Mac
```

### QRC 文件示例

创建 `app/resource/resource.qrc`：

```xml
<!DOCTYPE RCC>
<RCC version="1.0">
    <qresource prefix="/app">
        <file>images/logo.png</file>
        <file>images/icon.png</file>
    </qresource>
    <qresource prefix="/qss">
        <file>qss/light.qss</file>
        <file>qss/dark.qss</file>
    </qresource>
</RCC>
```

### 在代码中使用编译后的资源

```python
# 导入编译后的资源模块
from app.common import resource

# 使用资源路径（注意前缀）
icon = QIcon(':/app/images/logo.png')

# 或读取 QSS
with open(':/qss/light.qss', 'r') as f:
    stylesheet = f.read()
```

### 常见问题

1. **找不到 pyrcc5 命令**
   - 使用上面的 Python 脚本包装器即可

2. **编译后的文件很大**
   - 正常现象，资源会被 base64 编码嵌入 Python 文件
   - 考虑只包含必需的资源

3. **更新资源后没有生效**
   - 重新编译 qrc 文件
   - 重启应用

### 自动化编译

可以在开发时使用文件监听自动编译：

```python
# 添加到项目构建脚本
import subprocess
import os

qrc_file = 'app/resource/resource.qrc'
output_file = 'app/common/resource.py'

subprocess.run([
    'python', '-m', 'PyQt5.pyrcc_main',
    qrc_file, '-o', output_file
])
```

## 相关工具

- **pyuic5**: UI 文件编译器（.ui -> .py）
  ```bash
  python -m PyQt5.uic.pyuic input.ui -o output.py
  ```

- **pylupdate5**: 翻译文件生成器（.py -> .ts）
  ```bash
  python -m PyQt5.pylupdate_main project.pro
  ```

- **lrelease**: 翻译文件编译器（.ts -> .qm）
  ```bash
  lrelease translations/*.ts
  ```
